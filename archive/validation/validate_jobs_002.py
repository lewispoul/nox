#!/usr/bin/env python3
"""
JOBS-002 Validation Script

This script validates the complete implementation of JOBS-002:
- Job creation via POST /jobs
- Job status polling via GET /jobs/{id}
- Artifact retrieval via GET /jobs/{id}/artifacts
- Complete workflow: submit → poll → results
- Dramatiq background processing integration
"""

import sys
import time

import requests

API_BASE = "http://127.0.0.1:8082"


def test_health_check() -> bool:
    """Test API health endpoint"""
    print("🔍 Testing API health...")
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ Health check failed: {resp.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Health check error: {e}")
        return False


def test_job_creation() -> str:
    """Test job creation and return job ID"""
    print("\n🚀 Testing job creation...")

    job_request = {
        "engine": "xtb",
        "kind": "opt_properties",
        "inputs": {
            "xyz": "2\nH2\nH 0 0 0\nH 0 0 0.74\n",
            "charge": 0,
            "multiplicity": 1,
            "params": {"cubes": True},  # Test cube generation
        },
    }

    resp = requests.post(f"{API_BASE}/jobs", json=job_request)

    if resp.status_code != 200:
        print(f"❌ Job creation failed: {resp.status_code}")
        print(f"Response: {resp.text}")
        return ""

    job_data = resp.json()
    job_id = job_data.get("job_id", "")

    print(f"✅ Job created: {job_id}")
    print(f"   State: {job_data.get('state')}")
    print(f"   Message: {job_data.get('message')}")

    # Validate response structure
    required_fields = ["job_id", "state", "message", "progress"]
    missing = [f for f in required_fields if f not in job_data]
    if missing:
        print(f"❌ Missing fields in response: {missing}")
        return ""

    if job_data["state"] != "pending":
        print(f"❌ Expected state 'pending', got '{job_data['state']}'")
        return ""

    return job_id


def test_job_polling(job_id: str, max_wait: int = 120) -> str:
    """Test job status polling until completion"""
    print(f"\n⏳ Polling job {job_id} (max {max_wait}s)...")

    start_time = time.time()
    states_seen = []

    for i in range(max_wait):
        try:
            resp = requests.get(f"{API_BASE}/jobs/{job_id}")

            if resp.status_code != 200:
                print(f"❌ Status check failed: {resp.status_code}")
                return "failed"

            status_data = resp.json()
            state = status_data["state"]
            message = status_data.get("message", "")
            progress = status_data.get("progress", 0.0)

            if state not in states_seen:
                states_seen.append(state)
                print(f"   [{i+1:02d}s] State: {state} (progress: {progress:.1f}) - {message}")
            elif i % 10 == 0:  # Show update every 10s
                print(f"   [{i+1:02d}s] Still: {state} - {message}")

            if state in ["completed", "failed"]:
                elapsed = time.time() - start_time
                print(f"✅ Job finished in {elapsed:.1f}s")
                print(f"   Final state: {state}")
                print(f"   States seen: {' → '.join(states_seen)}")
                return state

            time.sleep(1)

        except requests.RequestException as e:
            print(f"❌ Polling error: {e}")
            return "error"

    print(f"❌ Job did not complete within {max_wait} seconds")
    return "timeout"


def test_artifact_retrieval(job_id: str) -> bool:
    """Test artifact retrieval for completed job"""
    print(f"\n📊 Testing artifact retrieval for {job_id}...")

    resp = requests.get(f"{API_BASE}/jobs/{job_id}/artifacts")

    if resp.status_code != 200:
        print(f"❌ Artifact retrieval failed: {resp.status_code}")
        print(f"Response: {resp.text}")
        return False

    artifacts_data = resp.json()

    print("✅ Artifacts retrieved successfully")

    # Validate structure
    if "scalars" not in artifacts_data:
        print("❌ Missing 'scalars' in response")
        return False

    if "artifacts" not in artifacts_data:
        print("❌ Missing 'artifacts' in response")
        return False

    scalars = artifacts_data["scalars"]
    artifacts = artifacts_data["artifacts"]

    print(f"   Scalars: {len(scalars)} values")
    if scalars:
        for key, value in list(scalars.items())[:3]:  # Show first 3
            print(f"     - {key}: {value}")
        if len(scalars) > 3:
            print(f"     ... and {len(scalars) - 3} more")

    print(f"   Artifacts: {len(artifacts)} files")
    for artifact in artifacts:
        name = artifact.get("name", "unnamed")
        fmt = artifact.get("format", "unknown")
        size = artifact.get("size_bytes", 0)
        print(f"     - {name} ({fmt}, {size} bytes)")

    return True


def test_job_not_found() -> bool:
    """Test handling of non-existent jobs"""
    print("\n🔍 Testing non-existent job handling...")

    fake_id = "nonexistent_job_id"
    resp = requests.get(f"{API_BASE}/jobs/{fake_id}")

    if resp.status_code != 404:
        print(f"❌ Expected 404, got {resp.status_code}")
        return False

    error_data = resp.json()
    if error_data.get("detail") != "Job not found":
        print(f"❌ Unexpected error message: {error_data}")
        return False

    print("✅ Non-existent job correctly returns 404")
    return True


def test_invalid_job_request() -> bool:
    """Test handling of invalid job requests"""
    print("\n🔍 Testing invalid job request handling...")

    invalid_request = {
        "engine": "xtb",
        "kind": "opt_properties",
        # Missing required 'inputs' field
    }

    resp = requests.post(f"{API_BASE}/jobs", json=invalid_request)

    if resp.status_code != 422:
        print(f"❌ Expected 422, got {resp.status_code}")
        return False

    print("✅ Invalid job request correctly returns 422")
    return True


def test_concurrent_jobs() -> bool:
    """Test handling multiple concurrent jobs"""
    print("\n🔄 Testing concurrent job submission...")

    job_requests = []
    for i in range(3):
        job_requests.append(
            {
                "engine": "xtb",
                "kind": "opt_properties",
                "inputs": {
                    "xyz": f"2\nH2_job{i}\nH 0 0 0\nH 0 0 0.74\n",
                    "charge": 0,
                    "multiplicity": 1,
                },
            }
        )

    job_ids = []
    for i, req in enumerate(job_requests):
        resp = requests.post(f"{API_BASE}/jobs", json=req)
        if resp.status_code != 200:
            print(f"❌ Job {i+1} creation failed: {resp.status_code}")
            return False
        job_ids.append(resp.json()["job_id"])

    print(f"✅ {len(job_ids)} jobs created successfully")

    # Verify all jobs can be queried
    for i, job_id in enumerate(job_ids):
        resp = requests.get(f"{API_BASE}/jobs/{job_id}")
        if resp.status_code != 200:
            print(f"❌ Job {i+1} status check failed")
            return False

    print("✅ All concurrent jobs can be queried")
    return True


def main():
    """Run complete JOBS-002 validation"""
    print("=" * 60)
    print("🧪 JOBS-002 COMPLETE VALIDATION")
    print("=" * 60)

    # Test sequence
    tests = [
        ("Health Check", test_health_check),
        ("Job Not Found", test_job_not_found),
        ("Invalid Job Request", test_invalid_job_request),
        ("Concurrent Jobs", test_concurrent_jobs),
    ]

    # Run basic tests
    passed = 0
    total = len(tests)

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n❌ {name} test failed")
        except Exception as e:
            print(f"\n💥 {name} test crashed: {e}")

    # Run complete workflow test
    print("\n" + "=" * 60)
    print("🔄 COMPLETE WORKFLOW TEST")
    print("=" * 60)

    workflow_success = False
    try:
        job_id = test_job_creation()
        if job_id:
            final_state = test_job_polling(job_id)
            if final_state == "completed":
                workflow_success = test_artifact_retrieval(job_id)
                total += 1
                if workflow_success:
                    passed += 1
            else:
                print(f"\n❌ Workflow test failed: job ended with state '{final_state}'")
                total += 1
        else:
            total += 1
    except Exception as e:
        print(f"\n💥 Workflow test crashed: {e}")
        total += 1

    # Final results
    print("\n" + "=" * 60)
    print("📊 VALIDATION RESULTS")
    print("=" * 60)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 ALL TESTS PASSED - JOBS-002 FULLY IMPLEMENTED!")
        print("\n✅ Dramatiq jobs from API with state polling is ACTIVE")
        print("✅ POST /jobs enqueues jobs")
        print("✅ GET /jobs/<id> shows states")
        print("✅ GET /jobs/<id>/artifacts returns results")
        print("✅ Complete submit → poll → results workflow functional")
        sys.exit(0)
    else:
        print(f"❌ {total - passed} tests failed - JOBS-002 needs fixes")
        sys.exit(1)


if __name__ == "__main__":
    main()
