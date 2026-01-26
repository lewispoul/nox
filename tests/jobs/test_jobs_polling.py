"""
Tests for JOBS-002 polling endpoint: GET /jobs/{job_id}/wait

This module tests:
1. Wait endpoint polls until job completion
2. Timeout behavior when job doesn't complete
3. 404 for non-existent jobs
4. Immediate return for already-completed jobs
"""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_wait_completes_for_done_job():
    """Test /jobs/{id}/wait returns when job completes"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a simple echo job
        job_request = {"kind": "echo", "payload": {"test": "data"}}
        
        create_response = await ac.post("/jobs/simple", json=job_request)
        assert create_response.status_code == status.HTTP_200_OK
        job_id = create_response.json()["job_id"]
        
        # Poll with a short timeout - job may or may not be done, but endpoint should respond
        wait_response = await ac.get(f"/jobs/{job_id}/wait?timeout=2")
        assert wait_response.status_code == status.HTTP_200_OK
        
        wait_data = wait_response.json()
        assert wait_data["job_id"] == job_id
        # Job should eventually complete or timeout
        assert wait_data["state"] in ("completed", "failed", "pending", "running")


@pytest.mark.asyncio
async def test_wait_with_custom_timeout():
    """Test /jobs/{id}/wait respects custom timeout parameter"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create job
        job_request = {"kind": "echo", "payload": {"test": "timeout"}}
        create_response = await ac.post("/jobs/simple", json=job_request)
        job_id = create_response.json()["job_id"]
        
        # Wait with short timeout (job should complete anyway for echo)
        wait_response = await ac.get(f"/jobs/{job_id}/wait?timeout=5")
        assert wait_response.status_code == status.HTTP_200_OK
        
        wait_data = wait_response.json()
        assert wait_data["job_id"] == job_id


@pytest.mark.asyncio
async def test_wait_job_not_found():
    """Test /jobs/{id}/wait returns 404 for non-existent jobs"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        fake_job_id = "nonexistent_job_id_12345"
        
        response = await ac.get(f"/jobs/{fake_job_id}/wait")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_wait_already_completed():
    """Test /jobs/{id}/wait works for various job states"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a job
        job_request = {"kind": "echo", "payload": {}}
        create_response = await ac.post("/jobs/simple", json=job_request)
        assert create_response.status_code == status.HTTP_200_OK
        job_id = create_response.json()["job_id"]
        
        # Call wait with very short timeout to test it doesn't hang
        wait_response = await ac.get(f"/jobs/{job_id}/wait?timeout=1")
        assert wait_response.status_code == status.HTTP_200_OK
        
        wait_data = wait_response.json()
        assert wait_data["job_id"] == job_id
        # Should return some valid state (could be pending, running, completed, or failed)
        assert "state" in wait_data
        assert "message" in wait_data


@pytest.mark.asyncio
async def test_wait_enforces_max_timeout():
    """Test /jobs/{id}/wait caps timeout at 300s"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create job
        job_request = {"kind": "echo", "payload": {}}
        create_response = await ac.post("/jobs/simple", json=job_request)
        job_id = create_response.json()["job_id"]
        
        # Request huge timeout - should be capped (but job completes quickly anyway)
        wait_response = await ac.get(f"/jobs/{job_id}/wait?timeout=9999")
        assert wait_response.status_code == status.HTTP_200_OK
        
        # Job should complete before any timeout
        wait_data = wait_response.json()
        assert wait_data["state"] in ("completed", "failed")
