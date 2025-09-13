import asyncio
import os
import time

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

TERMINAL = {"done", "completed", "failed"}


async def _poll_status(client, job_id: str, timeout_s: float = 10.0):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        r = await client.get(f"/jobs/{job_id}")
        r.raise_for_status()
        last = r.json()
        state = last.get("state")
        if state in TERMINAL:
            return last
        await asyncio.sleep(0.05)
    return last


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_echo_local_mode(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        payload = {
            "kind": "echo",
            "payload": {"x": 42, "msg": "hello"},
        }  # Adjusted to match SimpleJobRequest
        r = await c.post("/jobs", json=payload)
        assert r.status_code == 200
        job = r.json()
        job_id = job.get("job_id")
        assert job.get("state") in {"queued", "pending", "running", "done", "completed"}
        final = await _poll_status(c, job_id, timeout_s=5.0)
        assert final and final.get("state") in {"done", "completed"}
        res = final.get("result") or final
        assert res.get("payload", {}).get("x") == 42
        assert res.get("payload", {}).get("msg") == "hello"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_xtb_with_cubes(monkeypatch):
    if not os.getenv("REDIS_URL"):
        monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        job_req = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
                "charge": 0,
                "multiplicity": 1,
                "params": {"cubes": True},
            },
        }
        r = await c.post("/jobs", json=job_req)
        assert r.status_code == 200
        job = r.json()
        job_id = job.get("job_id")
        final = await _poll_status(c, job_id, timeout_s=10.0)
        assert final and final.get("state") in {"done", "completed", "failed"}
        r_art = await c.get(f"/jobs/{job_id}/artifacts")
        assert r_art.status_code in {200, 404}
        if r_art.status_code == 200:
            data = r_art.json()
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                assert "artifacts" in data
