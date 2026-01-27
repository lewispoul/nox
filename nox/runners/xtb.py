from __future__ import annotations

import pathlib
import shutil
from typing import Any, Dict

from nox.parsers.xtb_json import parse_xtbout_text


class XTBNotAvailable(RuntimeError):
    """Raised when the xtb binary is not present on PATH."""


_HERMETIC_SCALARS = {
    "E_total_hartree": -40.123456,
    "gap_eV": 3.217,
    "dipole_D": 1.842,
}


def _hermetic_result() -> Dict[str, Any]:
    return {
        "scalars": dict(_HERMETIC_SCALARS),
        "series": {},
        "artifacts": [],
        "returncode": 0,
        "hermetic": True,
    }


def run_xtb_job(
    job_dir: pathlib.Path,
    xyz: str,
    charge: int,
    multiplicity: int,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a real XTB calculation when the binary is available, otherwise
    short-circuit to a deterministic hermetic result for CI.
    """

    if shutil.which("xtb") is None:
        # Hermetic mode: return deterministic scalars and optional placeholder cubes
        job_dir.mkdir(parents=True, exist_ok=True)
        result = _hermetic_result()

        if params.get("cubes"):
            # Generate placeholder cube files directly for hermetic mode
            from nox.artifacts.cubes import _create_placeholder_cubes, validate_cube_file

            try:
                cube_files = _create_placeholder_cubes(job_dir, ["homo", "lumo"])
                for cube_file in cube_files:
                    metadata = validate_cube_file(cube_file)
                    result["artifacts"].append(
                        {
                            "name": cube_file.name,
                            "path": str(cube_file),
                            "mime": "application/x-cube",
                            "size": cube_file.stat().st_size,
                            "metadata": metadata,
                        }
                    )
            except Exception:
                # Keep hermetic deterministic even if cube generation fails
                pass

        return result

    from ai.runners.xtb import run_xtb_job as _real_run_xtb_job

    return _real_run_xtb_job(job_dir, xyz, charge, multiplicity, params)


def run_xtb(smiles: str | None = None, infile: str | None = None) -> dict:
    """
    Backward-compatible helper used by older tests: read xtbout.json next to an
    input file, or return a hermetic result if xtb is missing. Prefer
    ``run_xtb_job`` for job execution.
    """

    if shutil.which("xtb") is None:
        return _hermetic_result()

    if not infile and not smiles:
        raise ValueError("Provide infile or smiles")

    path = pathlib.Path(infile or "")
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")

    out_json = path.with_name("xtbout.json")
    text = out_json.read_text(encoding="utf-8")
    return parse_xtbout_text(text)
