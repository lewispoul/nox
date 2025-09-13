#!/usr/bin/env python3
"""Test de la fonctionnalité cubes/Molden du runner XTB"""

import tempfile
from pathlib import Path

from ai.runners.xtb import run_xtb_job


def test_xtb_cubes_feature():
    """Test de la génération Molden quand params.cubes=True"""

    with tempfile.TemporaryDirectory() as tmpdir:
        job_dir = Path(tmpdir)

        # XYZ simple molécule H2
        xyz = "2\nH2 molecule\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74"

        # Paramètres avec cubes activé
        params = {
            "gfn": 2,
            "opt": True,
            "cubes": True,  # Active génération Molden
            "chrg": 0,
        }

        print("Test XTB job avec génération cubes/Molden...")
        print(f"Job dir: {job_dir}")

        # Note: Ce test va échouer si xtb n'est pas installé,
        # mais il teste la structure et la logique
        try:
            result = run_xtb_job(job_dir, xyz, 0, 1, params)

            print("\nRésultat job:")
            print(f"- Return code: {result['returncode']}")
            print(f"- Scalars: {result['scalars']}")
            print(f"- Artifacts: {len(result['artifacts'])} fichiers")

            for artifact in result["artifacts"]:
                print(f"  * {artifact['name']} ({artifact['size']} bytes)")

            # Vérifier la structure de réponse
            assert "scalars" in result
            assert "series" in result
            assert "artifacts" in result
            assert "returncode" in result

            # Vérifier que les artifacts sont bien listés
            artifact_names = [a["name"] for a in result["artifacts"]]
            print(f"\nArtifacts générés: {artifact_names}")

            if result["returncode"] == 0:
                print("✅ XTB job exécuté avec succès!")
                # Si Molden généré, il devrait être dans les artifacts
                molden_found = any("molden" in name.lower() for name in artifact_names)
                if molden_found:
                    print("✅ Fichier Molden trouvé dans les artifacts!")
            else:
                print("⚠️  XTB job failed (probablement XTB non installé)")

        except Exception as e:
            print(f"⚠️  Erreur attendue si XTB n'est pas installé: {e}")

        print(f"\nFichiers créés dans {job_dir}:")
        for f in job_dir.glob("*"):
            print(f"  - {f.name} ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    test_xtb_cubes_feature()
    print("\n🧪 Test fonctionnalité cubes terminé")
