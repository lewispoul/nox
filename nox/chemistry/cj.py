from __future__ import annotations

import csv
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
        # Hermetic fallback: deterministic Pcj/Tcj values with CSV artifact
        pcj = 2.0e9
        tcj = 3000.0
        dcj = 8000.0
        csv_path = job_dir / "cj_results.csv"
        job_dir.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Pcj_Pa", "Tcj_K", "Dcj_m_per_s"])
            writer.writerow([pcj, tcj, dcj])

        return {
            "scalars": {"Pcj_Pa": pcj, "Tcj_K": tcj, "Dcj_m_per_s": dcj},
            "series": {},
            "artifacts": [
                {
                    "name": csv_path.name,
                    "path": str(csv_path),
                    "mime": "text/csv",
                    "size": csv_path.stat().st_size,
                }
            ],
            "returncode": 0,
            "available": False,
            "hermetic": True,
            "message": "Cantera not available; returning hermetic CJ result",
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
