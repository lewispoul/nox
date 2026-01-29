import asyncio
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routes.agent import router as agent_router
from api.routes.jobs import router as jobs_router
from api.services import queue as q


@pytest.mark.asyncio
async def test_agent_run_and_ask_with_mocks(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)

    q.set_xtb_runner(
        lambda payload: {
            "scalars": {"E_total_hartree": -1.0},
            "series": {},
            "artifacts": [],
            "returncode": 0,
        }
    )
    q.set_psi4_runner(
        lambda payload: {
            "scalars": {"E_total_hartree": -2.0},
            "series": {},
            "artifacts": [],
            "returncode": 0,
        }
    )

    app = FastAPI()
    app.include_router(agent_router)
    app.include_router(jobs_router)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # agent.run for xtb
        r1 = await client.post(
            "/agent/run",
            json={
                "intent": "xtb.opt",
                "params": {
                    "engine": "xtb",
                    "kind": "opt_properties",
                    "inputs": {
                        "xyz": "1\nH\nH 0 0 0\n",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                },
            },
        )
        assert r1.status_code == 200
        job_id = r1.json()["job_id"]
        deadline = time.time() + 5
        state = r1.json()["state"]
        while state not in {"done", "failed"} and time.time() < deadline:
            await asyncio.sleep(0.05)
            r2 = await client.get(f"/jobs/{job_id}")
            state = r2.json()["state"]
        assert state == "done"

        # agent.ask with psi4 keyword
        r3 = await client.post(
            "/agent/ask",
            headers={"X-Session-Id": "t1"},
            json={
                "q": "please run psi4 on this xyz",
                "params": {
                    "engine": "psi4",
                    "kind": "opt_scf_freq",
                    "inputs": {
                        "xyz": "2\nWater\nO 0 0 0\nH 0 0 1\n",
                        "charge": 0,
                        "multiplicity": 1,
                    },
                },
            },
        )
        assert r3.status_code == 200
        job_id2 = r3.json()["job_id"]
        state = r3.json()["state"]
        deadline = time.time() + 5
        while state not in {"done", "failed"} and time.time() < deadline:
            await asyncio.sleep(0.05)
            r4 = await client.get(f"/jobs/{job_id2}")
            state = r4.json()["state"]
        assert state == "done"
