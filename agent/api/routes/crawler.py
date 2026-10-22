from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ...core.database import get_db, AsyncSessionLocal
from ...core.security import get_current_token_auth
from ...models import Website, CrawlResult
from ...crawler.spider import SEOSpider
from ...intelligence.content_optimizer import ContentOptimizer

router = APIRouter(prefix="/api/crawl", tags=["Website Crawler"], dependencies=[Depends(get_current_token_auth)])

class CrawlRequest(BaseModel):
    website_id: int
    max_pages: int = 30

async def _run_crawl_background(website_id: int, domain: str, max_pages: int):
    async with AsyncSessionLocal() as db:
        spider = SEOSpider(website_id=website_id, base_url=f"https://{domain}", max_pages=max_pages)
        results = await spider.run(db)
        optimizer = ContentOptimizer()
        await optimizer.generate_recommendations_for_crawl(website_id, results, db)

@router.post("")
async def start_crawl(payload: CrawlRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    background_tasks.add_task(_run_crawl_background, site.id, site.domain, payload.max_pages)
    return {"success": True, "message": f"SEO crawl started for {site.domain} (max {payload.max_pages} pages)."}

@router.get("/{website_id}")
async def get_crawl_results(website_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawlResult).where(CrawlResult.website_id == website_id).order_by(CrawlResult.id.desc()).limit(100)
    res = await db.execute(stmt)
    items = res.scalars().all()

    total_pages = len(items)
    issues_count = sum(len(it.issues or []) for it in items)
    critical_issues = sum(1 for it in items for iss in (it.issues or []) if iss.get("severity") == "critical")
    high_issues = sum(1 for it in items for iss in (it.issues or []) if iss.get("severity") == "high")

    return {
        "total_pages": total_pages,
        "total_issues": issues_count,
        "critical_issues": critical_issues,
        "high_issues": high_issues,
        "pages": [
            {
                "id": it.id,
                "url": it.url,
                "status_code": it.status_code,
                "title": it.title,
                "meta_description": it.meta_description,
                "h1": it.h1,
                "canonical": it.canonical,
                "images_without_alt": it.images_without_alt,
                "issues": it.issues or []
            }
            for it in items
        ]
    }
