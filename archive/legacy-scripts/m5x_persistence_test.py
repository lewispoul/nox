#!/usr/bin/env python3
"""
M5.x Database Persistence Validation
Test that quota/usage data survives API restarts and system reboots
"""

import subprocess
import sys
import time
from typing import Any, Dict

import requests


class PersistenceValidator:
    """Validate database persistence across API restarts"""

    def __init__(self, base_url: str = "http://127.0.0.1:8082", token: str = "test123"):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_current_state(self) -> Dict[str, Any]:
        """Capture current quota and usage state"""
        try:
            response = requests.get(
                f"{self.base_url}/quotas/my/usage", headers=self.headers, timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "quotas": data["quotas"],
                    "usage": data["usage"],
                    "timestamp": time.time(),
                }
            else:
                return {
                    "status": "error",
                    "code": response.status_code,
                    "response": response.text,
                }
        except Exception as e:
            return {"status": "exception", "error": str(e)}

    def generate_usage_activity(self) -> Dict[str, Any]:
        """Generate some API activity to create usage data"""
        print("📈 Generating usage activity...")

        activity_summary = {
            "total_requests": 0,
            "successful_requests": 0,
            "endpoints_tested": [],
        }

        # Test different endpoints to generate varied usage
        endpoints = [
            "/health",
            "/quotas/my/quotas",
            "/quotas/my/usage",
            "/quotas/my/violations",
        ]

        for endpoint in endpoints:
            print(f"   Testing {endpoint}...")
            try:
                response = requests.get(
                    f"{self.base_url}{endpoint}", headers=self.headers, timeout=5
                )
                activity_summary["total_requests"] += 1

                if response.status_code == 200:
                    activity_summary["successful_requests"] += 1
                    activity_summary["endpoints_tested"].append(endpoint)
                    print(f"   ✅ {endpoint}: {response.status_code}")
                else:
                    print(f"   ❌ {endpoint}: {response.status_code}")

                time.sleep(0.5)  # Small delay between requests
            except Exception as e:
                print(f"   ⚠️  {endpoint}: Exception - {e}")

        return activity_summary

    def restart_api_server(self) -> bool:
        """Restart the API server process"""
        print("🔄 Restarting API server...")

        try:
            # Find and kill the existing API process
            kill_result = subprocess.run(
                ["pkill", "-f", "nox_api_v5_fixed.py"], capture_output=True, text=True
            )
            print(f"   Kill process: exit code {kill_result.returncode}")

            # Wait a moment for cleanup
            time.sleep(2)

            # Start new API process
            start_result = subprocess.run(
                [
                    "bash",
                    "-c",
                    "cd /home/lppoulin/nox-api-src && NOX_QUOTAS_ENABLED=1 NOX_API_TOKEN=test123 NOX_PORT=8082 python3 nox_api_v5_fixed.py > /tmp/api_restart.log 2>&1 &",
                ],
                capture_output=True,
                text=True,
            )
            print(f"   Start process: exit code {start_result.returncode}")

            # Wait for API to start
            print("   Waiting for API to start...")
            for i in range(10):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"   ✅ API started successfully (attempt {i+1})")
                        return True
                except:
                    time.sleep(2)

            print("   ❌ API failed to start within timeout")
            return False

        except Exception as e:
            print(f"   ⚠️  Exception during restart: {e}")
            return False

    def compare_states(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Compare quota/usage states before and after restart"""

        if before["status"] != "success" or after["status"] != "success":
            return {
                "comparison": "failed",
                "reason": "Could not retrieve state data",
                "before_status": before["status"],
                "after_status": after["status"],
            }

        # Compare quotas (should be identical)
        quota_differences = {}
        for key in before["quotas"]:
            if key in after["quotas"]:
                if before["quotas"][key] != after["quotas"][key]:
                    quota_differences[key] = {
                        "before": before["quotas"][key],
                        "after": after["quotas"][key],
                    }
            else:
                quota_differences[key] = {
                    "before": before["quotas"][key],
                    "after": "missing",
                }

        # Compare usage (may have increased)
        usage_differences = {}
        for key in before["usage"]:
            if key != "updated_at" and key in after["usage"]:
                if before["usage"][key] != after["usage"][key]:
                    usage_differences[key] = {
                        "before": before["usage"][key],
                        "after": after["usage"][key],
                    }

        return {
            "comparison": "success",
            "quota_differences": quota_differences,
            "usage_differences": usage_differences,
            "quotas_preserved": len(quota_differences) == 0,
            "usage_preserved_or_increased": all(
                after["usage"][key] >= before["usage"][key]
                for key in before["usage"]
                if key != "updated_at"
                and key != "user_id"
                and isinstance(before["usage"][key], (int, float))
            ),
        }

    def run_persistence_test(self) -> Dict[str, Any]:
        """Execute complete persistence validation test"""

        print("🔍 M5.x Database Persistence Validation")
        print("=" * 50)

        # Step 1: Capture initial state
        print("\n1️⃣ Capturing initial state...")
        initial_state = self.get_current_state()

        if initial_state["status"] != "success":
            return {
                "test_result": "failed",
                "step": 1,
                "reason": "Could not get initial state",
                "data": initial_state,
            }

        print("   ✅ Initial state captured")
        print(
            f"   📊 Usage: {initial_state['usage']['req_hour']} req/hour, {initial_state['usage']['req_day']} req/day"
        )
        print(f"   🎯 Quotas: {initial_state['quotas']['quota_req_hour']} req/hour limit")

        # Step 2: Generate some usage activity
        print("\n2️⃣ Generating usage activity...")
        activity = self.generate_usage_activity()
        print(
            f"   ✅ Activity generated: {activity['successful_requests']}/{activity['total_requests']} successful"
        )

        # Step 3: Capture state after activity
        print("\n3️⃣ Capturing post-activity state...")
        time.sleep(1)  # Allow time for usage to be recorded
        post_activity_state = self.get_current_state()

        if post_activity_state["status"] != "success":
            return {
                "test_result": "failed",
                "step": 3,
                "reason": "Could not get post-activity state",
            }

        print("   ✅ Post-activity state captured")
        print(
            f"   📊 Usage: {post_activity_state['usage']['req_hour']} req/hour, {post_activity_state['usage']['req_day']} req/day"
        )

        # Step 4: Restart API server
        print("\n4️⃣ Restarting API server...")
        restart_success = self.restart_api_server()

        if not restart_success:
            return {
                "test_result": "failed",
                "step": 4,
                "reason": "Could not restart API server",
            }

        # Step 5: Capture state after restart
        print("\n5️⃣ Capturing post-restart state...")
        time.sleep(2)  # Allow API to fully initialize
        post_restart_state = self.get_current_state()

        if post_restart_state["status"] != "success":
            return {
                "test_result": "failed",
                "step": 5,
                "reason": "Could not get post-restart state",
                "data": post_restart_state,
            }

        print("   ✅ Post-restart state captured")
        print(
            f"   📊 Usage: {post_restart_state['usage']['req_hour']} req/hour, {post_restart_state['usage']['req_day']} req/day"
        )

        # Step 6: Compare states
        print("\n6️⃣ Comparing states...")
        comparison = self.compare_states(post_activity_state, post_restart_state)

        if comparison["comparison"] == "failed":
            return {
                "test_result": "failed",
                "step": 6,
                "reason": "State comparison failed",
                "data": comparison,
            }

        # Step 7: Results analysis
        print("\n📊 Persistence Test Results:")
        print(f"   🎯 Quotas preserved: {'✅ Yes' if comparison['quotas_preserved'] else '❌ No'}")
        print(
            f"   📈 Usage preserved: {'✅ Yes' if comparison['usage_preserved_or_increased'] else '❌ No'}"
        )

        if comparison["quota_differences"]:
            print("   ⚠️  Quota differences found:")
            for key, diff in comparison["quota_differences"].items():
                print(f"      {key}: {diff['before']} → {diff['after']}")

        if comparison["usage_differences"]:
            print("   📈 Usage differences found:")
            for key, diff in comparison["usage_differences"].items():
                print(f"      {key}: {diff['before']} → {diff['after']}")

        # Overall test result
        test_passed = comparison["quotas_preserved"] and comparison["usage_preserved_or_increased"]

        return {
            "test_result": "passed" if test_passed else "failed",
            "quotas_persistent": comparison["quotas_preserved"],
            "usage_persistent": comparison["usage_preserved_or_increased"],
            "initial_state": initial_state,
            "post_activity_state": post_activity_state,
            "post_restart_state": post_restart_state,
            "comparison": comparison,
            "activity_summary": activity,
        }


def main():
    """Execute persistence validation"""
    validator = PersistenceValidator()
    result = validator.run_persistence_test()

    print("\n🏁 Final Result:")
    if result["test_result"] == "passed":
        print("   ✅ PERSISTENCE TEST PASSED")
        print("   📋 Database successfully preserves quota and usage data across API restarts")
    else:
        print("   ❌ PERSISTENCE TEST FAILED")
        print(
            f"   📋 Issue at step {result.get('step', 'unknown')}: {result.get('reason', 'unknown')}"
        )

    return result


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["test_result"] == "passed" else 1)
