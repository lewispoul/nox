import asyncio
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routes.predict import router as predict_router
from api.routes.jobs import router as jobs_router
from api.services import queue as q


@pytest.mark.asyncio
async def test_predict_cj_with_mock_runner(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)

    def fake_cj(payload):
        return {
            "scalars": {"Pcj_Pa": 2.0e9, "Tcj_K": 3000.0, "Dcj_m_per_s": 8000.0},
            "series": {"composition": [["H2O", 0.5], ["CO2", 0.5]]},
            "artifacts": [],
            "returncode": 0,
        }

    q.set_cj_runner(fake_cj)

    app = FastAPI()
    app.include_router(predict_router)
    app.include_router(jobs_router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/predict/cj",
            json={"reactants": {"H2": 2, "O2": 1}, "T0": 300.0, "P0": 101325.0},
        )
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        deadline = time.time() + 5
        state = r.json()["state"]
        while state not in {"done", "failed"} and time.time() < deadline:
            await asyncio.sleep(0.05)
            r2 = await client.get(f"/jobs/{job_id}")
            state = r2.json()["state"]
        assert state == "done"
