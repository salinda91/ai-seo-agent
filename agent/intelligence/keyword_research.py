import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .gemini_client import GeminiSEOClient
from ..models import Keyword

logger = logging.getLogger("ai_seo.intelligence.keyword_research")

class KeywordResearcher:
    """
    Analyzes website crawled data and Search Console queries to identify
    high-opportunity keywords, search intent, and clusters.
    """

    def __init__(self, gemini_client: Optional[GeminiSEOClient] = None):
        self.ai = gemini_client or GeminiSEOClient()

    def calculate_opportunity_score(
        self,
        impressions: int,
        clicks: int,
        ctr: float,
        position: float
    ) -> float:
        """
        Calculates an opportunity score (0.0 to 100.0).
        High impressions + low CTR + positions 5-20 yield the highest opportunity.
        """
        score = 0.0

        # Impression factor (up to 40 pts)
        if impressions > 5000:
            score += 40
        elif impressions > 1000:
            score += 30
        elif impressions > 200:
            score += 20
        elif impressions > 0:
            score += 10

        # Position factor (up to 35 pts)
        # Striking distance keywords (positions 4 - 20) have max potential for quick wins
        if 4.0 <= position <= 10.0:
            score += 35  # Bottom of page 1
        elif 10.1 <= position <= 20.0:
            score += 28  # Page 2 striking distance
        elif 1.0 <= position < 4.0:
            score += 15  # Already top 3, maintain
        elif position > 20.0:
            score += 10

        # Low CTR with high impressions indicates title/meta optimization opportunity
        if impressions > 200 and ctr < 0.02:
            score += 25
        elif ctr < 0.04:
            score += 15

        return round(min(score, 100.0), 1)

    def determine_search_intent(self, phrase: str) -> str:
        """Classifies search intent based on semantic markers."""
        phrase_lower = phrase.lower()
        if any(w in phrase_lower for w in ["buy", "discount", "price", "order", "purchase", "coupon", "cheap"]):
            return "transactional"
        if any(w in phrase_lower for w in ["best", "review", "vs", "compare", "top 10", "alternative"]):
            return "commercial"
        if any(w in phrase_lower for w in ["how to", "what is", "why", "guide", "tutorial", "tips", "examples"]):
            return "informational"
        if any(w in phrase_lower for w in ["login", "sign in", "portal", "website", "official"]):
            return "navigational"
        return "informational"

    async def analyze_gsc_queries(
        self,
        website_id: int,
        queries_data: List[Dict[str, Any]],
        db: AsyncSession
    ) -> List[Keyword]:
        """
        Processes real queries extracted from Google Search Console.
        Saves structured Keyword objects with opportunity scores.
        """
        saved_keywords = []
        for item in queries_data:
            phrase = item.get("query", "").strip()
            if not phrase:
                continue

            # Parse metrics safely
            try:
                clicks = int(item.get("clicks", "0").replace(",", ""))
            except ValueError:
                clicks = 0

            try:
                impressions = int(item.get("impressions", "0").replace(",", ""))
            except ValueError:
                impressions = 0

            try:
                ctr_str = item.get("ctr", "0%").replace("%", "").strip()
                ctr = float(ctr_str) / 100.0
            except ValueError:
                ctr = 0.0

            try:
                pos_str = item.get("position", "0.0").strip()
                position = float(pos_str)
            except ValueError:
                position = 0.0

            opportunity_score = self.calculate_opportunity_score(impressions, clicks, ctr, position)
            intent = self.determine_search_intent(phrase)

            # Check if keyword already exists
            stmt = select(Keyword).where(
                Keyword.website_id == website_id,
                Keyword.phrase == phrase
            ).limit(1)
            res = await db.execute(stmt)
            existing = res.scalars().first()

            if existing:
                existing.clicks = clicks
                existing.impressions = impressions
                existing.ctr = ctr
                existing.position = position
                existing.opportunity_score = opportunity_score
                existing.search_intent = intent
                existing.research_date = datetime.now(timezone.utc)
                saved_keywords.append(existing)
            else:
                kw = Keyword(
                    website_id=website_id,
                    phrase=phrase,
                    target_page=None,
                    search_intent=intent,
                    country="US",
                    language="en",
                    impressions=impressions,
                    clicks=clicks,
                    ctr=ctr,
                    position=position,
                    opportunity_score=opportunity_score,
                    confidence=1.0,
                    source="gsc"
                )
                db.add(kw)
                saved_keywords.append(kw)

        await db.commit()
        return saved_keywords

    async def cluster_keywords(self, phrases: List[str]) -> Dict[str, List[str]]:
        """
        Clusters keywords by topic/intent using Gemini or semantic token overlap.
        """
        if not phrases:
            return {}

        prompt = f"""
        Group the following SEO search queries into semantic topic clusters:
        Queries: {phrases[:80]}

        Return JSON format:
        {{
            "clusters": [
                {{
                    "cluster_name": "Topic Name",
                    "intent": "informational/commercial/transactional",
                    "keywords": ["query1", "query2"]
                }}
            ]
        }}
        """
        result = await self.ai.generate_json(prompt)
        if result and "clusters" in result:
            return {c["cluster_name"]: c["keywords"] for c in result["clusters"] if "cluster_name" in c and "keywords" in c}

        # Fallback grouping by first two words
        clusters = {}
        for p in phrases:
            words = p.split()
            key = " ".join(words[:2]) if len(words) >= 2 else p
            clusters.setdefault(key, []).append(p)
        return clusters
