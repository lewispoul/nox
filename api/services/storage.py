from pathlib import Path

from .settings import settings


def job_dir(job_id: str) -> Path:
    d = settings.artifacts_root / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d
