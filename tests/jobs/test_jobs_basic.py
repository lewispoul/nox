"""
Tests for JOBS-002: Activate Dramatiq jobs from API with state polling

This module tests:
1. Job creation via POST /jobs
2. Job status polling via GET /jobs/{id}
3. Artifact retrieval via GET /jobs/{id}/artifacts
4. Complete workflow: submit → poll → results
"""

import uuid

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.main import app

print("Module loaded successfully")  # Debug print


@pytest.mark.asyncio
async def test_job_creation():
    """Test POST /jobs creates job and returns pending status"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        job_request = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
                "charge": 0,
                "multiplicity": 1,
                "params": {"cubes": False},
            },
        }

        response = await ac.post("/jobs", json=job_request)
        assert response.status_code == status.HTTP_200_OK

        job_data = response.json()
        assert "job_id" in job_data
        assert job_data["state"] == "pending"
        assert job_data["message"] == "Job queued for processing"
        assert job_data["progress"] == 0.0

        # Validate job_id format (UUID hex without dashes)
        job_id = job_data["job_id"]
        assert len(job_id) == 32
        uuid.UUID(job_id)  # Should not raise exception


@pytest.mark.asyncio
async def test_job_status_polling():
    """Test GET /jobs/{id} returns job status correctly"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create job first
        job_request = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
                "charge": 0,
                "multiplicity": 1,
            },
        }

        create_response = await ac.post("/jobs", json=job_request)
        job_id = create_response.json()["job_id"]

        # Poll job status
        status_response = await ac.get(f"/jobs/{job_id}/status")
        assert status_response.status_code == status.HTTP_200_OK

        status_data = status_response.json()
        assert status_data["job_id"] == job_id
        valid_states = ["pending", "running", "completed", "failed"]
        assert status_data["state"] in valid_states
        assert "message" in status_data
        assert "progress" in status_data


@pytest.mark.asyncio
async def test_job_not_found():
    """Test GET /jobs/{id} with non-existent job returns 404"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        fake_job_id = "nonexistent_job_id"

        response = await ac.get(f"/jobs/{fake_job_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_artifacts_not_ready():
    """Test GET /jobs/{id}/artifacts returns 404 for pending jobs"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create job
        job_request = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
                "charge": 0,
                "multiplicity": 1,
            },
        }

        create_response = await ac.post("/jobs", json=job_request)
        job_id = create_response.json()["job_id"]

        # Try to get artifacts immediately (should be pending)
        artifacts_response = await ac.get(f"/jobs/{job_id}/artifacts")
        assert artifacts_response.status_code == status.HTTP_404_NOT_FOUND
        expected_detail = "Result not available"
        assert artifacts_response.json()["detail"] == expected_detail


@pytest.mark.asyncio
async def test_job_with_cube_generation():
    """Test job creation with cube generation parameter"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        job_request = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
                "charge": 0,
                "multiplicity": 1,
                "params": {"cubes": True},  # Enable cube generation
            },
        }

        response = await ac.post("/jobs", json=job_request)
        assert response.status_code == status.HTTP_200_OK

        job_data = response.json()
        assert job_data["state"] == "pending"
        assert "job_id" in job_data
