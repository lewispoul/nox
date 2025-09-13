#!/usr/bin/env python3
"""Test de la logique XTB en mode synchrone (simule le worker Dramatiq)"""

import uuid

from api.routes.jobs import JOBS, run_job
from api.schemas.job import JobRequest
from api.services.storage import job_dir


def test_xtb_logic_sync():
    """Test de la logique XTB sans Dramatiq (mode synchrone)"""

    # 1. Créer une requête job
    job_request = JobRequest(
        engine="xtb",
        kind="opt_properties",
        inputs={
            "xyz": "2\nH2 molecule\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n",
            "charge": 0,
            "multiplicity": 1,
            "params": {"gfn": 2, "opt": True, "hess": False, "cubes": True, "chrg": 0},
        },
    )

    # 2. Simuler la création du job
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"state": "pending", "message": "Job queued", "result": None}

    print(f"🧪 Test XTB job ID: {job_id}")
    print(f"📋 État initial: {JOBS[job_id]}")

    # 3. Exécuter la logique du worker (fonction run_job) directement
    print("⚡ Exécution directe de la logique worker...")

    try:
        # Appel direct de l'actor logic (sans Dramatiq)
        req_json = job_request.model_dump_json()
        run_job.fn(job_id, req_json)  # .fn pour appel direct sans queue

        # 4. Vérifier le résultat
        final_state = JOBS[job_id]
        print(f"📊 État final: {final_state['state']}")
        print(f"💬 Message: {final_state['message']}")

        if final_state["state"] == "completed":
            result = final_state["result"]
            print("🎉 Succès! Résultats:")
            print(f"   Scalars: {result.get('scalars', {})}")
            print(f"   Artifacts: {len(result.get('artifacts', []))} fichiers")

            for artifact in result.get("artifacts", []):
                print(f"      📁 {artifact['name']} ({artifact['size']} bytes)")

            # Vérifier le dossier de job
            jd = job_dir(job_id)
            print(f"   📂 Dossier job: {jd}")
            if jd.exists():
                files = list(jd.glob("*"))
                print(f"      Fichiers créés: {[f.name for f in files]}")

        elif final_state["state"] == "failed":
            print(f"❌ Échec: {final_state['message']}")

    except Exception as e:
        print(f"💥 Erreur pendant l'exécution: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_xtb_logic_sync()
