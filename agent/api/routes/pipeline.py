import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.security import get_current_token_auth
from ...core.database import get_db
from ...models import Website, BusinessProfile, Recommendation
from ...workflows.ranking_pipeline import ranking_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["10-Stage SEO Ranking Pipeline"], dependencies=[Depends(get_current_token_auth)])

async def _run_pipeline_task(website_id: int, job_id: str):
    await ranking_pipeline.execute_pipeline(website_id=website_id, job_id=job_id)

@router.post("/run/{website_id}")
async def trigger_ranking_pipeline(website_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    job_id = f"rank_{uuid.uuid4().hex[:8]}"
    background_tasks.add_task(_run_pipeline_task, website_id, job_id)

    return {
        "success": True,
        "job_id": job_id,
        "website_id": website_id,
        "domain": site.domain,
        "message": f"Full 10-stage SEO ranking workflow initiated for {site.domain}."
    }

@router.get("/status/{job_id}")
async def get_pipeline_status(job_id: str):
    state = ranking_pipeline.active_jobs.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline job not found.")
    return state

@router.get("/business-profile/{website_id}")
async def get_business_profile(website_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(BusinessProfile).where(BusinessProfile.website_id == website_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        return {
            "business_name": None,
            "summary": "Business profile has not been generated yet. Run the ranking pipeline to analyze.",
            "offerings": [],
            "target_audience": [],
            "service_locations": [],
            "languages": ["en"],
            "competitors": [],
            "seo_goals": [],
            "content_gaps": [],
            "internal_linking_plan": [],
            "authority_roadmap": []
        }

    return {
        "business_name": profile.business_name,
        "summary": profile.summary,
        "offerings": profile.offerings or [],
        "target_audience": profile.target_audience or [],
        "service_locations": profile.service_locations or [],
        "languages": profile.languages or ["en"],
        "competitors": profile.competitors or [],
        "seo_goals": profile.seo_goals or [],
        "content_gaps": profile.content_gaps or [],
        "internal_linking_plan": profile.internal_linking_plan or [],
        "authority_roadmap": profile.authority_roadmap or []
    }
