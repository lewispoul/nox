from __future__ import annotations

from typing import Dict, Optional


def kamlet_jacobs_vod_kms(
    rho_g_cc: float,
    N_mol_gas_per_g: float,
    M_g_mol: float,
    Q_cal_g: float,
) -> float:
    """Compute VoD (km/s) using a standard Kamlet–Jacobs form.

    D (km/s) = 1.01 * sqrt(N * M * Q) * (1 + 1.30 * rho)
    where rho: density (g/cc), N: moles gaseous products per gram,
    M: average molar mass (g/mol), Q: heat of detonation (cal/g).
    """
    from math import sqrt

    return 1.01 * (N_mol_gas_per_g * M_g_mol * Q_cal_g) ** 0.5 * (1.0 + 1.30 * rho_g_cc)


def keshavarz_vod_kms(
    rho_g_cc: float,
    ob: float,
    q_MJ_kg: Optional[float] = None,
) -> float:
    """A simple Keshavarz-style linear correlation.

    This is a placeholder linear model using density and oxygen balance (OB in %).
    Literature contains multiple fitted forms; coefficients here are illustrative
    and should be calibrated on a dataset.
    """
    a0, a1, a2 = 1.0, 1.2, 0.01  # placeholder coefficients
    base = a0 + a1 * rho_g_cc + a2 * ob
    if q_MJ_kg is not None:
        base += 0.05 * q_MJ_kg  # small sensitivity to energy content
    return max(base, 0.0)


def simple_ml_vod_kms(features: Dict[str, float]) -> float:
    """Very small baseline linear model without external deps.

    Uses a fixed-weight linear combination over common features.
    """
    # Default weights; tune later
    weights = {
        "rho_g_cc": 1.1,
        "Q_MJ_kg": 0.06,
        "OB": 0.012,
        "N": 0.4,
        "M": -0.002,
    }
    bias = 0.5
    s = bias
    for k, w in weights.items():
        s += w * float(features.get(k, 0.0))
    return max(s, 0.0)
