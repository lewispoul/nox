import time

import pytest

from api.services.jobs_store import get_store
from api.services.queue import submit_job


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


@pytest.mark.parametrize(
    "kind,payload",
    [("echo", {"a": 1}), ("echo", {"x": 42})],
)
def test_submit_job_injects_job_id_and_finishes(monkeypatch, kind, payload):
    # Force local thread mode
    monkeypatch.setenv("JOBS_FORCE_LOCAL", "1")

    job_id = submit_job(kind, payload)
    assert job_id

    j = poll_state(job_id, timeout=3.0)
    assert j is not None, "job disappeared from store"
    assert j.state in ("done", "failed")

    # For echo jobs, result should include payload (we return payload
    # under 'payload')
    if kind == "echo":
        assert j.result is not None
        assert j.result.get("payload") is not None
        # job_id should have been injected into payload
        assert j.result.get("payload").get("job_id") == job_id
