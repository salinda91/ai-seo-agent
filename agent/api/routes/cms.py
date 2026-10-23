from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ...core.database import get_db
from ...core.security import get_current_token_auth
from ...models import Website, Recommendation, ChangeRecord
from ...browser.controller import browser_controller
from ...workflows.cms.wordpress import WordPressAutomation
from ...workflows.cms.woocommerce import WooCommerceAutomation
from ...workflows.cms.laravel import LaravelAdminAutomation
from ...workflows.codebase.git_fixer import local_codebase_fixer
from ...workflows.sitemap import sitemap_manager

router = APIRouter(prefix="/api/cms", tags=["CMS Automation & Rollback"], dependencies=[Depends(get_current_token_auth)])

class ApplyChangeRequest(BaseModel):
    website_id: int
    recommendation_id: Optional[int] = None
    url: str
    field_name: str  # e.g. "meta_description" or "title"
    new_value: str

@router.get("/recommendations/{website_id}")
async def get_recommendations(website_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Recommendation).where(Recommendation.website_id == website_id).order_by(Recommendation.id.desc())
    res = await db.execute(stmt)
    recs = res.scalars().all()
    return [
        {
            "id": r.id,
            "url": r.url,
            "issue_title": r.issue_title,
            "severity": r.severity,
            "category": r.category,
            "evidence": r.evidence,
            "proposed_fix": r.proposed_fix,
            "proposed_change_data": r.proposed_change_data or {},
            "expected_benefit": r.expected_benefit,
            "risk_level": r.risk_level,
            "automation_eligible": r.automation_eligible,
            "status": r.status
        }
        for r in recs
    ]

@router.post("/apply")
async def apply_seo_change(payload: ApplyChangeRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    # 0. XML Sitemap Generation & Upload
    if payload.field_name in ("sitemap", "sitemap.xml") or payload.url.endswith("sitemap.xml"):
        result = await sitemap_manager.create_and_upload_sitemap(
            website_id=site.id,
            db=db,
            auto_submit_gsc=True
        )
        return result

    # 1. WordPress
    if site.cms_type == "wordpress":
        if not site.admin_url:
            raise HTTPException(status_code=400, detail="WordPress site has no Admin URL configured. Please add Admin URL in Connected Websites.")
        post_slug = payload.url.strip("/").split("/")[-1] or "home"
        wp = WordPressAutomation(browser_controller)
        result = await wp.update_post_seo(
            db=db,
            website_id=site.id,
            admin_base_url=site.admin_url,
            post_slug_or_title=post_slug,
            public_url=payload.url,
            new_meta_description=payload.new_value if payload.field_name == "meta_description" else None,
            new_title=payload.new_value if payload.field_name == "title" else None,
            recommendation_id=payload.recommendation_id
        )

    # 2. WooCommerce
    elif site.cms_type == "woocommerce":
        if not site.admin_url:
            raise HTTPException(status_code=400, detail="WooCommerce site has no Admin URL configured. Please add Admin URL in Connected Websites.")
        post_slug = payload.url.strip("/").split("/")[-1] or "home"
        woo = WooCommerceAutomation(browser_controller)
        result = await woo.update_product_seo(
            db=db,
            website_id=site.id,
            admin_base_url=site.admin_url,
            product_title=post_slug,
            public_url=payload.url,
            new_meta_description=payload.new_value,
            recommendation_id=payload.recommendation_id
        )

    # 3. Custom / Non-WordPress (or Laravel with connected codebase): Apply directly to code and commit/push to Git!
    elif site.cms_type in ("custom", "laravel") or site.local_repo_path:
        if not site.local_repo_path:
            raise HTTPException(
                status_code=400,
                detail=f"This website is configured as '{site.cms_type}'. To apply changes directly to code and push to Git, please connect its local codebase folder path in Connected Websites."
            )
        result = await local_codebase_fixer.apply_single_change(
            website_id=site.id,
            repo_path_str=site.local_repo_path,
            url=payload.url,
            field_name=payload.field_name,
            new_value=payload.new_value,
            db=db,
            recommendation_id=payload.recommendation_id,
            git_branch=site.git_branch or "main",
            git_remote=site.git_remote or "origin",
            auto_push=True
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to apply change to code."))

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported CMS '{site.cms_type}'. Connect local project folder in Connected Websites to apply changes directly to code."
        )

    if result.get("success") and payload.recommendation_id:
        stmt_rec = select(Recommendation).where(Recommendation.id == payload.recommendation_id)
        res_rec = await db.execute(stmt_rec)
        rec = res_rec.scalar_one_or_none()
        if rec and rec.status != "applied":
            rec.status = "applied"
            await db.commit()

    return result

@router.post("/rollback/{change_id}")
async def rollback_change(change_id: int, db: AsyncSession = Depends(get_db)):
    """
    Rolls back an applied change by re-applying the before_value:
    - If WordPress/WooCommerce: updates in CMS via browser automation.
    - If Custom/Codebase: updates source file on disk and commits/pushes to Git.
    """
    stmt = select(ChangeRecord).where(ChangeRecord.id == change_id)
    res = await db.execute(stmt)
    change = res.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=404, detail="Change record not found.")

    stmt_site = select(Website).where(Website.id == change.website_id)
    res_site = await db.execute(stmt_site)
    site = res_site.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Associated website not found.")

    # 1. Custom / Codebase rollback
    if site.local_repo_path and (site.cms_type in ("custom", "laravel") or not site.admin_url):
        actual_field = change.field_name.split(":")[-1]
        rollback_res = await local_codebase_fixer.apply_single_change(
            website_id=site.id,
            repo_path_str=site.local_repo_path,
            url=change.url,
            field_name=actual_field,
            new_value=change.before_value if change.before_value != "empty" else "",
            db=db,
            recommendation_id=change.recommendation_id,
            git_branch=site.git_branch or "main",
            git_remote=site.git_remote or "origin",
            auto_push=True
        )
        if rollback_res.get("success"):
            change.status = "rolled_back"
            await db.commit()
        return rollback_res

    # 2. WordPress / WooCommerce rollback
    if not site.admin_url:
        raise HTTPException(status_code=400, detail="Cannot rollback without website admin URL or connected local codebase.")

    post_slug = change.url.strip("/").split("/")[-1] or "home"
    wp = WordPressAutomation(browser_controller)
    rollback_res = await wp.update_post_seo(
        db=db,
        website_id=site.id,
        admin_base_url=site.admin_url,
        post_slug_or_title=post_slug,
        public_url=change.url,
        new_meta_description=change.before_value if change.field_name == "meta_description" else None,
        new_title=change.before_value if change.field_name == "title" else None,
        recommendation_id=change.recommendation_id
    )

    if rollback_res.get("success"):
        change.status = "rolled_back"
        await db.commit()

    return rollback_res

