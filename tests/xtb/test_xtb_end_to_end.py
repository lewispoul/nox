import json
import pathlib
import shutil

import pytest

from nox.runners.xtb import run_xtb

DATA = pathlib.Path(__file__).parent / "data"


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
