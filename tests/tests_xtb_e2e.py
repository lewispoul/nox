"""
End-to-end tests for XTB quantum chemistry calculations via API.

Tests the complete workflow:
1. Submit nitromethane optimization job
2. Poll for completion
3. Validate results and artifacts

Requires:
- Running API server at http://127.0.0.1:8080
- Redis server for Dramatiq queue
- XTB binary in PATH
- Dramatiq worker running
"""

import shutil

import anyio
import httpx
import pytest

API = "http://127.0.0.1:8081"

pytestmark = pytest.mark.skipif(
    shutil.which("xtb") is None, reason="xtb not available in PATH"
)

XYZ_NM = """12
nitromethane
C 0.000000 0.000000 0.000000
H 0.000000 0.000000 1.089000
H 1.026719 0.000000 -0.363000
H -0.513360 -0.889165 -0.363000
N -0.513360 0.889165 -0.363000
O -1.713360 0.889165 -0.363000
O 0.186640 1.779165 -0.363000
"""


async def wait_done(client: httpx.AsyncClient, job_id: str, timeout: int = 180) -> str:
    """Poll job status until completion or timeout."""
    for _ in range(timeout):
        r = await client.get(f"{API}/jobs/{job_id}")
        r.raise_for_status()
        state = r.json()["state"]
        if state in {"completed", "failed"}:
            return state
        await anyio.sleep(1)
    return "timeout"


@pytest.mark.anyio
async def test_xtb_job_e2e():
    """Test complete XTB job workflow with nitromethane optimization."""
    async with httpx.AsyncClient() as client:
        # Submit job
        payload = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": XYZ_NM,
                "charge": 0,
                "multiplicity": 1,
                "params": {"gfn": 2, "opt": True, "json": True},
            },
        }

        r = await client.post(f"{API}/jobs", json=payload)
        r.raise_for_status()
        job_data = r.json()
        job_id = job_data["job_id"]

        # Poll until completion
        state = await wait_done(client, job_id, timeout=180)
        assert state == "completed", f"Job {job_id} state: {state}"

        # Validate artifacts
        r2 = await client.get(f"{API}/jobs/{job_id}/artifacts")
        r2.raise_for_status()
        data = r2.json()

        # Check scalars
        scalars = data["scalars"]
        assert "E_total_hartree" in scalars
        assert isinstance(scalars["E_total_hartree"], float)

        # Optional scalars may be present
        if "gap_eV" in scalars:
            assert isinstance(scalars["gap_eV"], float)
        if "dipole_D" in scalars:
            assert isinstance(scalars["dipole_D"], float)

        # Check artifacts
        artifact_names = [a["name"] for a in data["artifacts"]]
        assert "xtb.log" in artifact_names, f"Missing xtb.log in {artifact_names}"
        assert (
            "xtbout.json" in artifact_names
        ), f"Missing xtbout.json in {artifact_names}"


@pytest.mark.anyio
async def test_api_health():
    """Verify API is running and healthy."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API}/health")
        r.raise_for_status()
        assert r.json()["status"] == "ok"


@pytest.mark.anyio
async def test_simple_h2_job():
    """Test with simple H2 molecule for faster execution."""
    xyz_h2 = """2
H2
H 0 0 0
H 0 0 0.74
"""

    async with httpx.AsyncClient() as client:
        payload = {
            "engine": "xtb",
            "kind": "opt_properties",
            "inputs": {
                "xyz": xyz_h2,
                "charge": 0,
                "multiplicity": 1,
                "params": {"gfn": 2, "opt": True, "json": True},
            },
        }

        r = await client.post(f"{API}/jobs", json=payload)
        r.raise_for_status()
        job_id = r.json()["job_id"]

        state = await wait_done(client, job_id, timeout=60)
        assert state == "completed"

        # Check basic artifacts exist
        r2 = await client.get(f"{API}/jobs/{job_id}/artifacts")
        r2.raise_for_status()
        data = r2.json()

        assert "E_total_hartree" in data["scalars"]
        artifact_names = [a["name"] for a in data["artifacts"]]
        assert "xtb.log" in artifact_names
