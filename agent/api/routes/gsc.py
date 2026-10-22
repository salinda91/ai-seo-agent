from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ...core.database import get_db, AsyncSessionLocal
from ...core.security import get_current_token_auth
from ...browser.controller import browser_controller
from ...workflows.gsc import (
    GSCPropertyManager,
    GSCPerformanceAnalyzer,
    GSCSitemapsManager,
    GSCURLInspector
)
from ...intelligence.keyword_research import KeywordResearcher
from ...models import Website, Task

router = APIRouter(prefix="/api/gsc", tags=["Google Search Console"], dependencies=[Depends(get_current_token_auth)])

class AddPropertyRequest(BaseModel):
    website_id: int
    is_domain: bool = False

class PerformanceRequest(BaseModel):
    website_id: int

class SitemapRequest(BaseModel):
    website_id: int
    sitemap_url: str

class InspectUrlRequest(BaseModel):
    website_id: int
    target_url: str
    request_indexing: bool = True

@router.post("/open")
async def open_gsc():
    manager = GSCPropertyManager(browser_controller)
    res = await manager.open_search_console()
    return res

@router.post("/properties")
async def list_gsc_properties():
    manager = GSCPropertyManager(browser_controller)
    props = await manager.list_properties()
    return {"properties": props}

@router.post("/add-property")
async def add_gsc_property(payload: AddPropertyRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    manager = GSCPropertyManager(browser_controller)
    domain_to_add = site.domain if payload.is_domain else f"https://{site.domain}/"
    result = await manager.add_property(domain_to_add, is_domain_property=payload.is_domain)

    if result.get("is_verified"):
        site.gsc_verified = True
        await db.commit()

    return result

@router.post("/performance")
async def sync_performance(payload: PerformanceRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    prop_id = site.gsc_property_id or f"sc-domain:{site.domain}"
    analyzer = GSCPerformanceAnalyzer(browser_controller)
    nav_res = await analyzer.navigate_to_performance(prop_id)
    if not nav_res["success"]:
        return nav_res

    metrics = await analyzer.extract_metric_cards()
    queries = await analyzer.extract_queries_table(max_rows=50)
    pages = await analyzer.extract_pages_table(max_rows=30)

    # Save keywords into database
    researcher = KeywordResearcher()
    saved_kws = await researcher.analyze_gsc_queries(site.id, queries, db)

    return {
        "success": True,
        "metrics": metrics,
        "queries_count": len(queries),
        "pages_count": len(pages),
        "keywords_saved": len(saved_kws),
        "queries": queries[:10],
        "pages": pages[:10],
        "screenshot": nav_res.get("screenshot")
    }

@router.post("/sitemaps")
async def handle_sitemap(payload: SitemapRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    prop_id = site.gsc_property_id or f"sc-domain:{site.domain}"
    mgr = GSCSitemapsManager(browser_controller)
    await mgr.navigate_to_sitemaps(prop_id)
    submit_res = await mgr.submit_sitemap(payload.sitemap_url)
    return submit_res

@router.post("/inspect")
async def inspect_url(payload: InspectUrlRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    prop_id = site.gsc_property_id or f"sc-domain:{site.domain}"
    inspector = GSCURLInspector(browser_controller)
    inspect_res = await inspector.inspect_url(prop_id, payload.target_url)

    indexing_res = None
    if payload.request_indexing and inspect_res.get("can_request_indexing"):
        indexing_res = await inspector.request_indexing()

    return {
        "inspection": inspect_res,
        "indexing_request": indexing_res
    }
