"""Test helpers for reducing duplication across test suites."""

import asyncio
import time
from typing import Literal, Optional

from httpx import AsyncClient

from api.services.jobs_store import get_store


async def wait_for_job_done(
    job_id: str,
    client: Optional[AsyncClient] = None,
    timeout: float = 5.0,
    poll_delay: float = 0.05,
) -> Literal["done", "failed"]:
    """
    Poll job state until done/failed or timeout.

    Args:
        job_id: Job identifier
        client: Optional AsyncClient for API polling; if None, polls store directly
        timeout: Maximum seconds to wait
        poll_delay: Seconds between polls

    Returns:
        Final state ("done" or "failed")
    """
    deadline = time.time() + timeout

    if client:
        # API polling mode
        r = await client.get(f"/jobs/{job_id}")
        state = r.json()["state"]
        while state not in {"done", "failed"} and time.time() < deadline:
            await asyncio.sleep(poll_delay)
            r = await client.get(f"/jobs/{job_id}")
            state = r.json()["state"]
    else:
        # Store polling mode
        store = get_store()
        state = store.get(job_id).state
        while state not in {"done", "failed"} and time.time() < deadline:
            await asyncio.sleep(poll_delay)
            state = store.get(job_id).state

    return state
