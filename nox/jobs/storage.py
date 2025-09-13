"""
Job Storage Management

Provides persistent storage for job data, results, and metadata.
Handles job state persistence and cleanup operations.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .states import JobState


class JobStorage:
    """Manages persistent storage for job data and results"""

    def __init__(self, base_path: str = "./data/jobs"):
        """Initialize job storage with base directory"""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_job_path(self, job_id: str) -> Path:
        """Get the storage path for a specific job"""
        return self.base_path / f"{job_id}.json"

    def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Save job data to persistent storage"""
        job_path = self._get_job_path(job_id)

        # Add timestamp metadata
        job_data["_metadata"] = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "storage_version": "1.0",
        }

        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job_data, f, indent=2)

    def load_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load job data from persistent storage"""
        job_path = self._get_job_path(job_id)

        if not job_path.exists():
            return None

        try:
            with open(job_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def update_job_state(
        self, job_id: str, new_state: JobState, message: str = "", progress: float = 0.0
    ) -> bool:
        """Update job state and related metadata"""
        job_data = self.load_job(job_id)
        if job_data is None:
            return False

        job_data["state"] = new_state.value
        job_data["message"] = message
        job_data["progress"] = progress
        job_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        self.save_job(job_id, job_data)
        return True

    def set_job_result(self, job_id: str, result: Dict[str, Any]) -> bool:
        """Set the result data for a completed job"""
        job_data = self.load_job(job_id)
        if job_data is None:
            return False

        job_data["result"] = result
        job_data["completed_at"] = datetime.now(timezone.utc).isoformat()

        self.save_job(job_id, job_data)
        return True

    def list_jobs(self, state_filter: Optional[JobState] = None) -> Dict[str, Dict]:
        """List all jobs, optionally filtered by state"""
        jobs = {}

        for job_file in self.base_path.glob("*.json"):
            job_id = job_file.stem
            job_data = self.load_job(job_id)

            if job_data is None:
                continue

            job_state = job_data.get("state")
            if state_filter is None or job_state == state_filter.value:
                jobs[job_id] = job_data

        return jobs

    def cleanup_old_jobs(self, max_age_days: int = 30) -> int:
        """Remove jobs older than specified age"""
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - (max_age_days * 86400)
        cleaned = 0

        for job_file in self.base_path.glob("*.json"):
            if job_file.stat().st_mtime < cutoff:
                job_file.unlink()
                cleaned += 1

        return cleaned

    def delete_job(self, job_id: str) -> bool:
        """Delete a specific job from storage"""
        job_path = self._get_job_path(job_id)
        if job_path.exists():
            job_path.unlink()
            return True
        return False
