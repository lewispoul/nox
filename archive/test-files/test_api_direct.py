#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient

from api.main import app


def test_api():
    client = TestClient(app)

    # Test /health
    print("Testing /health...")
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Test POST /jobs
    print("\nTesting POST /jobs...")
    job_req = {
        "engine": "xtb",
        "kind": "opt_properties",
        "inputs": {
            "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
            "charge": 0,
            "multiplicity": 1,
        },
    }
    response = client.post("/jobs", json=job_req)
    print(f"Status: {response.status_code}")
    job_data = response.json()
    print(f"Response: {job_data}")
    assert response.status_code == 200
    assert "job_id" in job_data
    assert job_data["state"] == "completed"

    job_id = job_data["job_id"]

    # Test GET /jobs/{job_id}
    print(f"\nTesting GET /jobs/{job_id}...")
    response = client.get(f"/jobs/{job_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200

    # Test GET /jobs/{job_id}/artifacts
    print(f"\nTesting GET /jobs/{job_id}/artifacts...")
    response = client.get(f"/jobs/{job_id}/artifacts")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")
    assert response.status_code == 200
    assert "scalars" in result
    assert "E_total_hartree" in result["scalars"]

    print("\n✅ All API tests passed! The minimal Nox API is working correctly.")
    print(f"📋 Scalars found: {list(result['scalars'].keys())}")


if __name__ == "__main__":
    test_api()
