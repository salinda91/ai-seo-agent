from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ...core.database import get_db
from ...core.security import get_current_token_auth
from ...models import Keyword, Website
from ...intelligence.keyword_research import KeywordResearcher
from ...intelligence.gemini_client import GeminiSEOClient
from ...intelligence.content_optimizer import ContentOptimizer

router = APIRouter(prefix="/api/keywords", tags=["Keyword Research"], dependencies=[Depends(get_current_token_auth)])

class MetaOptimizeRequest(BaseModel):
    url: str
    current_title: str
    current_description: str
    target_keyword: str
    page_snippet: Optional[str] = ""

class ClusterRequest(BaseModel):
    phrases: List[str]

@router.get("/{website_id}")
async def get_keywords(website_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.website_id == website_id).order_by(Keyword.opportunity_score.desc())
    res = await db.execute(stmt)
    kws = res.scalars().all()
    return [
        {
            "id": k.id,
            "phrase": k.phrase,
            "target_page": k.target_page,
            "search_intent": k.search_intent,
            "impressions": k.impressions,
            "clicks": k.clicks,
            "ctr": k.ctr,
            "position": k.position,
            "opportunity_score": k.opportunity_score,
            "source": k.source
        }
        for k in kws
    ]

@router.post("/cluster")
async def cluster_keywords(payload: ClusterRequest):
    researcher = KeywordResearcher()
    clusters = await researcher.cluster_keywords(payload.phrases)
    return {"clusters": clusters}

@router.post("/optimize-meta")
async def optimize_meta(payload: MetaOptimizeRequest):
    optimizer = ContentOptimizer()
    result = await optimizer.optimize_page_metadata(
        url=payload.url,
        current_title=payload.current_title,
        current_description=payload.current_description,
        target_keyword=payload.target_keyword,
        page_snippet=payload.page_snippet or ""
    )
    return result
