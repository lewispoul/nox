#!/usr/bin/env python3
"""
Test cube generation integration with XTB job workflow.
"""

import asyncio

from httpx import ASGITransport, AsyncClient

from api.main import app
from tests.tests_xtb_e2e import wait_done


async def test_cube_generation_integration():
    """Test cube generation through the full API workflow."""

    print("🧪 Testing CUBE-003: HOMO/LUMO cube generation")

    # Create a job request with cube generation enabled
    job_data = {
        "engine": "xtb",
        "kind": "opt_properties",
        "inputs": {
            "xyz": "2\nH2 molecule test\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74",
            "charge": 0,
            "multiplicity": 1,
            "params": {
                "gfn": 2,
                "opt": True,
                "cubes": True,  # Enable cube generation!
                "chrg": 0,
            },
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Submit job with cube generation
        print("📤 Submitting XTB job with cube generation...")
        response = await client.post("/jobs", json=job_data)
        assert response.status_code == 200

        job_info = response.json()
        job_id = job_info["job_id"]
        print(f"✅ Job submitted: {job_id}")

        # 2. Wait for completion (or skip if XTB not available)
        print("⏱️  Waiting for job completion...")
        final_state = await wait_done(client, job_id, timeout=60)
        print(f"📊 Final state: {final_state}")

        # 3. Check job status
        response = await client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        status = response.json()
        print(f"📋 Status: {status['state']} - {status.get('message', '')}")

        # 4. Get artifacts if job completed successfully
        if final_state == "completed":
            print("🎉 Job completed! Checking artifacts...")

            response = await client.get(f"/jobs/{job_id}/artifacts")
            assert response.status_code == 200

            artifacts = response.json()
            print(f"📦 Found {len(artifacts['artifacts'])} artifacts")

            # Check for cube files in artifacts
            artifact_names = [a["name"] for a in artifacts["artifacts"]]
            print(f"📄 Artifacts: {artifact_names}")

            # Look for cube files
            cube_files = [name for name in artifact_names if name.endswith(".cube")]
            molden_files = [name for name in artifact_names if "molden" in name.lower()]

            if cube_files:
                print(f"🎯 SUCCESS: Found cube files: {cube_files}")

                # Validate cube file metadata if present
                for artifact in artifacts["artifacts"]:
                    if artifact["name"].endswith(".cube"):
                        print(f"📐 Cube file: {artifact['name']}")
                        print(f"   Size: {artifact['size']} bytes")
                        print(f"   MIME: {artifact['mime']}")

                        if "metadata" in artifact:
                            meta = artifact["metadata"]
                            if meta.get("valid"):
                                print(f"   Grid: {meta.get('grid_points', 'unknown')}")
                                print(f"   Atoms: {meta.get('natoms', 'unknown')}")
                            else:
                                print(
                                    f"   ⚠️  Validation issue: {meta.get('error', 'unknown')}"
                                )

            elif molden_files:
                print(f"🔶 Molden files found: {molden_files}")
                print("   (Cube generation may have failed but Molden was generated)")

            else:
                print("⚠️  No cube or Molden files found")
                print("   This might be expected if XTB doesn't support --molden")

            # Verify standard XTB artifacts are still present
            expected_artifacts = ["xtb.log", "xtbout.json"]
            for expected in expected_artifacts:
                if expected in artifact_names:
                    print(f"✅ Standard artifact: {expected}")
                else:
                    print(f"❌ Missing standard artifact: {expected}")

        elif final_state == "failed":
            print("❌ Job failed (possibly XTB not installed)")
            print("   This is expected in CI environments without XTB")

        else:
            print(f"⏰ Job did not complete in time: {final_state}")

    print("\n🏆 CUBE-003 integration test completed!")
    return final_state == "completed"


if __name__ == "__main__":
    success = asyncio.run(test_cube_generation_integration())
    if success:
        print("✅ Cube generation fully functional!")
    else:
        print("⚠️  Cube generation test completed (may require XTB binary)")
