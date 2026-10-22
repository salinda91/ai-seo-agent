from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_token_auth
from ...models import Website

router = APIRouter(prefix="/api/websites", tags=["Websites"], dependencies=[Depends(get_current_token_auth)])

class WebsiteCreate(BaseModel):
    domain: str
    name: str
    cms_type: str = "wordpress"
    admin_url: Optional[str] = None
    local_repo_path: Optional[str] = None
    git_branch: Optional[str] = "main"
    git_remote: Optional[str] = "origin"
    gsc_property_id: Optional[str] = None
    automation_mode: str = "supervised"

class WebsiteUpdate(BaseModel):
    domain: Optional[str] = None
    name: Optional[str] = None
    cms_type: Optional[str] = None
    admin_url: Optional[str] = None
    local_repo_path: Optional[str] = None
    git_branch: Optional[str] = None
    git_remote: Optional[str] = None
    automation_mode: Optional[str] = None

class WebsiteResponse(BaseModel):
    id: int
    domain: str
    name: str
    cms_type: str
    admin_url: Optional[str]
    local_repo_path: Optional[str] = None
    git_branch: Optional[str] = "main"
    git_remote: Optional[str] = "origin"
    is_active: bool
    gsc_property_id: Optional[str]
    gsc_verified: bool
    automation_mode: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[WebsiteResponse])
async def list_websites(db: AsyncSession = Depends(get_db)):
    stmt = select(Website).order_by(Website.id.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=WebsiteResponse)
async def create_website(payload: WebsiteCreate, db: AsyncSession = Depends(get_db)):
    clean_domain = payload.domain.replace("https://", "").replace("http://", "").strip("/")
    stmt = select(Website).where(Website.domain == clean_domain)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Website with this domain already exists.")

    site = Website(
        domain=clean_domain,
        name=payload.name,
        cms_type=payload.cms_type,
        admin_url=payload.admin_url,
        local_repo_path=payload.local_repo_path,
        git_branch=payload.git_branch or "main",
        git_remote=payload.git_remote or "origin",
        gsc_property_id=payload.gsc_property_id or f"sc-domain:{clean_domain}",
        automation_mode=payload.automation_mode
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site

@router.put("/{website_id}", response_model=WebsiteResponse)
async def update_website(website_id: int, payload: WebsiteUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")

    if payload.domain is not None:
        clean = payload.domain.replace("https://", "").replace("http://", "").strip("/")
        if clean:
            site.domain = clean
    if payload.name is not None:
        site.name = payload.name
    if payload.cms_type is not None:
        site.cms_type = payload.cms_type
    if payload.admin_url is not None:
        site.admin_url = payload.admin_url
    if payload.local_repo_path is not None:
        site.local_repo_path = payload.local_repo_path
    if payload.git_branch is not None:
        site.git_branch = payload.git_branch
    if payload.git_remote is not None:
        site.git_remote = payload.git_remote
    if payload.automation_mode is not None:
        site.automation_mode = payload.automation_mode

    await db.commit()
    await db.refresh(site)
    return site

@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(website_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")
    return site

@router.delete("/{website_id}")
async def delete_website(website_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Website).where(Website.id == website_id)
    res = await db.execute(stmt)
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Website not found.")
    await db.delete(site)
    await db.commit()
    return {"success": True, "message": "Website removed."}
