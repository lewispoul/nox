from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass
class Job:
    id: str
    state: str = "queued"  # queued|running|done|failed
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("created_at", None)
        d.pop("updated_at", None)
        return d


class InMemoryJobsStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.RLock()

    def create(self) -> Job:
        with self._lock:
            now = time.time()
            j = Job(id=uuid.uuid4().hex, created_at=now, updated_at=now)
            self._jobs[j.id] = j
            return j

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def set_state(
        self,
        job_id: str,
        state: str,
        *,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            j = self._jobs[job_id]
            j.state = state
            j.result = result
            j.error = error
            j.updated_at = time.time()


class RedisJobsStore:
    def __init__(self, redis_client) -> None:
        self.r = redis_client
        self.prefix = os.getenv("JOBS_PREFIX", "jobs:")

    def _key(self, job_id: str) -> str:
        return f"{self.prefix}{job_id}"

    def create(self) -> Job:
        job_id = uuid.uuid4().hex
        now = time.time()
        payload = {
            "id": job_id,
            "state": "queued",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        self.r.hset(
            self._key(job_id), mapping={k: json.dumps(v) for k, v in payload.items()}
        )
        return Job(**payload)

    def get(self, job_id: str) -> Optional[Job]:
        data = self.r.hgetall(self._key(job_id))
        if not data:
            return None
        decoded = {k.decode(): json.loads(v) for k, v in data.items()}
        return Job(**decoded)

    def set_state(
        self,
        job_id: str,
        state: str,
        *,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        key = self._key(job_id)
        now = time.time()
        if result is None:
            result_json = None
        else:
            result_json = result
        self.r.hset(
            key,
            mapping={
                "state": json.dumps(state),
                "result": json.dumps(result_json),
                "error": json.dumps(error),
                "updated_at": json.dumps(now),
            },
        )


# factory
_store_singleton = None


def get_store():
    global _store_singleton
    if _store_singleton is not None:
        return _store_singleton
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        import redis

        client = redis.from_url(REDIS_URL)
        _store_singleton = RedisJobsStore(client)
    else:
        _store_singleton = InMemoryJobsStore()
    return _store_singleton
