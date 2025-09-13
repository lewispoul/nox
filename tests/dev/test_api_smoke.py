import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_smoke_docs_or_404():
    """Smoke test demonstrating ASGITransport (no server needed)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/docs")
        assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_smoke_jobs_endpoint_if_present():
    """Test jobs endpoint if it exists"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/jobs/nonexistent")
        # Should be 404 (endpoint exists) or 405 (method not allowed)
        # but not 500 (server error)
        assert r.status_code in (404, 405)
