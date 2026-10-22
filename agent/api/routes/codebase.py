import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ...core.database import get_db
from ...core.security import get_current_token_auth
from ...models import Website, Recommendation, ChangeRecord
from ...workflows.codebase.git_fixer import local_codebase_fixer

router = APIRouter(prefix="/api/codebase", tags=["Local Codebase & Git SEO Automation"], dependencies=[Depends(get_current_token_auth)])

class ValidatePathRequest(BaseModel):
    path: str

class ConnectCodebaseRequest(BaseModel):
    website_id: int
    local_repo_path: str
    git_branch: Optional[str] = "main"
    git_remote: Optional[str] = "origin"

class FixAndPushRequest(BaseModel):
    website_id: int
    auto_push: bool = True
    custom_branch: Optional[str] = None
    custom_remote: Optional[str] = None

@router.post("/validate")
async def validate_local_path(payload: ValidatePathRequest):
    """Validates local folder path and inspects git repository parameters."""
    res = await local_codebase_fixer.validate_repo(payload.path)
    return res

@router.post("/connect")
async def connect_codebase(payload: ConnectCodebaseRequest, db: AsyncSession = Depends(get_db)):
    """Connects a local folder path to a website for non-WordPress auto-fixing."""
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    val = await local_codebase_fixer.validate_repo(payload.local_repo_path)
    if not val["valid"]:
        raise HTTPException(status_code=400, detail=val.get("error", "Invalid directory path."))

    site.local_repo_path = val["path"]
    site.git_branch = payload.git_branch or val.get("current_branch") or "main"
    site.git_remote = payload.git_remote or "origin"

    await db.commit()
    await db.refresh(site)

    return {
        "success": True,
        "website_id": site.id,
        "local_repo_path": site.local_repo_path,
        "git_branch": site.git_branch,
        "git_remote": site.git_remote,
        "is_git": val.get("is_git", False),
        "remote_url": val.get("remote_url", ""),
        "message": f"Successfully connected local codebase at {site.local_repo_path}"
    }

@router.post("/fix-and-push")
async def fix_audit_issues_and_push(payload: FixAndPushRequest, db: AsyncSession = Depends(get_db)):
    """
    Auto-fixes technical SEO issues in the connected local folder, commits, and pushes to Git.
    """
    stmt = select(Website).where(Website.id == payload.website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    if not site.local_repo_path:
        raise HTTPException(
            status_code=400,
            detail="No local codebase folder connected for this website. Please set the Local Project Path first."
        )

    branch = payload.custom_branch or site.git_branch or "main"
    remote = payload.custom_remote or site.git_remote or "origin"

    result = await local_codebase_fixer.fix_and_push_codebase(
        website_id=site.id,
        repo_path_str=site.local_repo_path,
        db=db,
        git_branch=branch,
        git_remote=remote,
        auto_push=payload.auto_push
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Codebase fix failed."))

    return result
