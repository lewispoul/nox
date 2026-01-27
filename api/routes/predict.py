from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from api.schemas.predict import CJRequest, VoDRequest
from api.services.jobs_store import get_store
from api.services.queue import submit_job
from nox.predict.vod import kamlet_jacobs_vod_kms, keshavarz_vod_kms, simple_ml_vod_kms

router = APIRouter()


@router.post("/predict/cj")
async def predict_cj(body: CJRequest) -> Dict[str, Any]:
    """Submit a CJ detonation prediction job.

    Body example:
    {
      "reactants": {"H2": 2, "O2": 1},
      "T0": 300.0,
      "P0": 101325.0
    }
    """
    job_id = submit_job("cj", {"cj_request": body.model_dump()})
    j = get_store().get(job_id)
    if not j:
        raise HTTPException(500, "Failed to create job")
    return {"job_id": job_id, "state": j.state}


@router.post("/predict/vod")
async def predict_vod(body: VoDRequest) -> Dict[str, Any]:
    """Compute VoD via Kamlet–Jacobs, Keshavarz, and a simple ML baseline.

    Body may contain inputs for KJ:
      - rho_g_cc, N, M, Q_cal_g
    For Keshavarz-style:
      - rho_g_cc, OB (oxygen balance, percent), optional Q_MJ_kg
    For ML baseline:
      - arbitrary features {rho_g_cc, Q_MJ_kg, OB, N, M}
    """
    body_dict = body.model_dump(exclude_none=True)
    out: Dict[str, Any] = {"models": {}}

    # Kamlet–Jacobs
    if all(k in body_dict for k in ("rho_g_cc", "N", "M", "Q_cal_g")):
        d = kamlet_jacobs_vod_kms(
            float(body_dict["rho_g_cc"]), float(body_dict["N"]), float(body_dict["M"]), float(body_dict["Q_cal_g"])
        )
        out["models"]["kamlet_jacobs"] = {"VoD_km_s": d}

    # Keshavarz
    if all(k in body_dict for k in ("rho_g_cc", "OB")):
        d2 = keshavarz_vod_kms(
            float(body_dict["rho_g_cc"]), float(body_dict["OB"]), float(body_dict.get("Q_MJ_kg", 0.0))
        )
        out["models"]["keshavarz"] = {"VoD_km_s": d2}

    if not out["models"]:
        raise HTTPException(
            422,
            "Provide inputs for KJ (rho_g_cc,N,M,Q_cal_g) and/or Keshavarz (rho_g_cc,OB).",
        )

    # Simple ML
    d3 = simple_ml_vod_kms({k: float(v) for k, v in body_dict.items() if isinstance(v, (int, float))})
    out["models"]["ml_baseline"] = {"VoD_km_s": d3}
    return out
