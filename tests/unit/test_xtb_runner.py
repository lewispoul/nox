import time

from api.services.jobs_store import get_store
from api.services.queue import set_xtb_runner, submit_job


def fake_runner_success(payload):
    return {
        "scalars": {"E_total_hartree": -1.0},
        "series": {},
        "artifacts": [],
        "returncode": 0,
        "payload": payload,
    }


def fake_runner_fail(payload):
    return {
        "scalars": {},
        "series": {},
        "artifacts": [],
        "returncode": 1,
        "payload": payload,
    }


def poll_state(job_id: str, timeout: float = 2.0):
    deadline = time.time() + timeout
    store = get_store()
    while time.time() < deadline:
        j = store.get(job_id)
        if j is None:
            return None
        if j.state in ("done", "failed"):
            return j
        time.sleep(0.01)
    return store.get(job_id)


def test_xtb_runner_injection_success(monkeypatch):
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    set_xtb_runner(fake_runner_success)
    job_req = {
        "engine": "xtb",
        "kind": "opt_properties",
        "inputs": {
            "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
            "charge": 0,
            "multiplicity": 1,
            "params": {},
        },
    }
    job_id = submit_job("xtb", job_req)
    j = poll_state(job_id, timeout=3.0)
    assert j is not None
    assert j.state == "done"
    assert j.result is not None
    assert isinstance(j.result.get("scalars"), dict)
    assert j.result.get("scalars").get("E_total_hartree") == -1.0


def test_xtb_runner_injection_failure(monkeypatch):
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")
    set_xtb_runner(fake_runner_fail)
    job_req = {
        "engine": "xtb",
        "kind": "opt_properties",
        "inputs": {
            "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
            "charge": 0,
            "multiplicity": 1,
            "params": {},
        },
    }
    job_id = submit_job("xtb", job_req)
    j = poll_state(job_id, timeout=3.0)
    assert j is not None
    # fake_runner_fail returns returncode=1 so submit_job should mark failed
    assert j.state == "failed"
