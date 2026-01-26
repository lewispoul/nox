from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


class IAMClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.base_url = base_url or os.getenv("IAM_BASE_URL", "").rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        if not self.base_url:
            raise RuntimeError("IAM_BASE_URL not configured")
        return f"{self.base_url}{path}"

    async def run_xtb(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(self._url("/run_xtb"), json=payload)
            r.raise_for_status()
            return r.json()

    async def run_psi4(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(self._url("/run_psi4"), json=payload)
            r.raise_for_status()
            return r.json()

    async def predict_vod(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(self._url("/predict/vod"), json=payload)
            r.raise_for_status()
            return r.json()

    async def predict_cj(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(self._url("/predict/cj"), json=payload)
            r.raise_for_status()
            return r.json()
