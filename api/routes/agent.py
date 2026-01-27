from __future__ import annotations

import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from api.schemas.agent import AgentAskRequest, AgentRunRequest
from api.schemas.job import JobRequest
from api.schemas.psi4_job import Psi4JobRequest
from api.services.jobs_store import get_store
from api.services.queue import submit_job

router = APIRouter()

_conversations: Dict[str, Dict[str, Any]] = {}


def _session_id(req: Request) -> str:
    return req.headers.get("X-Session-Id", "default")


@router.post("/agent/run")
async def agent_run(body: AgentRunRequest) -> Dict[str, Any]:
    intent: str = body.intent.lower()
    params = body.params

    if intent.startswith("xtb"):
        try:
            jr = JobRequest(**params)
        except Exception as e:
            raise HTTPException(422, f"Invalid XTB params: {e}")
        job_id = submit_job("xtb", {"job_request": jr.model_dump_json()})

    elif intent.startswith("psi4"):
        try:
            jr = Psi4JobRequest(**params)
        except Exception as e:
            raise HTTPException(422, f"Invalid Psi4 params: {e}")
        job_id = submit_job("psi4", {"job_request": jr.model_dump_json()})

    elif intent.startswith("cj"):
        job_id = submit_job("cj", {"cj_request": params})

    else:
        raise HTTPException(400, f"Unknown intent: {intent}")

    j = get_store().get(job_id)
    if not j:
        raise HTTPException(500, "Failed to create job")
    return {"job_id": job_id, "state": j.state}


@router.post("/agent/ask")
async def agent_ask(request: Request, body: AgentAskRequest) -> Dict[str, Any]:
    question: str = body.q.lower()
    params = body.params

    sid = _session_id(request)
    convo = _conversations.setdefault(sid, {"history": []})
    convo["history"].append({"role": "user", "q": question})

    job_id: Optional[str] = None
    plan: str = ""

    if "psi4" in question:
        plan = "Run Psi4 opt + energy"
        try:
            jr = Psi4JobRequest(**params)
        except Exception as e:
            raise HTTPException(422, f"Invalid Psi4 params: {e}")
        job_id = submit_job("psi4", {"job_request": jr.model_dump_json()})

    elif "cj" in question or "chapman" in question:
        plan = "Compute CJ conditions via Cantera"
        job_id = submit_job("cj", {"cj_request": params})

    elif "xtb" in question:
        plan = "Run XTB opt + properties"
        try:
            jr = JobRequest(**params)
        except Exception as e:
            raise HTTPException(422, f"Invalid XTB params: {e}")
        job_id = submit_job("xtb", {"job_request": jr.model_dump_json()})

    else:
        if re.search(r"\bxyz\b|\bsmiles\b", question):
            plan = "Default to XTB optimization"
            jr = JobRequest(**params)
            job_id = submit_job("xtb", {"job_request": jr.model_dump_json()})
        else:
            raise HTTPException(400, "Could not determine intent; specify 'params'")

    j = get_store().get(job_id)
    convo["history"].append({"role": "system", "plan": plan, "job_id": job_id})
    return {"job_id": job_id, "state": j.state if j else "unknown", "plan": plan}


@router.get("/agent/state/{job_id}")
def agent_state(job_id: str) -> Dict[str, Any]:
    j = get_store().get(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, "state": j.state, "error": j.error, "result": j.result}
