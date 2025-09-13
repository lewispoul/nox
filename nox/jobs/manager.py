"""
Job Manager

Orchestrates job lifecycle management including creation, status tracking,
and result retrieval. Integrates with Dramatiq for background processing
and provides a clean interface for job operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .states import JobState, is_valid_transition
from .storage import JobStorage


class JobManager:
    """Central manager for job lifecycle operations"""

    def __init__(self, storage: Optional[JobStorage] = None):
        """Initialize job manager with optional custom storage"""
        self.storage = storage or JobStorage()
        self._memory_jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, job_request: Dict[str, Any]) -> str:
        """Create a new job and return its ID"""
        job_id = uuid.uuid4().hex

        job_data = {
            "job_id": job_id,
            "state": JobState.PENDING.value,
            "message": "Job queued for processing",
            "progress": 0.0,
            "request": job_request,
            "result": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store in both memory (for immediate access) and persistent storage
        self._memory_jobs[job_id] = job_data.copy()
        self.storage.save_job(job_id, job_data)

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID, checking memory first then storage"""
        # Check memory first for performance
        if job_id in self._memory_jobs:
            return self._memory_jobs[job_id].copy()

        # Fall back to persistent storage
        job_data = self.storage.load_job(job_id)
        if job_data:
            # Cache in memory for future access
            self._memory_jobs[job_id] = job_data.copy()
            return job_data

        return None

    def update_job_state(
        self, job_id: str, new_state: JobState, message: str = "", progress: float = 0.0
    ) -> bool:
        """Update job state with validation"""
        job_data = self.get_job(job_id)
        if not job_data:
            return False

        current_state = JobState(job_data["state"])

        # Validate state transition
        if not is_valid_transition(current_state, new_state):
            return False

        # Update job data
        job_data["state"] = new_state.value
        job_data["message"] = message
        job_data["progress"] = progress
        job_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Update both memory and storage
        self._memory_jobs[job_id] = job_data
        self.storage.save_job(job_id, job_data)

        return True

    def set_job_result(self, job_id: str, result: Dict[str, Any]) -> bool:
        """Set job result and mark as completed"""
        job_data = self.get_job(job_id)
        if not job_data:
            return False

        # Update result
        job_data["result"] = result
        job_data["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Update both memory and storage
        self._memory_jobs[job_id] = job_data
        self.storage.save_job(job_id, job_data)

        return True

    def set_job_failed(self, job_id: str, error_message: str) -> bool:
        """Mark job as failed with error message"""
        return self.update_job_state(
            job_id, JobState.FAILED, error_message, progress=0.0
        )

    def list_jobs(
        self, state_filter: Optional[JobState] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List jobs with optional filtering and limiting"""
        # Get jobs from storage (more complete than memory)
        jobs = self.storage.list_jobs(state_filter)

        # Convert to list and sort by creation time
        job_list = list(jobs.values())
        job_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        if limit:
            job_list = job_list[:limit]

        return job_list

    def cleanup_memory_cache(self, max_size: int = 1000) -> None:
        """Clean up memory cache to prevent unbounded growth"""
        if len(self._memory_jobs) <= max_size:
            return

        # Keep most recently updated jobs
        jobs_by_update = sorted(
            self._memory_jobs.items(),
            key=lambda x: x[1].get("updated_at", ""),
            reverse=True,
        )

        # Keep only the most recent max_size jobs
        self._memory_jobs = dict(jobs_by_update[:max_size])

    def get_job_stats(self) -> Dict[str, int]:
        """Get statistics about job states"""
        all_jobs = self.storage.list_jobs()
        stats = {"total": len(all_jobs)}

        for state in JobState:
            count = sum(
                1 for job in all_jobs.values() if job.get("state") == state.value
            )
            stats[state.value] = count

        return stats
