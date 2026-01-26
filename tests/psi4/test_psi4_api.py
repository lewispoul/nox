import asyncio
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routes.jobs import router as jobs_router
from api.services import queue as q


@pytest.mark.asyncio
async def test_submit_psi4_job_with_mock_runner(monkeypatch):
    # Force local queue mode
    monkeypatch.delenv("REDIS_URL", raising=False)

    def fake_runner(_payload):
        return {
            "scalars": {"E_total_hartree": -40.0},
            "series": {"vibfreq_cm^-1": [1000.0, 1500.0]},
            "artifacts": [],
            "returncode": 0,
        }

    q.set_psi4_runner(fake_runner)

    app = FastAPI()
    app.include_router(jobs_router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        req = {
            "engine": "psi4",
            "kind": "opt_scf_freq",
            "inputs": {
                "xyz": "2\nWater\nO 0 0 0\nH 0 0 1\n",
                "charge": 0,
                "multiplicity": 1,
                "params": {"method": "HF", "basis": "6-31G*", "opt": True},
            },
        }
        r = await client.post("/jobs", json=req)
        assert r.status_code == 200
        data = r.json()
        job_id = data["job_id"]
        deadline = time.time() + 5
        state = data["state"]
        while state not in {"done", "failed"} and time.time() < deadline:
            await asyncio.sleep(0.05)
            r2 = await client.get(f"/jobs/{job_id}")
            state = r2.json()["state"]
        assert state == "done"
