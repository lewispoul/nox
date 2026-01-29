import json
import pathlib
import shutil

import pytest

from nox.runners.xtb import run_xtb, run_xtb_job

DATA = pathlib.Path(__file__).parent / "data"


def test_xtb_hermetic_fallback_when_binary_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)

    res = run_xtb_job(
        job_dir=tmp_path,
        xyz="2\nH2\nH 0 0 0\nH 0 0 0.74\n",
        charge=0,
        multiplicity=1,
        params={"gfn": 2},
    )

    assert res["returncode"] == 0
    assert res.get("hermetic") is True
    scalars = res.get("scalars", {})
    assert scalars.get("E_total_hartree") is not None
    assert scalars.get("gap_eV") is not None
    assert scalars.get("dipole_D") is not None


def test_xtb_hermetic_generates_placeholder_cubes(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)

    res = run_xtb_job(
        job_dir=tmp_path,
        xyz="2\nH2\nH 0 0 0\nH 0 0 0.74\n",
        charge=0,
        multiplicity=1,
        params={"gfn": 2, "cubes": True},
    )

    artifacts = res.get("artifacts", [])
    names = {a.get("name") for a in artifacts}
    assert {"homo.cube", "lumo.cube"} <= names
    for art in artifacts:
        if art.get("name") in {"homo.cube", "lumo.cube"}:
            meta = art.get("metadata", {})
            assert meta.get("valid") is True


@pytest.mark.skipif(shutil.which("xtb") is None, reason="xtb not installed")
def test_xtb_end_to_end_reads_json(tmp_path):
    infile = tmp_path / "dummy.inp"
    (tmp_path / "xtbout.json").write_text(
        json.dumps({"energy": -40.12, "homo_lumo_gap_ev": 3.21, "dipole_debye": 1.84}),
        encoding="utf-8",
    )
    infile.write_text("$dummy", encoding="utf-8")
    res = run_xtb(infile=str(infile))
    assert res["gap"] > 0
