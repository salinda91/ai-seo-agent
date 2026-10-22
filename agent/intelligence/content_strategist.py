import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Recommendation, BusinessProfile
from .gemini_client import GeminiSEOClient

logger = logging.getLogger("ai_seo.intelligence.content_strategist")

class ContentStrategist:
    """
    Stage 6: Create useful, original content.
    Identifies genuine content gaps between business offerings, keyword demand, and existing pages.
    Produces comprehensive content briefs for service pages, product descriptions, comparison articles,
    and location pages.
    """

    def __init__(self, gemini_client: Optional[GeminiSEOClient] = None):
        self.ai = gemini_client or GeminiSEOClient()

    async def identify_content_gaps(
        self,
        website_id: int,
        domain: str,
        business_profile: Optional[Dict[str, Any]],
        existing_urls: List[str],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        offerings = (business_profile or {}).get("offerings", [])
        audience = (business_profile or {}).get("target_audience", [])
        locations = (business_profile or {}).get("service_locations", [])

        prompt = f"""
        Website domain: {domain}
        Business Offerings: {', '.join(offerings) if offerings else 'Core products & digital services'}
        Target Audience: {', '.join(audience) if audience else 'Consumers & businesses'}
        Locations: {', '.join(locations) if locations else 'Global'}
        Existing Page URLs: {', '.join(existing_urls[:15])}

        Identify 3 high-impact content gaps that the website currently lacks but potential customers search for.
        Return in valid JSON format:
        {{
            "content_gaps": [
                {{
                    "topic": "Comprehensive Guide or Missing Service Page",
                    "target_keyword": "primary target search query",
                    "search_intent": "informational or commercial",
                    "suggested_slug": "/guide-name-or-service",
                    "proposed_title": "SEO Optimized Page Title | Brand",
                    "proposed_description": "Compelling 150-char meta description answering user query.",
                    "target_word_count": 1200,
                    "outline": ["H2: Overview", "H2: Key Benefits", "H2: Detailed Comparison", "H2: FAQs"],
                    "questions_to_answer": ["What is X?", "How does it work?", "How much does it cost?"],
                    "call_to_action": "Schedule a free consultation or view pricing."
                }}
            ]
        }}
        """

        ai_res = await self.ai.generate_json(prompt, system_instruction="You are an expert SEO Content Strategist.")

        gaps = []
        if ai_res and isinstance(ai_res, dict) and "content_gaps" in ai_res:
            gaps = ai_res["content_gaps"]
        else:
            # Deterministic fallback content gaps
            first_offering = offerings[0] if offerings else "Solutions"
            gaps = [
                {
                    "topic": f"In-Depth {first_offering} Buyers Guide",
                    "target_keyword": f"best {first_offering.lower()} guide",
                    "search_intent": "commercial",
                    "suggested_slug": f"/{first_offering.lower().replace(' ', '-')}-guide",
                    "proposed_title": f"The Complete Guide to {first_offering} | Complete Overview",
                    "proposed_description": f"Everything you need to know about {first_offering.lower()}. Compare options, key benefits, and expert tips.",
                    "target_word_count": 1500,
                    "outline": [f"What is {first_offering}?", "Key Benefits & Features", "Pricing & Comparison", "Frequently Asked Questions"],
                    "questions_to_answer": ["How does this solve my problem?", "What are the common pitfalls?", "What is the ROI?"],
                    "call_to_action": "Contact our team for a personalized walkthrough."
                },
                {
                    "topic": f"Comparison: How {domain.split('.')[0].title()} Compares Against Alternatives",
                    "target_keyword": f"{domain.split('.')[0].lower()} vs alternatives",
                    "search_intent": "commercial",
                    "suggested_slug": f"/compare/{domain.split('.')[0].lower()}-vs-alternatives",
                    "proposed_title": f"{domain.split('.')[0].title()} vs Alternatives: Full Feature Breakdown",
                    "proposed_description": f"Detailed comparison of features, pricing, and benefits. See why clients choose {domain.split('.')[0].title()}.",
                    "target_word_count": 1200,
                    "outline": ["Feature-by-Feature Matrix", "Performance & Speed", "Cost Comparison", "Customer Case Studies"],
                    "questions_to_answer": ["Which solution is right for my budget?", "What are the migration steps?"],
                    "call_to_action": "Get started today with zero risk."
                }
            ]

        # Save to recommendations table
        for gap in gaps:
            target_url = f"https://{domain}{gap.get('suggested_slug', '/new-content')}"
            title = f"Content Opportunity: {gap.get('topic')}"

            stmt = select(Recommendation.id).where(
                Recommendation.website_id == website_id,
                Recommendation.url == target_url
            ).limit(1)
            res = await db.execute(stmt)
            if not res.scalar():
                rec = Recommendation(
                    website_id=website_id,
                    url=target_url,
                    issue_title=title,
                    severity="high",
                    category="content_gap",
                    evidence=f"Target Query: '{gap.get('target_keyword')}' ({gap.get('search_intent')} intent). Website currently lacks dedicated content for this topic.",
                    proposed_fix=f"Publish high-quality original page matching search intent.\nOutline: {', '.join(gap.get('outline', []))}",
                    proposed_change_data=gap,
                    expected_benefit="Captures net-new search traffic, satisfies unaddressed search intent, and builds topical authority.",
                    risk_level="low",
                    automation_eligible=False,  # Draft review recommended
                    status="suggested"
                )
                db.add(rec)

        # Update BusinessProfile with content gaps list
        stmt_prof = select(BusinessProfile).where(BusinessProfile.website_id == website_id).limit(1)
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalars().first()
        if profile:
            profile.content_gaps = [g.get("topic") for g in gaps]

        await db.commit()
        logger.info(f"Generated {len(gaps)} content gap briefs for Website #{website_id}")
        return gaps
