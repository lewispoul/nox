import shutil
from unittest import mock

import pytest

from api.services import queue
from api.services.jobs_store import get_store
from api.schemas.job import JobInputs, JobRequest, XTBParams
from tests.helpers import wait_for_job_done


@pytest.mark.skipif(shutil.which("xtb") is not None, reason="Test hermetic fallback only when xtb unavailable")
@pytest.mark.asyncio
async def test_xtb_job_hermetic_cubes(monkeypatch):
    # Force local execution and hermetic XTB path
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)

    params = XTBParams(gfn=2, opt=True, cubes=True)
    jr = JobRequest(
        engine="xtb",
        kind="opt_properties",
        inputs=JobInputs(
            xyz="2\nH2 molecule\nH 0 0 0\nH 0 0 0.74\n",
            charge=0,
            multiplicity=1,
            params=params,
        ),
    )

    job_id = queue.submit_job("xtb", {"job_request": jr.model_dump_json()})

    await wait_for_job_done(job_id)

    store = get_store()
    job = store.get(job_id)
    assert job.state == "done"
    result = job.result or {}
    artifacts = result.get("artifacts", [])
    names = {a.get("name") for a in artifacts}
    assert {"homo.cube", "lumo.cube"} <= names
    scalars = result.get("scalars", {})
    assert scalars.get("E_total_hartree") is not None
    assert scalars.get("gap_eV") is not None


@pytest.mark.asyncio
async def test_xtb_job_with_mock_runner(monkeypatch):
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)

    orig = queue._xtb_runner

    def fake_xtb_runner(payload):
        return {
            "scalars": {"E_total_hartree": -10.0, "gap_eV": 2.5},
            "series": {},
            "artifacts": [
                {"name": "homo.cube", "path": "/tmp/homo.cube", "mime": "application/x-cube", "size": 10},
                {"name": "lumo.cube", "path": "/tmp/lumo.cube", "mime": "application/x-cube", "size": 10},
            ],
            "returncode": 0,
        }

    queue.set_xtb_runner(fake_xtb_runner)

    params = XTBParams(gfn=2, opt=True, cubes=True)
    jr = JobRequest(
        engine="xtb",
        kind="opt_properties",
        inputs=JobInputs(
            xyz="2\nH2 molecule\nH 0 0 0\nH 0 0 0.74\n",
            charge=0,
            multiplicity=1,
            params=params,
        ),
    )

    job_id = queue.submit_job("xtb", {"job_request": jr.model_dump_json()})

    await wait_for_job_done(job_id)

    store = get_store()
    job = store.get(job_id)
    assert job.state == "done"
    result = job.result or {}
    artifacts = result.get("artifacts", [])
    names = {a.get("name") for a in artifacts}
    assert {"homo.cube", "lumo.cube"} <= names
    scalars = result.get("scalars", {})
    assert scalars.get("E_total_hartree") == -10.0

    # Restore runner
    queue.set_xtb_runner(orig)
