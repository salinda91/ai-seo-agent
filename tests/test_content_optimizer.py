import uuid
import pytest
import pytest_asyncio
from agent.core.database import AsyncSessionLocal
from agent.models import Website
from agent.intelligence.content_optimizer import ContentOptimizer

@pytest.mark.asyncio
async def test_generate_recommendations_with_dicts():
    async with AsyncSessionLocal() as db:
        domain = f"testsite_{uuid.uuid4().hex[:8]}.org"
        site = Website(domain=domain, name="Test Dict Site")
        db.add(site)
        await db.commit()
        await db.refresh(site)

        # Crawl results as dictionaries (from spider.run)
        dict_results = [
            {
                "url": f"https://{domain}/about",
                "title": "About Us",
                "meta_description": "Short",  # Length < 70 -> triggers recommendation
                "issues": []
            },
            {
                "url": f"https://{domain}/services",
                "title": "Our Services",
                "meta_description": "Comprehensive and detailed meta description that is well over 70 characters long for testing purposes.",
                "issues": []
            }
        ]

        optimizer = ContentOptimizer()
        recs = await optimizer.generate_recommendations_for_crawl(site.id, dict_results, db)

        assert len(recs) == 1
        assert recs[0].url == f"https://{domain}/about"
        assert recs[0].issue_title == "Optimize Meta Description"
        assert recs[0].proposed_change_data["field"] == "meta_description"
