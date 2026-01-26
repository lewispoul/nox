from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict

from .jobs_store import get_store

logger = logging.getLogger(__name__)


def _normalize_remote_result(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a remote IAM response into Nox result shape.

    Expected shape: {scalars, series, artifacts, returncode}. If missing,
    infer from common fields like 'energy' and add defaults.
    """
    if not isinstance(resp, dict):
        return {"scalars": {}, "series": {}, "artifacts": [], "returncode": 1}

    result = dict(resp)
    scalars = result.get("scalars") or {}
    series = result.get("series") or {}
    artifacts = result.get("artifacts") or []
    rc = result.get("returncode")

    # Validate artifacts is a list and contains only safe paths
    if not isinstance(artifacts, list):
        logger.warning(
            "Invalid artifacts type in remote result, expected list",
            extra={"type": type(artifacts).__name__},
        )
        artifacts = []
    else:
        # Filter out potentially malicious paths (absolute paths, path traversal)
        safe_artifacts = []
        for art in artifacts:
            if isinstance(art, str):
                # Reject absolute paths and path traversal attempts
                # Use normpath to resolve encoded and complex traversal attempts
                try:
                    normalized = os.path.normpath(art)
                    # Reject if:
                    # - Absolute path after normalization
                    # - Starts with .. (parent directory traversal)
                    is_safe = (
                        not os.path.isabs(normalized)
                        and not normalized.startswith("..")
                    )
                    
                    # Additional check: if normalization changed the path, verify no
                    # parent directory components were introduced by obfuscation
                    # (e.g., "foo/../../etc" -> "../etc" or "....//etc" -> "../etc")
                    if is_safe and normalized != art:
                        # Reject if any path component is ".." after normalization
                        if ".." in normalized.split(os.sep):
                            is_safe = False
                    
                    if is_safe:
                        safe_artifacts.append(art)
                    else:
                        logger.warning(
                            "Rejected unsafe artifact path",
                            extra={"path": art, "normalized": normalized},
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to validate artifact path",
                        extra={"path": art, "error": str(e)},
                    )
        artifacts = safe_artifacts

    # Validate scalars and series are dicts
    if not isinstance(scalars, dict):
        logger.warning(
            "Invalid scalars type in remote result, expected dict",
            extra={"type": type(scalars).__name__},
        )
        scalars = {}

    if not isinstance(series, dict):
        logger.warning(
            "Invalid series type in remote result, expected dict",
            extra={"type": type(series).__name__},
        )
        series = {}

    # Infer energy if provided under other keys
    if not scalars:
        energy = None
        for k in ("energy", "E_total_hartree", "etot", "total_energy"):
            if k in result:
                try:
                    energy = float(result[k])
                except (TypeError, ValueError):
                    # Ignore values that cannot be converted to float and try next key
                    continue
                break
        if energy is not None:
            scalars = {"E_total_hartree": energy}

    if rc is None:
        rc = 0 if scalars else 1

    return {
        "scalars": scalars,
        "series": series,
        "artifacts": artifacts,
        "returncode": rc,
    }


# Simple demo work; replace with real task kinds
def echo_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    time.sleep(0.05)
    # Return both an echo and keep the original payload under 'payload'
    return {"echo": payload, "payload": payload}


def submit_job(kind: str, payload: Dict[str, Any]) -> str:
    store = get_store()
    job = store.create()
    job_id = job.id

    # Ensure payload carries the job_id for worker/local runner
    try:
        payload["job_id"] = job_id
    except Exception:
        # If payload is not a mutable dict for any reason, ignore
        pass

    def _run_local():
        try:
            store.set_state(job_id, "running")
            # Brief delay after state transition to handle race condition where
            # API clients may immediately query job artifacts. The artifacts
            # endpoint should return 404 for jobs not in a terminal state
            # (completed/failed), but some clients poll aggressively right after
            # submission. This delay ensures the "running" state is visible before
            # the job completes, giving clients time to see the intermediate state.
            # TODO: Consider removing this delay and instead ensuring the artifacts
            # endpoint properly checks job state and returns 404/409 for non-terminal
            # states, or use proper synchronization primitives (locks/events).
            time.sleep(0.05)
            if kind == "echo":
                result = echo_worker(payload)
            elif kind == "xtb":
                # For local mode, run XTB calculation directly
                result = _xtb_runner(payload)
            elif kind == "psi4":
                result = _psi4_runner(payload)
            elif kind == "cj":
                result = _cj_runner(payload)
            else:
                result = {"echo": payload}
            # If runner returned a returncode, treat non-success as failure
            if isinstance(result, dict) and "returncode" in result:
                rc = result.get("returncode")
                has_energy = (
                    result.get("scalars", {}).get("E_total_hartree") is not None
                )
                success = (rc == 0) or (rc == 2 and has_energy)
                if not success:
                    store.set_state(
                        job_id,
                        "failed",
                        error=f"returncode={rc}",
                        result=result,
                    )
                else:
                    store.set_state(job_id, "done", result=result)
            else:
                store.set_state(job_id, "done", result=result)
        except Exception as e:  # noqa: BLE001
            store.set_state(job_id, "failed", error=str(e))

    # Check Redis URL dynamically to support test monkeypatching
    redis_url = os.getenv("REDIS_URL")

    # Allow explicit env override for local mode (used by tests)
    jfl_env = os.getenv("JOBS_FORCE_LOCAL")
    if jfl_env is not None and jfl_env.lower() in ("1", "true", "yes"):
        redis_url = None
    else:
        # Prefer local mode when settings request it (explicit config)
        try:
            from api.services.settings import settings

            if getattr(settings, "jobs_force_local", False):
                redis_url = None
        except Exception:
            # If settings import fails or has no attribute, ignore
            pass

    if redis_url:
        # Publish to Dramatiq actor; worker will update Redis-backed store
        # We import inside to avoid dramatiq dep at import time in CI
        from workers.jobs_worker import enqueue_job

        # Dispatch send in background to avoid synchronous execution when
        # using a stub broker which may run actors immediately. This keeps
        # POST semantics predictable (queued) for tests that inspect state
        # immediately after submission.
        def _send_or_fallback():
            try:
                enqueue_job.send(job_id, kind, payload)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "enqueue_job.send failed; falling back to local execution",
                    extra={"job_id": job_id, "kind": kind},
                )
                _run_local()

        threading.Thread(target=_send_or_fallback, daemon=True).start()
        return job_id

    # Local thread mode for CI or dev without Redis
    threading.Thread(target=_run_local, daemon=True).start()
    return job_id


def _default_xtb_runner(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Default runner that executes XTB calculations locally.

    Kept as an injectable callable so tests can replace it with a stub.
    """
    from ai.runners.xtb import run_xtb_job
    from api.schemas.job import JobRequest
    from api.services.storage import job_dir
    from api.services.settings import settings

    # Parse the job request
    job_request_data = payload.get("job_request", {})
    try:
        if isinstance(job_request_data, str):
            # Support legacy JSON string format for backwards compatibility
            JR = JobRequest.model_validate_json(job_request_data)
        else:
            # Prefer dict format to avoid unnecessary serialization
            JR = JobRequest.model_validate(job_request_data)
    except Exception as e:
        raise ValueError(f"Invalid job request: {e}")

    job_id = payload.get("job_id", "unknown")
    jd = job_dir(job_id)

    if settings.iam_use_remote:
        if not settings.iam_base_url:
            raise ValueError(
                "iam_use_remote is enabled but iam_base_url is not configured"
            )
        from ai.iam_client import IAMClient

        try:
            client = IAMClient(base_url=settings.iam_base_url)
            result = _normalize_remote_result(client.run_xtb(JR.model_dump()))
        except Exception as e:
            # Normalize IAM errors into a failure result so caller logic remains consistent
            result = {
                "scalars": {},
                "series": {},
                "artifacts": [],
                "returncode": 1,
                "error": f"IAM XTB invocation failed: {e}",
            }
        # Assume IAM returns compatible structure; otherwise adapt here
    else:
        result = run_xtb_job(
            jd,
            JR.inputs.xyz,
            JR.inputs.charge,
            JR.inputs.multiplicity,
            JR.inputs.params.model_dump(),
        )

    # Include the original payload in the result
    result["payload"] = payload

    # XTB success: return code 0 OR (return code 2 with valid energy results)
    has_energy = result.get("scalars", {}).get("E_total_hartree") is not None
    success = (result.get("returncode") == 0) or (
        result.get("returncode") == 2 and has_energy
    )

    if not success:
        error_msg = (
            "XTB calculation failed with return code " f"{result.get('returncode')}"
        )
        raise RuntimeError(error_msg)

    return result


# Exported runner and setter to allow tests to inject a stub
_xtb_runner = _default_xtb_runner


def set_xtb_runner(runner_callable):
    """Replace the XTB runner callable (used in tests).

    The callable must accept a payload dict and return a result dict.
    """
    global _xtb_runner
    _xtb_runner = runner_callable


def _default_psi4_runner(payload: Dict[str, Any]) -> Dict[str, Any]:
    from api.schemas.psi4_job import Psi4JobRequest
    from api.services.storage import job_dir
    from ai.runners.psi4 import run_psi4_job
    from api.services.settings import settings

    job_request_data = payload.get("job_request", {})
    try:
        if isinstance(job_request_data, str):
            # Support legacy JSON string format for backwards compatibility
            JR = Psi4JobRequest.model_validate_json(job_request_data)
        else:
            # Prefer dict format to avoid unnecessary serialization
            JR = Psi4JobRequest.model_validate(job_request_data)
    except Exception as exc:
        raise ValueError(f"Invalid Psi4 job_request payload: {exc}") from exc

    job_id = payload.get("job_id", "unknown")
    jd = job_dir(job_id)

    if settings.iam_use_remote:
        if not settings.iam_base_url:
            raise ValueError(
                "iam_use_remote is enabled but iam_base_url is not configured"
            )
        from ai.iam_client import IAMClient

        try:
            client = IAMClient(base_url=settings.iam_base_url)
            result = _normalize_remote_result(client.run_psi4(JR.model_dump()))
        except Exception as e:
            # Normalize IAM errors into a failure result so caller logic remains consistent
            result = {
                "scalars": {},
                "series": {},
                "artifacts": [],
                "returncode": 1,
                "error": f"IAM Psi4 invocation failed: {e}",
            }
    else:
        result = run_psi4_job(
            jd,
            JR.inputs.xyz,
            JR.inputs.charge,
            JR.inputs.multiplicity,
            JR.inputs.params.model_dump(),
        )

    result["payload"] = payload

    rc = result.get("returncode")
    if rc != 0:
        raise RuntimeError(f"Psi4 calculation failed, returncode={rc}")
    return result


_psi4_runner = _default_psi4_runner


def set_psi4_runner(runner_callable):
    global _psi4_runner
    _psi4_runner = runner_callable


def _default_cj_runner(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Light wrapper around optional Cantera-based CJ module
    from api.services.storage import job_dir
    from nox.chemistry.cj import run_cj  # lazy import; file will handle availability

    jd = job_dir(payload.get("job_id", "unknown"))
    req = payload.get("cj_request", {})
    res = run_cj(jd, req)
    res["payload"] = payload

    rc = res.get("returncode")
    if rc != 0:
        raise RuntimeError(f"CJ calculation failed, returncode={rc}")
    return res


_cj_runner = _default_cj_runner


def set_cj_runner(runner_callable):
    global _cj_runner
    _cj_runner = runner_callable
