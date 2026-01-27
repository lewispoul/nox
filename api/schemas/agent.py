from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Request body for agent run endpoint."""

    intent: str = Field(..., description="Intent keyword (xtb, psi4, cj, etc.)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the job")


class AgentAskRequest(BaseModel):
    """Request body for agent ask endpoint."""

    q: str = Field(..., description="Question or query for the agent")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Optional parameters for job execution"
    )
