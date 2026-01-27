from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class CJRequest(BaseModel):
    """Request body for Chapman-Jouguet (CJ) detonation prediction."""

    reactants: Dict[str, float] = Field(..., description="Reactants as {species: moles}")
    T0: float = Field(default=300.0, description="Initial temperature (K)")
    P0: float = Field(default=101325.0, description="Initial pressure (Pa)")


class VoDRequest(BaseModel):
    """Request body for Velocity of Detonation (VoD) prediction.
    
    Supports multiple model inputs:
    - Kamlet-Jacobs: rho_g_cc, N, M, Q_cal_g
    - Keshavarz: rho_g_cc, OB (oxygen balance)
    - ML baseline: arbitrary_features
    """

    rho_g_cc: float | None = Field(
        default=None, description="Density in g/cm³"
    )
    N: float | None = Field(
        default=None, description="Number of moles of gas products (KJ model)"
    )
    M: float | None = Field(
        default=None, description="Average molecular weight of products (KJ model)"
    )
    Q_cal_g: float | None = Field(
        default=None, description="Heat of detonation in cal/g (KJ model)"
    )
    Q_MJ_kg: float | None = Field(
        default=None, description="Heat of detonation in MJ/kg (Keshavarz model)"
    )
    OB: float | None = Field(
        default=None, description="Oxygen balance in percent (Keshavarz model)"
    )
    arbitrary_features: Dict[str, float] | None = Field(
        default=None, description="Arbitrary features for ML baseline"
    )