@router.get("/changes/{website_id}")
async def get_changes(website_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(ChangeRecord).where(ChangeRecord.website_id == website_id).order_by(ChangeRecord.id.desc())
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [
        {
            "id": it.id,
            "url": it.url,
            "field_name": it.field_name,
            "before_value": it.before_value,
            "after_value": it.after_value,
            "status": it.status,
            "applied_at": it.applied_at,
            "verified_at": it.verified_at
        }
        for it in items
    ]

@router.post("/auto-fix-all/{website_id}")
async def auto_fix_all_audit_issues(website_id: int, db: AsyncSession = Depends(get_db)):
    """
    Automatically fixes all audit issues:
    - If WordPress / WooCommerce: fixes via browser automation in wp-admin.
    - If Non-WordPress (custom, laravel, etc.): fixes in the connected local codebase folder and pushes to Git!
    """
    stmt = select(Website).where(Website.id == website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    if site.cms_type in ("wordpress", "woocommerce"):
        if not site.admin_url:
            raise HTTPException(
                status_code=400,
                detail="WordPress admin URL is missing. Please add the WordPress admin URL in Connected Websites."
            )
        wp = WordPressAutomation(browser_controller)
        result = await wp.batch_auto_fix_audit_issues(
            db=db,
            website_id=site.id,
            admin_base_url=site.admin_url
        )
        return result

    # Non-WordPress: Fix in local codebase folder and push to git
    if site.local_repo_path:
        result = await local_codebase_fixer.fix_and_push_codebase(
            website_id=site.id,
            repo_path_str=site.local_repo_path,
            db=db,
            git_branch=site.git_branch or "main",
            git_remote=site.git_remote or "origin",
            auto_push=True
        )
        return result

    raise HTTPException(
        status_code=400,
        detail="For non-WordPress websites, please connect a local project folder in the Websites settings so the agent can auto-fix files and push to Git."
    )

