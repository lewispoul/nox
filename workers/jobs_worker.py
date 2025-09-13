from __future__ import annotations

import os
import time
from typing import Any, Dict

import dramatiq

from api.services.jobs_store import get_store

# Set up Dramatiq broker
try:
    from dramatiq.brokers.redis import RedisBroker

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    broker = RedisBroker(url=REDIS_URL)
except Exception:
    from dramatiq.brokers.stub import StubBroker

    broker = StubBroker()

dramatiq.set_broker(broker)


@dramatiq.actor
def enqueue_job(job_id: str, kind: str, payload: Dict[str, Any]):
    """Dramatiq actor for handling different job types"""
    store = get_store()
    try:
        store.set_state(job_id, "running")

        if kind == "echo":
            time.sleep(0.05)
            result = {"echo": payload}
        elif kind == "xtb":
            # Handle XTB calculation
            result = run_xtb_calculation(payload)
        else:
            result = {"echo": payload}

        store.set_state(job_id, "done", result=result)
    except Exception as e:  # noqa: BLE001
        store.set_state(job_id, "failed", error=str(e))


def run_xtb_calculation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute XTB calculation with given parameters"""
    from ai.runners.xtb import run_xtb_job
    from api.schemas.job import JobRequest
    from api.services.storage import job_dir

    # Parse the job request
    job_request_json = payload.get("job_request", "{}")
    try:
        JR = JobRequest.model_validate_json(job_request_json)
    except Exception as e:
        raise ValueError(f"Invalid job request: {e}")

    job_id = payload.get("job_id", "unknown")
    jd = job_dir(job_id)

    result = run_xtb_job(
        jd,
        JR.inputs.xyz,
        JR.inputs.charge,
        JR.inputs.multiplicity,
        JR.inputs.params.model_dump(),
    )

    # XTB success: return code 0 OR (return code 2 with valid energy results)
    has_energy = result.get("scalars", {}).get("E_total_hartree") is not None
    success = (result.get("returncode") == 0) or (
        result.get("returncode") == 2 and has_energy
    )

    if not success:
        error_msg = (
            f"XTB calculation failed with return code {result.get('returncode')}"
        )
        raise RuntimeError(error_msg)

    return result
