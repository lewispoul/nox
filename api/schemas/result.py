from typing import Dict, List

from pydantic import BaseModel


class Artifact(BaseModel):
    name: str
    path: str
    mime: str = "application/octet-stream"
    size: int


class ResultBundle(BaseModel):
    scalars: Dict[str, float] = {}
    series: Dict[str, List[List[float]]] = {}
    artifacts: List[Artifact] = []
