import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Recommendation, BusinessProfile
from .gemini_client import GeminiSEOClient

logger = logging.getLogger("ai_seo.intelligence.authority_linking")

class AuthorityAndLinkingManager:
    """
    Stage 7: Improve internal links and website authority.
    - Connects related pages into topic clusters
    - Identifies orphan or under-linked valuable pages
    - Recommends descriptive contextual anchor text
    - Outlines trustworthy authority and backlink outreach roadmaps
    """

    def __init__(self, gemini_client: Optional[GeminiSEOClient] = None):
        self.ai = gemini_client or GeminiSEOClient()

    async def analyze_and_optimize_links(
        self,
        website_id: int,
        domain: str,
        crawl_pages: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyzes the internal linking network and generates semantic internal linking suggestions
        and authority roadmaps.
        """
        urls = [p.get("url", "") for p in crawl_pages if p.get("url")]
        homepage_url = f"https://{domain}/"

        internal_link_pairs = []
        # Identify under-linked pages (internal_links_count <= 1)
        for page in crawl_pages:
            url = page.get("url", "")
            if not url or url.rstrip("/") == homepage_url.rstrip("/"):
                continue

            title = page.get("title") or page.get("h1") or "Page"
            clean_anchor = title.split("-")[0].split("|")[0].strip()

            # Recommend linking from homepage or main hub to this page
            internal_link_pairs.append({
                "source_page": homepage_url,
                "target_page": url,
                "suggested_anchor": clean_anchor or "Explore our service",
                "reason": "Strengthens page discovery and passes homepage PageRank equity to valuable deep pages."
            })

            # Check if page has no internal links
            if page.get("internal_links_count", 0) <= 1:
                await self._create_rec_if_not_exists(
                    website_id=website_id,
                    url=url,
                    issue_title=f"Under-linked Page: Add Internal Link from Homepage or Hub",
                    severity="medium",
                    category="internal_linking",
                    evidence=f"Page has minimal incoming internal links ({page.get('internal_links_count', 0)} detected).",
                    proposed_fix=f"Add contextual internal link on {homepage_url} pointing to {url} using anchor text '{clean_anchor}'.",
                    expected_benefit="Enhances Googlebot crawl frequency and accelerates indexation.",
                    risk_level="low",
                    db=db
                )

        # Authority building roadmap hooks
        authority_roadmap = [
            {
                "strategy": "Original Industry Research & Statistics",
                "description": f"Publish original benchmark data or industry takeaways related to {domain.split('.')[0].title()} offerings. Data-driven pages naturally earn editorial backlinks.",
                "difficulty": "Medium",
                "expected_impact": "High authority signals"
            },
            {
                "strategy": "Curated Resource Directory Inclusions",
                "description": f"Identify curated industry directories, software libraries, and official tool listings to submit {domain}.",
                "difficulty": "Low",
                "expected_impact": "Foundational domain authority & referral traffic"
            },
            {
                "strategy": "Ecosystem Partner Collaborations",
                "description": "Cross-collaborate with non-competing vendors, CMS integrations, or ecosystem clients for joint case studies.",
                "difficulty": "Medium",
                "expected_impact": "High-relevance contextual backlinks"
            }
        ]

        # Update BusinessProfile with internal linking plan and authority roadmap
        stmt = select(BusinessProfile).where(BusinessProfile.website_id == website_id).limit(1)
        res = await db.execute(stmt)
        profile = res.scalars().first()
        if profile:
            profile.internal_linking_plan = internal_link_pairs[:10]
            profile.authority_roadmap = authority_roadmap

        await db.commit()
        logger.info(f"Generated {len(internal_link_pairs)} internal linking opportunities for Website #{website_id}")

        return {
            "internal_linking_plan": internal_link_pairs[:10],
            "authority_roadmap": authority_roadmap
        }

    async def _create_rec_if_not_exists(
        self,
        website_id: int,
        url: str,
        issue_title: str,
        severity: str,
        category: str,
        evidence: str,
        proposed_fix: str,
        expected_benefit: str,
        risk_level: str,
        db: AsyncSession
    ):
        stmt = select(Recommendation.id).where(
            Recommendation.website_id == website_id,
            Recommendation.url == url,
            Recommendation.issue_title == issue_title
        ).limit(1)
        res = await db.execute(stmt)
        if not res.scalar():
            rec = Recommendation(
                website_id=website_id,
                url=url,
                issue_title=issue_title,
                severity=severity,
                category=category,
                evidence=evidence,
                proposed_fix=proposed_fix,
                expected_benefit=expected_benefit,
                risk_level=risk_level,
                automation_eligible=True,
                status="suggested"
            )
            db.add(rec)
