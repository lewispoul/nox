"""
Redis-based Job Storage for JOBS-002

This implements shared job storage using Redis to ensure job state
is consistent between the API server and Dramatiq workers.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

from api.services.settings import settings


class RedisJobStorage:
    """Redis-based job storage for cross-process job state management"""

    def __init__(self, redis_url: str = None):
        """Initialize Redis connection"""
        self.redis_url = redis_url or getattr(
            settings, "redis_url", "redis://localhost:6379/0"
        )
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    def _job_key(self, job_id: str) -> str:
        """Get Redis key for job"""
        return f"job:{job_id}"

    def create_job(self, job_request: Dict[str, Any]) -> str:
        """Create new job and store in Redis"""
        job_id = uuid.uuid4().hex

        job_data = {
            "job_id": job_id,
            "state": "pending",
            "message": "Job queued for processing",
            "progress": 0.0,
            "request": job_request,
            "result": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store in Redis with 24 hour expiration
        key = self._job_key(job_id)
        self.redis_client.setex(key, 86400, json.dumps(job_data))

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data from Redis"""
        key = self._job_key(job_id)
        job_data_json = self.redis_client.get(key)

        if job_data_json is None:
            return None

        try:
            return json.loads(job_data_json)
        except json.JSONDecodeError:
            return None

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update job data in Redis"""
        job_data = self.get_job(job_id)
        if job_data is None:
            return False

        # Apply updates
        job_data.update(updates)
        job_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save back to Redis
        key = self._job_key(job_id)
        self.redis_client.setex(key, 86400, json.dumps(job_data))
        return True

    def set_job_state(
        self, job_id: str, state: str, message: str = "", progress: float = 0.0
    ) -> bool:
        """Update job state"""
        return self.update_job(
            job_id, {"state": state, "message": message, "progress": progress}
        )

    def set_job_result(self, job_id: str, result: Dict[str, Any]) -> bool:
        """Set job result and mark as completed"""
        return self.update_job(
            job_id,
            {
                "result": result,
                "state": "completed",
                "message": "Job completed successfully",
                "progress": 1.0,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def set_job_failed(self, job_id: str, error_message: str) -> bool:
        """Mark job as failed"""
        return self.update_job(
            job_id,
            {
                "state": "failed",
                "message": error_message,
                "progress": 0.0,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def list_jobs(self, pattern: str = "job:*") -> Dict[str, Dict[str, Any]]:
        """List all jobs matching pattern"""
        keys = self.redis_client.keys(pattern)
        jobs = {}

        for key in keys:
            job_id = key.replace("job:", "")
            job_data = self.get_job(job_id)
            if job_data:
                jobs[job_id] = job_data

        return jobs

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed jobs"""
        jobs = self.list_jobs()
        cleaned = 0
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

        for job_id, job_data in jobs.items():
            if job_data.get("state") in ["completed", "failed"]:
                completed_at = job_data.get("completed_at") or job_data.get("failed_at")
                if completed_at:
                    try:
                        job_time = datetime.fromisoformat(
                            completed_at.replace("Z", "+00:00")
                        ).timestamp()
                        if job_time < cutoff:
                            key = self._job_key(job_id)
                            self.redis_client.delete(key)
                            cleaned += 1
                    except (ValueError, AttributeError):
                        continue

        return cleaned


# Global instance
redis_job_storage = RedisJobStorage()
