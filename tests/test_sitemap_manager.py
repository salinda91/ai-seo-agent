import os
import tempfile
import subprocess
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from agent.workflows.sitemap import SitemapManager, sitemap_manager
from agent.api.main import app
from agent.core.config import settings

@pytest.mark.asyncio
async def test_generate_sitemap_xml():
    mgr = SitemapManager()
    urls = [
        "https://example.com/",
        "https://example.com/stay",
        "https://example.com/dine"
    ]
    xml = mgr.generate_sitemap_xml(urls, "example.com")
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in xml
    assert '<loc>https://example.com/</loc>' in xml
    assert '<priority>1.0</priority>' in xml
    assert '<loc>https://example.com/stay</loc>' in xml
    assert '<priority>0.8</priority>' in xml

@pytest.mark.asyncio
async def test_check_sitemap_live_not_available():
    mgr = SitemapManager()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        mock_get.return_value = mock_resp

        res = await mgr.check_sitemap_live("example.com")
        assert res["available"] is False
        assert res["status_code"] == 404
        assert "No valid XML sitemap detected" in res["details"]

@pytest.mark.asyncio
async def test_check_sitemap_live_available():
    mgr = SitemapManager()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<?xml version="1.0"?><urlset><url><loc>https://example.com/</loc></url></urlset>'
        mock_get.return_value = mock_resp

        res = await mgr.check_sitemap_live("example.com")
        assert res["available"] is True
        assert res["status_code"] == 200

@pytest.mark.asyncio
async def test_deploy_sitemap_to_codebase():
    mgr = SitemapManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_dir, capture_output=True, check=True)

        # Create public folder (standard Laravel / Next.js / Vite structure)
        pub = os.path.join(tmp_dir, "public")
        os.makedirs(pub, exist_ok=True)
        with open(os.path.join(pub, "index.html"), "w", encoding="utf-8") as f:
            f.write("<html><body>Home</body></html>")

        subprocess.run(["git", "add", "."], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_dir, capture_output=True, check=True)

        xml = mgr.generate_sitemap_xml(["https://example.com/"], "example.com")
        deploy_res = await mgr.deploy_sitemap_to_codebase(
            repo_path=Path(tmp_dir),
            domain="example.com",
            xml_content=xml
        )

        assert deploy_res["success"] is True
        assert os.path.exists(os.path.join(pub, "sitemap.xml"))
        assert os.path.exists(os.path.join(pub, "robots.txt"))

        # Verify robots.txt references sitemap
        with open(os.path.join(pub, "robots.txt"), "r", encoding="utf-8") as rf:
            robots_txt = rf.read()
        assert "Sitemap: https://example.com/sitemap.xml" in robots_txt

@pytest.mark.asyncio
async def test_sitemap_api_endpoints():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Agent-Token": settings.agent_token}

        # Status endpoint (Website ID 1)
        resp = await client.get("/api/sitemap/status/1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        assert "sitemap_url" in data
        assert "can_create_and_upload" in data
