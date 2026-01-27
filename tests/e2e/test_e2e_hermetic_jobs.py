import shutil

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routes.jobs import router as jobs_router
from api.routes.predict import router as predict_router
from api.services import queue as q
from tests.helpers import wait_for_job_done


async def _run_job_and_get_result(app, payload, endpoint="/jobs"):
    """Helper to run a job and retrieve its result."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(endpoint, json=payload)
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        state = await wait_for_job_done(job_id, client=client)
        assert state == "done"

        r3 = await client.get(f"/jobs/{job_id}")
        return r3.json().get("result", {})


@pytest.mark.asyncio
async def test_e2e_xtb_cubes_hermetic(monkeypatch):
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr("nox.runners.xtb.shutil.which", lambda _: None)

    app = FastAPI()
    app.include_router(jobs_router)

    payload = {
        "engine": "xtb",
        "kind": "opt_properties",
        "inputs": {
            "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
            "charge": 0,
            "multiplicity": 1,
            "params": {"gfn": 2, "cubes": True},
        },
    }

    result = await _run_job_and_get_result(app, payload)
    artifacts = result.get("artifacts", [])
    names = {a.get("name") for a in artifacts}
    assert {"homo.cube", "lumo.cube"} <= names
    scalars = result.get("scalars", {})
    assert scalars.get("E_total_hartree") is not None


@pytest.mark.asyncio
async def test_e2e_cj_hermetic(monkeypatch):
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr("nox.chemistry.cj._has_cantera", lambda: False)

    app = FastAPI()
    app.include_router(predict_router)
    app.include_router(jobs_router)

    payload = {"reactants": {"H2": 2, "O2": 1}, "T0": 300.0, "P0": 101325.0}

    result = await _run_job_and_get_result(app, payload, endpoint="/predict/cj")
    artifacts = result.get("artifacts", [])
    assert any(a.get("name") == "cj_results.csv" for a in artifacts)
    scalars = result.get("scalars", {})
    assert scalars.get("Pcj_Pa") is not None
    assert scalars.get("Tcj_K") is not None


@pytest.mark.asyncio
async def test_e2e_xtb_with_mock_runner(monkeypatch):
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)

    orig = q._xtb_runner

    def fake_xtb_runner(payload):
        return {
            "scalars": {"E_total_hartree": -12.34, "gap_eV": 1.11},
            "series": {},
            "artifacts": [
                {"name": "homo.cube", "path": "/tmp/homo.cube", "mime": "application/x-cube", "size": 10},
                {"name": "lumo.cube", "path": "/tmp/lumo.cube", "mime": "application/x-cube", "size": 10},
            ],
            "returncode": 0,
        }

    q.set_xtb_runner(fake_xtb_runner)

    app = FastAPI()
    app.include_router(jobs_router)

    payload = {
        "engine": "xtb",
        "kind": "opt_properties",
        "inputs": {
            "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
            "charge": 0,
            "multiplicity": 1,
            "params": {"gfn": 2, "cubes": True},
        },
    }

    result = await _run_job_and_get_result(app, payload)
    artifacts = result.get("artifacts", [])
    names = {a.get("name") for a in artifacts}
    assert {"homo.cube", "lumo.cube"} <= names
    scalars = result.get("scalars", {})
    assert scalars.get("E_total_hartree") == -12.34

    q.set_xtb_runner(orig)


@pytest.mark.asyncio
async def test_e2e_cj_with_mock_runner(monkeypatch):
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)

    orig = q._cj_runner

    def fake_cj_runner(payload):
        return {
            "scalars": {"Pcj_Pa": 1.23e9, "Tcj_K": 2500.0, "Dcj_m_per_s": 7500.0},
            "series": {},
            "artifacts": [
                {
                    "name": "cj_results.csv",
                    "path": "/tmp/cj_results.csv",
                    "mime": "text/csv",
                    "size": 20,
                }
            ],
            "returncode": 0,
        }

    q.set_cj_runner(fake_cj_runner)

    app = FastAPI()
    app.include_router(predict_router)
    app.include_router(jobs_router)

    payload = {"reactants": {"H2": 2, "O2": 1}, "T0": 300.0, "P0": 101325.0}

    result = await _run_job_and_get_result(app, payload, endpoint="/predict/cj")
    artifacts = result.get("artifacts", [])
    assert any(a.get("name") == "cj_results.csv" for a in artifacts)
    scalars = result.get("scalars", {})
    assert scalars.get("Pcj_Pa") == 1.23e9
    assert scalars.get("Tcj_K") == 2500.0

    q.set_cj_runner(orig)

