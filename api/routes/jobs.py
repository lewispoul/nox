from __future__ import annotations

from typing import Any, Dict, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from api.schemas.job import JobRequest, JobStatus
from api.schemas.psi4_job import Psi4JobRequest
from api.schemas.result import Artifact, ResultBundle
from api.services.jobs_store import get_store
from api.services.queue import submit_job

router = APIRouter()


class SimpleJobRequest(BaseModel):
    kind: str = "echo"
    payload: Dict[str, Any] = {}


@router.post("/jobs")
async def create_job(body: Union[SimpleJobRequest, Psi4JobRequest, JobRequest]):
    """Create a job - supports simple, XTB, and Psi4 job formats.
    
    The request type is automatically determined by the request body structure:
    - SimpleJobRequest: {kind: str, payload: dict} - for simple echo jobs
    - Psi4JobRequest: {engine: "psi4", kind: str, inputs: {...}} - for Psi4 calculations
    - JobRequest: {engine: "xtb", kind: str, inputs: {...}} - for XTB calculations
    
    Note: FastAPI validates against each union member in order. If you receive
    unexpected validation errors, ensure your request matches one of the schemas above.
    Alternatively, use the dedicated /jobs/simple endpoint for simple jobs.
    """
    try:
        # SimpleJobRequest
        if isinstance(body, SimpleJobRequest):
            job_id = submit_job(body.kind, body.payload)
            j = get_store().get(job_id)
            if j is None:
                raise HTTPException(500, "Failed to create job")
            return {"job_id": job_id, "state": j.state}

        # Psi4JobRequest
        if isinstance(body, Psi4JobRequest):
            payload = {"job_request": body.model_dump()}
            job_id = submit_job("psi4", payload)
            return JobStatus(
                job_id=job_id,
                state="pending",
                message="Psi4 job queued for processing",
            )

        # JobRequest (XTB or default)
        if isinstance(body, JobRequest):
            payload = {"job_request": body.model_dump()}
            job_id = submit_job("xtb", payload)
            return JobStatus(
                job_id=job_id,
                state="pending",
                message="Job queued for processing",
            )

    except ValidationError as e:
        raise HTTPException(422, f"Invalid job request format: {e}")
    except Exception as e:
        raise HTTPException(400, f"Invalid request: {str(e)}")


@router.post("/jobs/simple")
def create_simple_job(req: SimpleJobRequest):
    """Create a simple job (echo, etc.) - legacy endpoint"""
    job_id = submit_job(req.kind, req.payload)
    j = get_store().get(job_id)
    if j is None:
        raise HTTPException(500, "Failed to create job")
    return {"job_id": job_id, "state": j.state}


@router.get("/jobs/{job_id}")
def get_job_simple(job_id: str):
    """Get job status (raw format) - primary endpoint for simple jobs"""
    j = get_store().get(job_id)
    if not j:
        raise HTTPException(404, detail="Job not found")
    # Convert id to job_id for consistency
    result = j.to_dict()
    if "id" in result:
        result["job_id"] = result.pop("id")
    return result


@router.get("/jobs/{job_id}/status", response_model=JobStatus)
def get_job_status(job_id: str):
    """Get job status (JobStatus format with state mapping)"""
    j = get_store().get(job_id)
    if not j:
        raise HTTPException(404, "Job not found")

    # Map our job states to the expected states
    state_mapping = {
        "queued": "pending",
        "running": "running",
        "done": "completed",
        "failed": "failed",
    }

    return JobStatus(
        job_id=job_id,
        state=state_mapping.get(j.state, j.state),
        message=j.error or "Job processing",
    )


@router.get("/jobs/{job_id}/artifacts", response_model=ResultBundle)
def get_artifacts(job_id: str):
    """Get job results and artifacts if calculation is completed"""
    j = get_store().get(job_id)
    if not j or j.state != "done" or not j.result:
        raise HTTPException(404, "Result not available")

    rb = j.result

    # Convert dict artifacts to Artifact objects for proper validation
    artifacts = []
    for art_dict in rb.get("artifacts", []):
        artifacts.append(Artifact(**art_dict))

    return ResultBundle(
        scalars=rb.get("scalars", {}), series=rb.get("series", {}), artifacts=artifacts
    )


@router.get("/jobs/{job_id}/wait")
async def wait_for_job(job_id: str, timeout: int = 30):
    """Poll job until completion or timeout.
    
    Args:
        job_id: Job identifier
        timeout: Maximum seconds to wait (default 30, max 300)
        
    Returns:
        JobStatus with final state (completed/failed) or current state if timeout
    """
    import asyncio
    
    if timeout > 300:
        timeout = 300
    if timeout < 1:
        timeout = 1
        
    elapsed = 0
    poll_interval = 0.5  # 500ms between polls
    
    while elapsed < timeout:
        j = get_store().get(job_id)
        if not j:
            raise HTTPException(404, "Job not found")
            
        # Map internal states to API states
        state_mapping = {
            "queued": "pending",
            "running": "running",
            "done": "completed",
            "failed": "failed",
        }
        api_state = state_mapping.get(j.state, j.state)
        
        # Terminal states - return immediately
        if j.state in ("done", "failed"):
            return JobStatus(
                job_id=job_id,
                state=api_state,
                message=j.error or "Job completed",
            )
            
        # Non-terminal state - wait and poll again
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        
    # Timeout reached - return current state
    j = get_store().get(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
        
    state_mapping = {
        "queued": "pending",
        "running": "running",
        "done": "completed",
        "failed": "failed",
    }
    
    return JobStatus(
        job_id=job_id,
        state=state_mapping.get(j.state, j.state),
        message=f"Timeout after {timeout}s - job still {j.state}",
    )
