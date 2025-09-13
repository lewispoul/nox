import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from api.services.settings import settings
from nox.artifacts.cubes import generate_cubes_from_molden, validate_cube_file


def _write_xyz(xyz_text: str, path: Path) -> None:
    path.write_text(xyz_text.strip() + "\n", encoding="utf-8")


def _run_cmd(cmd: str, cwd: Path, log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            shlex.split(cmd),
            cwd=str(cwd),
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
        )
        ret = proc.wait()
    return ret


def _parse_xtbout_json(json_path: Path) -> Dict[str, float]:
    scalars: Dict[str, float] = {}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return scalars

    # énergie totale, plusieurs variantes possibles
    # essayer chemins connus, sinon rien
    candidates_E = [
        ("energy", "total"),
        ("results", "total_energy"),
        ("scf", "etot"),
        ("etot",),
    ]
    for path in candidates_E:
        node = data
        try:
            for k in path:
                node = node[k]
            if isinstance(node, (int, float, str)):
                scalars["E_total_hartree"] = float(node)
                break
        except Exception:
            continue

    # gap eV
    candidates_gap = [
        ("gap",),
        ("results", "gap"),
        ("orbitals", "gap"),
    ]
    for path in candidates_gap:
        node = data
        try:
            for k in path:
                node = node[k]
            if isinstance(node, (int, float, str)):
                scalars["gap_eV"] = float(node)
                break
        except Exception:
            continue

    # dipôle total en Debye
    candidates_dip = [
        ("dipole", "total"),
        ("properties", "dipole", "total"),
    ]
    for path in candidates_dip:
        node = data
        try:
            for k in path:
                node = node[k]
            if isinstance(node, (int, float, str)):
                scalars["dipole_D"] = float(node)
                break
        except Exception:
            continue

    return scalars


def _parse_from_text(text: str) -> Dict[str, float]:
    scalars: Dict[str, float] = {}
    # Energie totale, lignes type: "TOTAL ENERGY  -40.123456 Hartree"
    m = re.search(r"TOTAL\s+ENERGY\s+(-?\d+\.\d+)", text, re.IGNORECASE)
    if m:
        try:
            scalars["E_total_hartree"] = float(m.group(1))
        except Exception:
            pass
    # GAP, lignes type: "HOMO-LUMO GAP  5.43 eV"
    m = re.search(r"HOMO[-\s]?LUMO\s+GAP\s+(\d+\.\d+)", text, re.IGNORECASE)
    if m:
        try:
            scalars["gap_eV"] = float(m.group(1))
        except Exception:
            pass
    # Dipôle total, lignes type: "dipole moment  total:   1.234 Debye"
    m = re.search(r"dipole\s+moment.*total[:\s]+(\d+\.\d+)", text, re.IGNORECASE)
    if m:
        try:
            scalars["dipole_D"] = float(m.group(1))
        except Exception:
            pass
    return scalars


def _maybe_generate_molden(work: Path, inp_name: str) -> Path:
    """Essaye de produire un fichier Molden pour les MOs, utile pour générer des cubes plus tard.
    Plusieurs binaires xtb supportent l'option --molden, selon version. On essaie sans casser le job.
    """
    molden = work / "orbitals.molden"
    cmd = f"{settings.xtb_bin} {inp_name} --molden"
    try:
        ret = _run_cmd(cmd, work, work / "molden.log")
        if ret == 0 and molden.exists() and molden.stat().st_size > 0:
            return molden
    except Exception:
        pass
    return Path()


def run_xtb_job(
    job_dir: Path, xyz: str, charge: int, multiplicity: int, params: Dict[str, Any]
) -> Dict[str, Any]:
    job_dir.mkdir(parents=True, exist_ok=True)
    inp = job_dir / "input.xyz"
    _write_xyz(xyz, inp)

    log = job_dir / "xtb.log"
    out = job_dir / "xtb.out"  # certaines versions écrivent aussi xtb.out
    json_out = job_dir / "xtbout.json"

    # commande XTB
    gfn = int(params.get("gfn", 2))
    cmd = f"{settings.xtb_bin} {inp.name} --gfn {gfn} --json"
    if params.get("opt", True):
        cmd += " --opt"
    if params.get("hess", False):
        cmd += " --hess"
    if params.get("uhf", False):
        cmd += " --uhf"
    # charge, si différent de valeur par défaut
    chrg = int(params.get("chrg", charge))
    if chrg != 0:
        cmd += f" --chrg {chrg}"

    # exécuter
    ret = _run_cmd(cmd, job_dir, log)

    scalars: Dict[str, float] = {}
    artifacts: List[Dict[str, Any]] = []

    # parse prioritaire du JSON
    if json_out.exists():
        scalars.update(_parse_xtbout_json(json_out))
        artifacts.append(
            {
                "name": "xtbout.json",
                "path": str(json_out),
                "mime": "application/json",
                "size": json_out.stat().st_size,
            }
        )

    # fallback parsing texte
    text = ""
    if out.exists() and out.is_file():
        try:
            text = out.read_text(encoding="utf-8", errors="ignore")
            artifacts.append(
                {
                    "name": "xtb.out",
                    "path": str(out),
                    "mime": "text/plain",
                    "size": out.stat().st_size,
                }
            )
        except Exception:
            text = ""
    if not text and log.exists():
        try:
            text = log.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
    if text:
        parsed = _parse_from_text(text)
        for k, v in parsed.items():
            scalars.setdefault(k, v)

    # logs en artefacts (seulement si pas déjà ajouté et si existe)
    if log.exists() and not any(a["name"] == "xtb.log" for a in artifacts):
        artifacts.append(
            {
                "name": "xtb.log",
                "path": str(log),
                "mime": "text/plain",
                "size": log.stat().st_size,
            }
        )

    # génération Molden si demandé
    if params.get("cubes", False):
        molden_path = _maybe_generate_molden(job_dir, inp.name)
        if molden_path and molden_path.exists() and molden_path.is_file():
            artifacts.append(
                {
                    "name": molden_path.name,
                    "path": str(molden_path),
                    "mime": "text/plain",
                    "size": molden_path.stat().st_size,
                }
            )

            # Generate HOMO/LUMO cube files using our cube module
            try:
                cube_files = generate_cubes_from_molden(
                    molden_path, job_dir, ["homo", "lumo"]
                )

                for cube_file in cube_files:
                    if cube_file.exists():
                        cube_info = validate_cube_file(cube_file)
                        artifacts.append(
                            {
                                "name": cube_file.name,
                                "path": str(cube_file),
                                "mime": "application/x-cube",
                                "size": cube_file.stat().st_size,
                                "metadata": cube_info,
                            }
                        )

            except Exception as e:
                print(f"Cube generation failed: {e}")
        else:
            # XTB peut générer molden.input automatiquement
            molden_input = job_dir / "molden.input"
            if molden_input.exists():
                artifacts.append(
                    {
                        "name": "molden.input",
                        "path": str(molden_input),
                        "mime": "text/plain",
                        "size": molden_input.stat().st_size,
                    }
                )

    return {"scalars": scalars, "series": {}, "artifacts": artifacts, "returncode": ret}
