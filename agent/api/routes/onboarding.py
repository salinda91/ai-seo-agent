import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ...core.security import get_current_token_auth
from ...workflows.onboarding import domain_onboarding
from ...browser.controller import browser_controller

router = APIRouter(prefix="/api/onboarding", tags=["Full Domain Onboarding"], dependencies=[Depends(get_current_token_auth)])

class OnboardingRequest(BaseModel):
    domain: str
    name: Optional[str] = None
    cms_type: str = "wordpress"
    admin_url: Optional[str] = None
    automation_mode: str = "supervised"
    is_domain_property: bool = False
    local_repo_path: Optional[str] = None
    git_branch: Optional[str] = None
    git_remote: Optional[str] = None

async def _run_onboarding_task(payload: OnboardingRequest, job_id: str):
    await domain_onboarding.execute_onboarding(
        domain=payload.domain,
        name=payload.name,
        cms_type=payload.cms_type,
        admin_url=payload.admin_url,
        automation_mode=payload.automation_mode,
        is_domain_property=payload.is_domain_property,
        local_repo_path=payload.local_repo_path,
        git_branch=payload.git_branch,
        git_remote=payload.git_remote,
        job_id=job_id
    )

@router.post("/start")
async def start_onboarding(payload: OnboardingRequest, background_tasks: BackgroundTasks):
    clean_domain = payload.domain.replace("https://", "").replace("http://", "").strip("/")
    if not clean_domain:
        raise HTTPException(status_code=400, detail="Domain is required.")

    job_id = f"onboard_{uuid.uuid4().hex[:8]}"
    background_tasks.add_task(_run_onboarding_task, payload, job_id)

    return {
        "success": True,
        "job_id": job_id,
        "domain": clean_domain,
        "message": f"Full domain onboarding initiated for {clean_domain}."
    }

@router.get("/status/{job_id}")
async def get_onboarding_status(job_id: str):
    state = domain_onboarding.active_jobs.get(job_id)
    if not state:
        # Check by domain as fallback
        state = domain_onboarding.active_jobs.get(job_id.replace("https://", "").replace("http://", "").strip("/"))
    if not state:
        raise HTTPException(status_code=404, detail="Onboarding job not found.")
    return state
