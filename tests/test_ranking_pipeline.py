import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from agent.api.main import app
from agent.core.config import settings
from agent.workflows.ranking_pipeline import ranking_pipeline, FullSEORankingPipeline

@pytest.mark.asyncio
async def test_pipeline_api_unauthorized():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/pipeline/run/1")
        assert resp.status_code == 401

@pytest.mark.asyncio
async def test_pipeline_api_status_and_profile():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Agent-Token": settings.agent_token}
        
        # Test business profile query
        resp_prof = await client.get("/api/pipeline/business-profile/1", headers=headers)
        assert resp_prof.status_code == 200
        prof_data = resp_prof.json()
        assert "offerings" in prof_data
        assert "target_audience" in prof_data
        assert "seo_goals" in prof_data

        # Test pipeline status query with mock job in active_jobs
        ranking_pipeline.active_jobs["test_pipeline_job"] = {
            "job_id": "test_pipeline_job",
            "website_id": 1,
            "domain": "mywebsite.org",
            "status": "in_progress",
            "current_stage": 1,
            "total_stages": 10,
            "stages": [
                {"id": 1, "title": "Understand Business & Target Audience", "status": "completed", "details": "Done", "output": "Profile"},
                {"id": 2, "title": "Research Keywords & Search Intent", "status": "running", "details": "Clustering", "output": "Keywords"},
                {"id": 3, "title": "Comprehensive Website Audit", "status": "pending", "details": "", "output": "Audit"},
                {"id": 4, "title": "Fix Technical SEO Barriers", "status": "pending", "details": "", "output": "Fixes"},
                {"id": 5, "title": "Optimize Every Important Page", "status": "pending", "details": "", "output": "Onpage"},
                {"id": 6, "title": "Create Useful, Original Content", "status": "pending", "details": "", "output": "Gaps"},
                {"id": 7, "title": "Internal Links & Website Authority", "status": "pending", "details": "", "output": "Links"},
                {"id": 8, "title": "Submit & Monitor Indexing in GSC", "status": "pending", "details": "", "output": "GSC"},
                {"id": 9, "title": "Measure Rankings & Organic Performance", "status": "pending", "details": "", "output": "Rankings"},
                {"id": 10, "title": "Repeat & Improve Automatically", "status": "pending", "details": "", "output": "Continuous"}
            ],
            "logs": [],
            "error": None
        }

        resp_stat = await client.get("/api/pipeline/status/test_pipeline_job", headers=headers)
        assert resp_stat.status_code == 200
        stat_data = resp_stat.json()
        assert stat_data["total_stages"] == 10
        assert len(stat_data["stages"]) == 10
        assert stat_data["stages"][0]["title"] == "Understand Business & Target Audience"

@pytest.mark.asyncio
async def test_full_seo_ranking_pipeline_execution():
    pipeline = FullSEORankingPipeline()

    mock_crawl = [
        {
            "url": "https://samplebrand.org/",
            "status_code": 200,
            "title": "Sample Brand - Enterprise Solutions",
            "meta_description": "We offer software and technology tools for enterprises.",
            "h1": "Enterprise Software Solutions",
            "canonical": "https://samplebrand.org/",
            "images_without_alt": 0,
            "issues": []
        }
    ]

    with patch("agent.workflows.ranking_pipeline.SEOSpider") as mock_spider, \
         patch("agent.workflows.ranking_pipeline.GSCPropertyManager") as mock_gsc, \
         patch("agent.workflows.ranking_pipeline.GSCSitemapsManager") as mock_sm, \
         patch("agent.workflows.ranking_pipeline.GSCURLInspector") as mock_ins, \
         patch("agent.workflows.ranking_pipeline.GSCPerformanceAnalyzer") as mock_perf, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:

        mock_http_get.return_value = MagicMock(status_code=200, text="User-agent: *\nDisallow: /wp-admin/\nSitemap: https://samplebrand.org/sitemap.xml")
        mock_spider.return_value.run = AsyncMock(return_value=mock_crawl)
        mock_gsc.return_value.open_search_console = AsyncMock(return_value={"needs_login": False})
        mock_sm.return_value.navigate_to_sitemaps = AsyncMock(return_value={"status": "navigated"})
        mock_sm.return_value.submit_sitemap = AsyncMock(return_value={"message": "Submitted"})
        mock_ins.return_value.inspect_url = AsyncMock(return_value={"can_request_indexing": True})
        mock_ins.return_value.request_indexing = AsyncMock(return_value={"message": "Indexing requested"})
        mock_perf.return_value.navigate_to_performance = AsyncMock(return_value={"success": True})
        mock_perf.return_value.extract_queries_table = AsyncMock(return_value=[
            {"query": "enterprise software", "clicks": "10", "impressions": "200", "ctr": "5.0%", "position": "4.2"}
        ])

        # Execute on existing website #1
        result = await pipeline.execute_pipeline(website_id=1, job_id="test_ranking_run_1")
        assert result["status"] == "completed"
        assert result["total_stages"] == 10
        assert len(result["stages"]) == 10
        for s in result["stages"]:
            assert s["status"] == "completed"
