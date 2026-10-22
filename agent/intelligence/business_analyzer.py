import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import BusinessProfile, Website
from .gemini_client import GeminiSEOClient

logger = logging.getLogger("ai_seo.intelligence.business_analyzer")

class BusinessAudienceAnalyzer:
    """
    Stage 1: Understand the business and target audience.
    Analyzes website homepage, about/services text, and metadata to identify:
    - Business profile and offerings
    - Target customers & personas
    - Service locations & languages
    - Industry competitors
    - Concrete, prioritized SEO goals
    """

    def __init__(self, gemini_client: Optional[GeminiSEOClient] = None):
        self.ai = gemini_client or GeminiSEOClient()

    async def analyze_business(
        self,
        website_id: int,
        domain: str,
        crawl_pages: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Extracts business intelligence from crawl data and Gemini AI,
        and saves or updates the BusinessProfile record.
        """
        # Gather text from homepage and key pages (about, services)
        homepage_title = ""
        homepage_desc = ""
        homepage_h1 = ""
        sampled_content = []

        for p in crawl_pages[:10]:
            url = p.get("url", "")
            title = p.get("title") or ""
            desc = p.get("meta_description") or ""
            h1 = p.get("h1") or ""

            if not homepage_title and (url.rstrip("/") == f"https://{domain}" or url.rstrip("/") == f"http://{domain}"):
                homepage_title = title
                homepage_desc = desc
                homepage_h1 = h1

            page_info = f"URL: {url} | Title: {title} | H1: {h1} | Description: {desc}"
            sampled_content.append(page_info)

        content_blob = "\n".join(sampled_content[:8])

        # Prepare AI prompt
        prompt = f"""
        Analyze the following website information for domain '{domain}':
        {content_blob}

        Produce a comprehensive Business Profile and SEO Ranking Strategy in valid JSON format:
        {{
            "business_name": "Inferred Company Name",
            "summary": "Clear, concise 2-sentence summary of what the business does and value proposition.",
            "offerings": ["Product or Service 1", "Product or Service 2", "Product or Service 3"],
            "target_audience": ["Target Persona/Customer 1", "Target Industry/Audience 2"],
            "service_locations": ["Primary service areas or 'Global' / 'Regional'"],
            "languages": ["en"],
            "competitors": ["Likely competitor 1", "Likely competitor 2"],
            "seo_goals": [
                "Primary Goal: Rank in top 3 for high-intent commercial terms",
                "Secondary Goal: Build authoritative informational content answering customer pain points",
                "Technical Goal: Ensure 100% crawl accessibility and zero indexation barriers"
            ]
        }}
        """

        ai_response = await self.ai.generate_json(prompt, system_instruction="You are an expert SEO Business Analyst.")

        # Deterministic fallback heuristics if AI key is absent
        if not ai_response or not isinstance(ai_response, dict):
            inferred_name = homepage_title.split("-")[0].split("|")[0].strip() if homepage_title else domain.split(".")[0].title()
            ai_response = {
                "business_name": inferred_name,
                "summary": homepage_desc or f"Provider of commercial and informational solutions for {domain}.",
                "offerings": [homepage_h1] if homepage_h1 else ["Digital Services", "Products"],
                "target_audience": ["Online consumers", "B2B and B2C clients looking for solutions"],
                "service_locations": ["Global / Online"],
                "languages": ["en"],
                "competitors": [f"competitor-{domain.split('.')[0]}.com"],
                "seo_goals": [
                    "Drive targeted organic traffic for primary business offerings",
                    "Maximize Click-Through-Rate (CTR) across top landing pages",
                    "Eliminate all technical crawl issues and achieve rapid indexing"
                ]
            }

        # Persist to database
        stmt = select(BusinessProfile).where(BusinessProfile.website_id == website_id).limit(1)
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if profile:
            profile.business_name = ai_response.get("business_name") or profile.business_name
            profile.summary = ai_response.get("summary") or profile.summary
            profile.offerings = ai_response.get("offerings") or profile.offerings
            profile.target_audience = ai_response.get("target_audience") or profile.target_audience
            profile.service_locations = ai_response.get("service_locations") or profile.service_locations
            profile.languages = ai_response.get("languages") or profile.languages
            profile.competitors = ai_response.get("competitors") or profile.competitors
            profile.seo_goals = ai_response.get("seo_goals") or profile.seo_goals
        else:
            profile = BusinessProfile(
                website_id=website_id,
                business_name=ai_response.get("business_name"),
                summary=ai_response.get("summary"),
                offerings=ai_response.get("offerings", []),
                target_audience=ai_response.get("target_audience", []),
                service_locations=ai_response.get("service_locations", []),
                languages=ai_response.get("languages", ["en"]),
                competitors=ai_response.get("competitors", []),
                seo_goals=ai_response.get("seo_goals", [])
            )
            db.add(profile)

        await db.commit()
        await db.refresh(profile)

        logger.info(f"Generated Business Profile for #{website_id} ({domain}): {profile.business_name}")
        return {
            "business_name": profile.business_name,
            "summary": profile.summary,
            "offerings": profile.offerings,
            "target_audience": profile.target_audience,
            "service_locations": profile.service_locations,
            "languages": profile.languages,
            "competitors": profile.competitors,
            "seo_goals": profile.seo_goals
        }
