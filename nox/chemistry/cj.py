from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict


def _has_cantera() -> bool:
    try:
        import importlib

        importlib.import_module("cantera")
        return True
    except Exception:
        return False


def run_cj(job_dir: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    """Run a Chapman–Jouguet detonation calculation (scaffold).

    The real implementation requires Cantera and thermochemical datasets. This
    scaffold returns a structured response and, when Cantera is available,
    leaves a hook to implement a proper CJ solve. Tests may monkeypatch this
    function to provide deterministic outputs.
    """
    job_dir.mkdir(parents=True, exist_ok=True)

    if not _has_cantera():
        return {
            "scalars": {},
            "series": {},
            "artifacts": [],
            "returncode": 2,
            "available": False,
            "message": "Cantera not available; CJ module scaffold only",
        }

    # Placeholder structure for future implementation
    # Extract minimal inputs for logging
    reactants = request.get("reactants", {})
    T0 = float(request.get("T0", 298.15))
    P0 = float(request.get("P0", 101325.0))

    # Record input for traceability
    (job_dir / "cj_request.json").write_text(
        json.dumps({"reactants": reactants, "T0": T0, "P0": P0}, indent=2),
        encoding="utf-8",
    )

    # TODO: Implement CJ via Cantera (Gibbs minimization at sonic condition)
    # For now, signal unimplemented but available
    return {
        "scalars": {},
        "series": {},
        "artifacts": [
            {
                "name": "cj_request.json",
                "path": str(job_dir / "cj_request.json"),
                "mime": "application/json",
                "size": (job_dir / "cj_request.json").stat().st_size,
            }
        ],
        "returncode": 1,
        "available": True,
        "message": "CJ calculation not yet implemented",
    }
