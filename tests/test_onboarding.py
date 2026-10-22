import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from agent.api.main import app
from agent.core.config import settings
from agent.workflows.onboarding import domain_onboarding, DomainOnboardingManager

@pytest.mark.asyncio
async def test_onboarding_api_unauthorized():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/onboarding/start", json={"domain": "testdomain.com"})
        assert resp.status_code == 401

@pytest.mark.asyncio
async def test_onboarding_api_start_and_status():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Agent-Token": settings.agent_token}
        
        with patch("agent.api.routes.onboarding._run_onboarding_task", new_callable=AsyncMock):
            resp = await client.post(
                "/api/onboarding/start",
                json={
                    "domain": "https://newtestsite.org/",
                    "name": "New Test Site",
                    "cms_type": "wordpress",
                    "automation_mode": "supervised",
                    "is_domain_property": False
                },
                headers=headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "job_id" in data
            assert data["domain"] == "newtestsite.org"
            
            job_id = data["job_id"]
            
            # Setup state in memory for status endpoint test
            domain_onboarding.active_jobs[job_id] = {
                "job_id": job_id,
                "domain": "newtestsite.org",
                "status": "in_progress",
                "current_step": 1,
                "total_steps": 7,
                "steps": [
                    {"id": 1, "title": "Domain Registration", "status": "running", "details": ""},
                    {"id": 2, "title": "Google Search Console Property", "status": "pending", "details": ""},
                    {"id": 3, "title": "Sitemap Discovery & Submission", "status": "pending", "details": ""},
                    {"id": 4, "title": "Technical SEO Crawl & Audit", "status": "pending", "details": ""},
                    {"id": 5, "title": "Homepage Indexing Inspection", "status": "pending", "details": ""},
                    {"id": 6, "title": "AI Keyword Opportunities", "status": "pending", "details": ""},
                    {"id": 7, "title": "Prioritized SEO Optimization Roadmap", "status": "pending", "details": ""},
                ],
                "logs": [],
                "website_id": 1,
                "error": None
            }
            
            resp_status = await client.get(f"/api/onboarding/status/{job_id}", headers=headers)
            assert resp_status.status_code == 200
            status_data = resp_status.json()
            assert status_data["domain"] == "newtestsite.org"
            assert len(status_data["steps"]) == 7
            assert status_data["steps"][0]["title"] == "Domain Registration"

@pytest.mark.asyncio
async def test_domain_onboarding_manager_flow():
    manager = DomainOnboardingManager()
    
    mock_crawl = [
        {
            "url": "https://samplebrand.org/",
            "status_code": 200,
            "title": "Sample Brand - Leading Solutions",
            "meta_description": "We provide top tier technology and software solutions.",
            "h1": "Welcome to Sample Brand",
            "canonical": "https://samplebrand.org/",
            "images_without_alt": 0,
            "issues": []
        }
    ]
    
    with patch("agent.workflows.onboarding.GSCPropertyManager") as mock_gsc, \
         patch("agent.workflows.onboarding.SEOSpider") as mock_spider, \
         patch("agent.workflows.onboarding.GSCSitemapsManager") as mock_sm, \
         patch("agent.workflows.onboarding.GSCURLInspector") as mock_ins, \
         patch("agent.workflows.onboarding.GSCPerformanceAnalyzer") as mock_perf, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http_get:
        
        mock_http_get.return_value = MagicMock(status_code=200, text="Sitemap: https://samplebrand.org/sitemap.xml\n")
        mock_gsc.return_value.open_search_console = AsyncMock(return_value={"needs_login": False})
        mock_gsc.return_value.add_property = AsyncMock(return_value={"is_verified": True, "instructions": "Verified"})
        mock_spider.return_value.run = AsyncMock(return_value=mock_crawl)
        mock_sm.return_value.navigate_to_sitemaps = AsyncMock(return_value={"status": "navigated"})
        mock_sm.return_value.submit_sitemap = AsyncMock(return_value={"message": "Submitted"})
        mock_ins.return_value.inspect_url = AsyncMock(return_value={"can_request_indexing": True})
        mock_ins.return_value.request_indexing = AsyncMock(return_value={"message": "Indexing requested"})
        mock_perf.return_value.navigate_to_performance = AsyncMock(return_value={"success": True})
        mock_perf.return_value.extract_queries_table = AsyncMock(return_value=[
            {"query": "solutions", "clicks": "2", "impressions": "50", "ctr": "4.0%", "position": "10.0"}
        ])
        
        result = await manager.execute_onboarding(
            domain="samplebrand.org",
            name="Sample Brand",
            cms_type="wordpress",
            automation_mode="supervised",
            job_id="test_job_123"
        )
        
        assert result["status"] == "completed"
        assert result["website_id"] is not None
        assert len(result["steps"]) == 12
        for step in result["steps"]:
            assert step["status"] == "completed"
