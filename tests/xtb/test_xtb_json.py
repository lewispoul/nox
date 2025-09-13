import json
import pathlib

import pytest

from nox.parsers.xtb_json import XTBParseError, parse_xtbout_text

DATA = pathlib.Path(__file__).parent / "data" / "xtbout.json"


def test_parse_xtbout_ok():
    text = DATA.read_text(encoding="utf-8")
    res = parse_xtbout_text(text)
    assert {"energy", "gap", "dipole"} <= res.keys()
    assert isinstance(res["energy"], float)
    assert isinstance(res["gap"], float)
    assert isinstance(res["dipole"], float)


def test_parse_xtbout_missing_field():
    bad = json.dumps({"energy": -1.0, "homo_lumo_gap_ev": 2.0})
    with pytest.raises(XTBParseError) as e:
        parse_xtbout_text(bad)
    assert "missing field(s)" in str(e.value)
