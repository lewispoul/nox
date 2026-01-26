from typing import Literal

from pydantic import BaseModel


class XTBParams(BaseModel):
    gfn: int = 2
    opt: bool = True
    hess: bool = False
    uhf: bool = False
    chrg: int = 0
    json_output: bool = True
    cubes: bool = False


class JobInputs(BaseModel):
    xyz: str
    charge: int = 0
    multiplicity: int = 1
    params: XTBParams = XTBParams()


class JobRequest(BaseModel):
    engine: Literal["xtb"] = "xtb"
    kind: str = "opt_properties"
    inputs: JobInputs


class JobStatus(BaseModel):
    job_id: str
    state: str
    progress: float = 0.0
    message: str = ""
