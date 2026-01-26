from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Psi4Params(BaseModel):
    method: str = "HF"
    basis: str = "6-31G*"
    opt: bool = True
    freq: bool = False
    scf_type: str | None = None
    solvent: str | None = None


class Psi4Inputs(BaseModel):
    xyz: str
    charge: int = 0
    multiplicity: int = 1
    params: Psi4Params = Psi4Params()


class Psi4JobRequest(BaseModel):
    engine: Literal["psi4"] = "psi4"
    kind: str = "opt_scf_freq"
    inputs: Psi4Inputs
