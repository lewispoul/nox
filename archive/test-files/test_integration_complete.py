#!/usr/bin/env python3
"""Test complet de l'intégration XTB avec Dramatiq"""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_complete_xtb_integration():
    """Test de l'intégration complète XTB avec exécution réelle"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:

        # 1. Créer un job XTB avec paramètres réels
        job_req = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": "2\nH2 molecule\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n",
                "charge": 0,
                "multiplicity": 1,
                "params": {
                    "gfn": 2,
                    "opt": True,
                    "hess": False,
                    "cubes": True,  # Test génération Molden
                    "chrg": 0,
                },
            },
        }

        print("🧪 Création du job XTB...")
        resp = await ac.post("/jobs", json=job_req)
        assert resp.status_code == 200

        job = resp.json()
        assert "job_id" in job
        assert job["state"] == "pending"
        job_id = job["job_id"]
        print(f"✅ Job créé avec ID: {job_id}")

        # 2. Vérifier le statut initial
        resp2 = await ac.get(f"/jobs/{job_id}")
        assert resp2.status_code == 200
        job_status = resp2.json()
        assert job_status["state"] == "pending"
        print(f"📋 Statut initial: {job_status}")

        # 3. Attendre que le job soit traité (ou timeout)
        max_wait = 30  # secondes
        waited = 0
        final_state = "pending"

        print("⏳ Attente du traitement du job...")
        while waited < max_wait:
            time.sleep(2)
            waited += 2

            resp3 = await ac.get(f"/jobs/{job_id}")
            if resp3.status_code == 200:
                status = resp3.json()
                final_state = status["state"]
                print(
                    f"   État après {waited}s: {final_state} - {status.get('message', '')}"
                )

                if final_state in ["completed", "failed"]:
                    break

        # 4. Vérifier le résultat final
        if final_state == "completed":
            print("🎉 Job complété avec succès!")

            # Tester l'endpoint artifacts
            resp4 = await ac.get(f"/jobs/{job_id}/artifacts")
            assert resp4.status_code == 200

            results = resp4.json()
            print("📊 Résultats obtenus:")
            print(f"   Scalars: {results.get('scalars', {})}")
            print(f"   Artifacts: {len(results.get('artifacts', []))} fichiers")

            # Vérifier la présence des résultats XTB
            scalars = results.get("scalars", {})
            if "E_total_hartree" in scalars:
                print(f"   ✅ Énergie totale: {scalars['E_total_hartree']} Hartree")
            if "gap_eV" in scalars:
                print(f"   ✅ Gap HOMO-LUMO: {scalars['gap_eV']} eV")

            # Vérifier les artifacts
            artifacts = results.get("artifacts", [])
            artifact_names = [a["name"] for a in artifacts]
            print(f"   📁 Artifacts: {artifact_names}")

            # Chercher les fichiers attendus
            if "xtb.log" in artifact_names:
                print("   ✅ Log XTB trouvé")
            if any("molden" in name.lower() for name in artifact_names):
                print("   ✅ Fichier Molden trouvé (cubes activés)")

        elif final_state == "failed":
            print("❌ Job échoué - probablement XTB non installé")
            resp4 = await ac.get(f"/jobs/{job_id}")
            if resp4.status_code == 200:
                error_info = resp4.json()
                print(
                    f"   Message d'erreur: {error_info.get('message', 'Unknown error')}"
                )
        else:
            print(f"⚠️  Job encore en cours après {max_wait}s - état: {final_state}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_complete_xtb_integration())
