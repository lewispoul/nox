from pathlib import Path

from nox.chemistry.cj import run_cj


def test_cj_hermetic_fallback(tmp_path, monkeypatch):
    # Force hermetic path by pretending Cantera is unavailable
    monkeypatch.setattr("nox.chemistry.cj._has_cantera", lambda: False)

    res = run_cj(Path(tmp_path), {"reactants": {"H2": 2, "O2": 1}, "T0": 300.0, "P0": 101325.0})

    assert res.get("returncode") == 0
    scalars = res.get("scalars", {})
    assert scalars.get("Pcj_Pa") is not None
    assert scalars.get("Tcj_K") is not None
    assert scalars.get("Dcj_m_per_s") is not None
    artifacts = res.get("artifacts", [])
    assert any(a.get("name") == "cj_results.csv" for a in artifacts)
