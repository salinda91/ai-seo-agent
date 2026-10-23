import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ...core.database import get_db
from ...core.security import get_current_token_auth
from ...models import Website, Recommendation
from ...workflows.sitemap import sitemap_manager

logger = logging.getLogger("ai_seo.api.routes.sitemap")

router = APIRouter(prefix="/api/sitemap", tags=["XML Sitemap Automation"], dependencies=[Depends(get_current_token_auth)])

class CreateUploadSitemapRequest(BaseModel):
    website_id: int
    auto_submit_gsc: bool = True

@router.get("/status/{website_id}")
async def get_sitemap_status(website_id: int, db: AsyncSession = Depends(get_db)):
    """
    Checks whether an XML sitemap is live and publicly accessible on the website,
    checks if a local sitemap file exists in the codebase, and returns readiness details.
    """
    stmt = select(Website).where(Website.id == website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    # 1. Live HTTP check
    live_check = await sitemap_manager.check_sitemap_live(site.domain)

    # 2. Local file check if codebase connected
    local_found = False
    local_path = None
    if site.local_repo_path:
        repo_dir = Path(site.local_repo_path)
        for cand in [repo_dir / "public" / "sitemap.xml", repo_dir / "sitemap.xml"]:
            if cand.exists() and cand.is_file():
                local_found = True
                local_path = str(cand.relative_to(repo_dir))
                break

    # 3. Check if DB has pending 'Missing XML Sitemap' recommendation
    stmt_rec = select(Recommendation.id).where(
        Recommendation.website_id == site.id,
        Recommendation.issue_title == "Missing XML Sitemap",
        Recommendation.status == "suggested"
    ).limit(1)
    res_rec = await db.execute(stmt_rec)
    has_missing_rec = res_rec.scalar() is not None

    return {
        "website_id": site.id,
        "domain": site.domain,
        "available": live_check["available"],
        "sitemap_url": live_check["sitemap_url"],
        "status_code": live_check["status_code"],
        "details": live_check["details"],
        "has_local_file": local_found,
        "local_path": local_path,
        "has_missing_recommendation": has_missing_rec,
        "can_create_and_upload": bool(site.local_repo_path or site.admin_url or site.cms_type in ("wordpress", "custom", "laravel")),
        "cms_type": site.cms_type
    }

@router.post("/create-and-upload")
async def create_and_upload_sitemap_endpoint(payload: CreateUploadSitemapRequest, db: AsyncSession = Depends(get_db)):
    """
    Generates standard XML sitemap for the website, saves it to the local project codebase,
    commits & pushes to Git, and submits to Google Search Console.
    """
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    result = await sitemap_manager.create_and_upload_sitemap(
        website_id=payload.website_id,
        db=db,
        auto_submit_gsc=payload.auto_submit_gsc
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to create and upload sitemap."))

    return result
