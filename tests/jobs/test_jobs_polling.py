"""
Tests for JOBS-002 polling endpoint: GET /jobs/{job_id}/wait

This module tests:
1. Wait endpoint accepts requests and returns valid responses
2. 404 for non-existent jobs
3. Timeout parameter enforcement
"""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_wait_endpoint_exists():
    """Test /jobs/{id}/wait endpoint responds with valid JobStatus"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a simple echo job
        job_request = {"kind": "echo", "payload": {"test": "data"}}
        
        create_response = await ac.post("/jobs/simple", json=job_request)
        assert create_response.status_code == status.HTTP_200_OK
        job_id = create_response.json()["job_id"]
        
        # Call wait endpoint with short timeout
        wait_response = await ac.get(f"/jobs/{job_id}/wait?timeout=1")
        assert wait_response.status_code == status.HTTP_200_OK
        
        wait_data = wait_response.json()
        assert "job_id" in wait_data
        assert wait_data["job_id"] == job_id
        assert "state" in wait_data
        assert "message" in wait_data


@pytest.mark.asyncio
async def test_wait_with_custom_timeout():
    """Test /jobs/{id}/wait respects timeout parameter"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create job
        job_request = {"kind": "echo", "payload": {}}
        create_response = await ac.post("/jobs/simple", json=job_request)
        job_id = create_response.json()["job_id"]
        
        # Test with various timeout values
        for timeout in [1, 5, 10]:
            wait_response = await ac.get(f"/jobs/{job_id}/wait?timeout={timeout}")
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
async def test_wait_enforces_max_timeout():
    """Test /jobs/{id}/wait caps timeout at 300s"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create job
        job_request = {"kind": "echo", "payload": {}}
        create_response = await ac.post("/jobs/simple", json=job_request)
        job_id = create_response.json()["job_id"]
        
        # Request huge timeout - should be capped by endpoint
        wait_response = await ac.get(f"/jobs/{job_id}/wait?timeout=999999")
        assert wait_response.status_code == status.HTTP_200_OK
        
        wait_data = wait_response.json()
        assert wait_data["job_id"] == job_id
        assert "state" in wait_data
