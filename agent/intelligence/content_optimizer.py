import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .gemini_client import GeminiSEOClient
from ..models import Recommendation, CrawlResult, Website

logger = logging.getLogger("ai_seo.intelligence.content_optimizer")

class ContentOptimizer:
    """
    Produces actionable title, meta description, and heading optimizations
    with strict risk scoring, automation eligibility, and verification criteria.
    """

    def __init__(self, gemini_client: Optional[GeminiSEOClient] = None):
        self.ai = gemini_client or GeminiSEOClient()

    async def optimize_page_metadata(
        self,
        url: str,
        current_title: str,
        current_description: str,
        target_keyword: str,
        page_snippet: str = ""
    ) -> Dict[str, Any]:
        """
        Generates optimized meta tags with clear before/after values and rationale.
        """
        ai_result = await self.ai.rewrite_meta_tags(
            page_title=current_title,
            current_desc=current_description,
            page_content=page_snippet,
            target_keyword=target_keyword
        )

        return {
            "url": url,
            "target_keyword": target_keyword,
            "before": {
                "title": current_title,
                "meta_description": current_description
            },
            "after": {
                "title": ai_result.get("optimized_title", current_title),
                "meta_description": ai_result.get("optimized_description", current_description),
                "h1": ai_result.get("h1_suggestion", "")
            },
            "expected_benefit": "Increases organic SERP Click-Through-Rate (CTR) and search keyword relevance.",
            "risk_level": "low",
            "automation_eligible": True,
            "verification_steps": "1. Inspect live HTML head tags. 2. Verify title and meta description match proposed values. 3. Check for absence of double-encoding or truncation."
        }

    async def generate_recommendations_for_crawl(
        self,
        website_id: int,
        crawl_results: List[Any],
        db: AsyncSession
    ) -> List[Recommendation]:
        """
        Creates prioritized recommendations with evidence and automated change payloads.
        Supports both dicts (returned from spider) and CrawlResult DB models.
        """
        recs = []
        for cr in crawl_results:
            if isinstance(cr, dict):
                url = cr.get("url", "")
                title = cr.get("title") or ""
                meta_desc = cr.get("meta_description") or ""
            else:
                url = getattr(cr, "url", "")
                title = getattr(cr, "title", "") or ""
                meta_desc = getattr(cr, "meta_description", "") or ""

            if not url:
                continue

            # Check for missing or short meta description
            if not meta_desc or len(meta_desc) < 70:
                domain_clean = urlparse(url).netloc.replace("www.", "").split(".")[0].title()
                clean_title = (title or "").split("|")[0].split("-")[0].strip() or "our services"
                proposed_desc = f"Learn more about {clean_title} at {domain_clean}. High quality solutions, expert support, and comprehensive details."[:155]
                
                # Safe check for existing recommendation (avoids MultipleResultsFound)
                stmt = select(Recommendation.id).where(
                    Recommendation.website_id == website_id,
                    Recommendation.url == url,
                    Recommendation.issue_title == "Optimize Meta Description"
                ).limit(1)
                res = await db.execute(stmt)
                existing = res.scalar()

                if not existing:
                    rec = Recommendation(
                        website_id=website_id,
                        url=url,
                        issue_title="Optimize Meta Description",
                        severity="high" if not meta_desc else "medium",
                        category="onpage",
                        evidence=f"Current meta description: '{meta_desc or 'NONE'}' (length: {len(meta_desc)})",
                        proposed_fix=f"Update meta description to: '{proposed_desc}'",
                        proposed_change_data={
                            "field": "meta_description",
                            "current_value": meta_desc,
                            "proposed_value": proposed_desc
                        },
                        expected_benefit="Improves SERP snippet display and organic click-through rate.",
                        risk_level="low",
                        automation_eligible=True,
                        status="suggested"
                    )
                    db.add(rec)
                    recs.append(rec)

        await db.commit()
        return recs
