import asyncio
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routes.jobs import router as jobs_router


@pytest.mark.asyncio
async def test_jobs_echo_flow_local_mode(monkeypatch):
    # Force local mode (no Redis)
    monkeypatch.delenv("REDIS_URL", raising=False)
    app = FastAPI()
    app.include_router(jobs_router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/jobs", json={"kind": "echo", "payload": {"x": 1}})
        assert r.status_code == 200
        job = r.json()
        job_id = job["job_id"]
        assert job["state"] in {"queued", "running", "done"}
        deadline = time.time() + 5
        state = job["state"]
        while state not in {"done", "failed"} and time.time() < deadline:
            await asyncio.sleep(0.05)
            r2 = await client.get(f"/jobs/{job_id}")
            state = r2.json()["state"]
        assert state == "done"


@pytest.mark.asyncio
async def test_jobs_store_redis_via_fakeredis(monkeypatch):
    # Validate Redis store behavior without real Redis
    import fakeredis

    from api.services import jobs_store as js

    fake = fakeredis.FakeRedis()
    store = js.RedisJobsStore(fake)
    j = store.create()
    assert j.state == "queued"
    store.set_state(j.id, "running")
    got = store.get(j.id)
    assert got.state == "running"
    store.set_state(j.id, "done", result={"ok": True})
    got2 = store.get(j.id)
    assert got2.state == "done" and got2.result == {"ok": True}
