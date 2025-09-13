#!/usr/bin/env python3
"""Test rapide du nouveau runner XTB avec parsing robuste"""

import json
import tempfile
from pathlib import Path

from ai.runners.xtb import _parse_from_text, _parse_xtbout_json


def test_json_parsing():
    """Test du parsing JSON robuste avec différentes structures"""

    # Structure JSON classique XTB
    test_json1 = {
        "energy": {"total": -5.123456},
        "gap": 2.34,
        "dipole": {"total": 1.89},
    }

    # Structure alternative
    test_json2 = {
        "results": {"total_energy": -3.987654, "gap": 4.56},
        "properties": {"dipole": {"total": 0.123}},
    }

    # Structure minimal
    test_json3 = {"etot": -1.234567}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_json1, f)
        json_path = Path(f.name)

    try:
        result1 = _parse_xtbout_json(json_path)
        print("Test JSON 1:", result1)
        assert "E_total_hartree" in result1
        assert "gap_eV" in result1
        assert "dipole_D" in result1

        # Test structure alternative
        with open(json_path, "w") as f:
            json.dump(test_json2, f)

        result2 = _parse_xtbout_json(json_path)
        print("Test JSON 2:", result2)
        assert "E_total_hartree" in result2

        # Test structure minimal
        with open(json_path, "w") as f:
            json.dump(test_json3, f)

        result3 = _parse_xtbout_json(json_path)
        print("Test JSON 3:", result3)
        assert "E_total_hartree" in result3

    finally:
        json_path.unlink()

    print("✅ Tests JSON parsing réussis")


def test_text_parsing():
    """Test du parsing texte avec expressions régulières"""

    # Exemple de sortie XTB typique
    sample_output = """
 | TOTAL ENERGY               -5.123456 Eh   |
 | GRADIENT NORM               0.000123 Eh/α |
 | HOMO-LUMO GAP               2.345 eV       |
 |                                            |
 molecular dipole:
           x           y           z       total   Debye
      -0.123      0.456     -0.789     1.234
    
 dipole moment from electron density (au)
      X       Y       Z   
   0.123  -0.456   0.789  dipole moment  total:   1.234 Debye
    """

    result = _parse_from_text(sample_output)
    print("Test text parsing:", result)

    assert "E_total_hartree" in result
    assert abs(result["E_total_hartree"] - (-5.123456)) < 1e-6

    assert "gap_eV" in result
    assert abs(result["gap_eV"] - 2.345) < 1e-3

    assert "dipole_D" in result
    assert abs(result["dipole_D"] - 1.234) < 1e-3

    print("✅ Test text parsing réussi")


if __name__ == "__main__":
    test_json_parsing()
    test_text_parsing()
    print("\n🎉 Tous les tests du nouveau runner XTB sont OK!")
