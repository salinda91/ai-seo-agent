import pytest
import pytest_asyncio
import httpx
from agent.api.main import app
from agent.core.config import settings

@pytest.mark.asyncio
async def test_api_status_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["app_name"] == "AI SEO Automation Agent"
        assert "chrome_profile" in data

@pytest.mark.asyncio
async def test_token_authentication_protection():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Request without token -> 401 Unauthorized
        resp = await client.get("/api/websites")
        assert resp.status_code == 401

        # Request with invalid token -> 401 Unauthorized
        resp = await client.get("/api/websites", headers={"X-Agent-Token": "bad_token"})
        assert resp.status_code == 401

        # Request with valid token -> 200 OK
        resp = await client.get("/api/websites", headers={"X-Agent-Token": settings.agent_token})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
