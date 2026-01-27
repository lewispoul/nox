from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


class Psi4Unavailable(RuntimeError):
    pass


def _ensure_xyz(text: str) -> str:
    t = (text or "").strip()
    if not t:
        raise ValueError("Empty XYZ text")
    return t + ("\n" if not t.endswith("\n") else "")


def _has_psi4() -> bool:
    # Accept either Python module or a cli shim
    if shutil.which("psi4"):
        return True
    try:
        import importlib

        importlib.import_module("psi4")
        return True
    except Exception:
        return False


def run_psi4_job(
    job_dir: Path,
    xyz: str,
    charge: int,
    multiplicity: int,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a minimal Psi4 calculation via the Python API if available.

    This function avoids hard dependencies at import-time. If Psi4 is not
    installed in the environment, it raises Psi4Unavailable. Tests can
    monkeypatch this function to return mocked results without Psi4.
    """

    job_dir.mkdir(parents=True, exist_ok=True)

    if not _has_psi4():
        raise Psi4Unavailable("Psi4 not available in environment (module or binary not found)")

    method: str = params.get("method", "HF")
    basis: str = params.get("basis", "6-31G*")
    do_opt: bool = bool(params.get("opt", True))
    do_freq: bool = bool(params.get("freq", False))
    scf_type: Optional[str] = params.get("scf_type")
    solvent: Optional[str] = params.get("solvent")  # e.g. "water"

    # Defer import until runtime
    import psi4  # type: ignore

    psi4.core.set_output_file(str(job_dir / "psi4.out"), False)
    if scf_type:
        psi4.set_options({"scf_type": scf_type})
    if solvent:
        # Simple PCM setup when requested; users can refine as needed
        psi4.set_options({"pcm": True, "pcm_scf_type": "total"})

    molxyz = _ensure_xyz(xyz)
    mol = psi4.geometry(
        f"""
{molxyz}
units angstrom
charge {charge}
multiplicity {multiplicity}
"""
    )

    energy: Optional[float] = None
    vibfreqs: List[float] = []
    optimized_xyz: Optional[str] = None

    # Choose a small memory footprint by default
    try:
        psi4.set_memory("1 GiB")
    except Exception:
        # If setting memory fails, continue with Psi4's default memory settings.
        pass

    # Build method/basis label
    label = f"{method}/{basis}" if "/" not in method else method

    if do_opt:
        try:
            psi4.optimize(label, molecule=mol)
        except Exception:
            # Continue to attempt energies even if opt fails
            pass

        try:
            optimized_xyz = mol.save_string_xyz()
            (job_dir / "optimized.xyz").write_text(optimized_xyz, encoding="utf-8")
        except Exception:
            optimized_xyz = None

    # Single-point energy
    try:
        energy = float(psi4.energy(label, molecule=mol))
    except Exception:
        energy = None

    if do_freq:
        try:
            # Frequency calculation returns a wavefunction we can inspect
            e, wfn = psi4.frequency(label, molecule=mol, return_wfn=True)
            # Pull frequencies (in cm^-1)
            try:
                arr = wfn.frequency_analysis["omega"].data.to_array()
                vibfreqs = [float(x) for x in arr.flatten().tolist()]
            except Exception:
                vibfreqs = []
        except Exception:
            vibfreqs = []

    scalars: Dict[str, Any] = {}
    if energy is not None:
        scalars["E_total_hartree"] = energy

    artifacts = []
    out_path = job_dir / "psi4.out"
    if out_path.exists():
        artifacts.append(
            {
                "name": out_path.name,
                "path": str(out_path),
                "mime": "text/plain",
                "size": out_path.stat().st_size,
            }
        )
    if optimized_xyz:
        artifacts.append(
            {
                "name": "optimized.xyz",
                "path": str(job_dir / "optimized.xyz"),
                "mime": "chemical/x-xyz",
                "size": (job_dir / "optimized.xyz").stat().st_size,
            }
        )

    return {
        "scalars": scalars,
        "series": {"vibfreq_cm^-1": vibfreqs} if vibfreqs else {},
        "artifacts": artifacts,
        "returncode": 0 if energy is not None else 1,
    }
