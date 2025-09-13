#!/usr/bin/env python3
"""
M5.x Load Testing Script with Active Quotas
Tests quota enforcement under various load scenarios
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any, Dict

import aiohttp


@dataclass
class LoadTestResult:
    """Results from a load test run"""

    total_requests: int
    successful_requests: int
    quota_blocked_requests: int  # 429 responses
    error_requests: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    requests_per_second: float
    quota_violations_detected: int


class QuotaLoadTester:
    """Load tester specifically designed for quota system validation"""

    def __init__(self, base_url: str = "http://127.0.0.1:8082", token: str = "test123"):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    async def single_request(
        self, session: aiohttp.ClientSession, endpoint: str
    ) -> Dict[str, Any]:
        """Execute a single HTTP request and capture metrics"""
        start_time = time.time()

        try:
            async with session.get(
                f"{self.base_url}{endpoint}", headers=self.headers
            ) as response:
                end_time = time.time()
                content = await response.text()

                return {
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200,
                    "quota_blocked": response.status == 429,
                    "error": response.status >= 400 and response.status != 429,
                    "content_length": len(content),
                    "endpoint": endpoint,
                }
        except Exception as e:
            end_time = time.time()
            return {
                "status_code": 0,
                "response_time": end_time - start_time,
                "success": False,
                "quota_blocked": False,
                "error": True,
                "content_length": 0,
                "endpoint": endpoint,
                "exception": str(e),
            }

    async def burst_test(
        self, endpoint: str, concurrent_requests: int, total_requests: int
    ) -> LoadTestResult:
        """Execute a burst of concurrent requests to test quota enforcement"""
        print(
            f"🚀 Burst Test: {concurrent_requests} concurrent requests, {total_requests} total"
        )
        print(f"   Endpoint: {endpoint}")

        start_time = time.time()
        results = []

        connector = aiohttp.TCPConnector(limit=concurrent_requests)
        async with aiohttp.ClientSession(connector=connector) as session:

            # Create batches of concurrent requests
            batch_size = concurrent_requests
            for i in range(0, total_requests, batch_size):
                batch_requests = min(batch_size, total_requests - i)

                # Execute batch concurrently
                tasks = [
                    self.single_request(session, endpoint)
                    for _ in range(batch_requests)
                ]

                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)

                # Small delay between batches to avoid overwhelming
                if i + batch_size < total_requests:
                    await asyncio.sleep(0.1)

        end_time = time.time()
        total_time = end_time - start_time

        # Analyze results
        successful = sum(1 for r in results if r["success"])
        quota_blocked = sum(1 for r in results if r["quota_blocked"])
        errors = sum(1 for r in results if r["error"])
        response_times = [r["response_time"] for r in results if r["response_time"] > 0]

        return LoadTestResult(
            total_requests=len(results),
            successful_requests=successful,
            quota_blocked_requests=quota_blocked,
            error_requests=errors,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            requests_per_second=len(results) / total_time if total_time > 0 else 0,
            quota_violations_detected=quota_blocked,
        )

    async def sustained_load_test(
        self, endpoint: str, duration_seconds: int, requests_per_second: int
    ) -> LoadTestResult:
        """Execute sustained load over time to test quota accumulation"""
        print(
            f"⏱️  Sustained Load Test: {requests_per_second} req/s for {duration_seconds}s"
        )
        print(f"   Endpoint: {endpoint}")

        start_time = time.time()
        results = []

        connector = aiohttp.TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:

            end_test_time = start_time + duration_seconds
            interval = 1.0 / requests_per_second

            while time.time() < end_test_time:
                batch_start = time.time()

                # Send requests for this second
                tasks = [
                    self.single_request(session, endpoint)
                    for _ in range(requests_per_second)
                ]

                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)

                # Wait for next interval
                batch_duration = time.time() - batch_start
                sleep_time = max(0, 1.0 - batch_duration)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        end_time = time.time()
        total_time = end_time - start_time

        # Analyze results
        successful = sum(1 for r in results if r["success"])
        quota_blocked = sum(1 for r in results if r["quota_blocked"])
        errors = sum(1 for r in results if r["error"])
        response_times = [r["response_time"] for r in results if r["response_time"] > 0]

        return LoadTestResult(
            total_requests=len(results),
            successful_requests=successful,
            quota_blocked_requests=quota_blocked,
            error_requests=errors,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            requests_per_second=len(results) / total_time if total_time > 0 else 0,
            quota_violations_detected=quota_blocked,
        )

    async def get_current_quota_status(self) -> Dict[str, Any]:
        """Get current quota usage to understand test context"""
        try:
            connector = aiohttp.TCPConnector()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    f"{self.base_url}/quotas/my/usage", headers=self.headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        return {
                            "status": "quota_exceeded",
                            "message": "Already at quota limit",
                        }
                    else:
                        return {"status": "error", "code": response.status}
        except Exception as e:
            return {"status": "exception", "error": str(e)}

    async def reset_quotas_if_possible(self) -> bool:
        """Try to reset hourly quotas for testing"""
        try:
            connector = aiohttp.TCPConnector()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"{self.base_url}/quotas/admin/reset/hourly", headers=self.headers
                ) as response:
                    return response.status == 200
        except:
            return False

    def print_results(self, test_name: str, result: LoadTestResult):
        """Print formatted test results"""
        print(f"\n📊 {test_name} Results:")
        print(f"   Total Requests: {result.total_requests}")
        print(
            f"   ✅ Successful: {result.successful_requests} ({result.successful_requests/result.total_requests*100:.1f}%)"
        )
        print(
            f"   🚫 Quota Blocked (429): {result.quota_blocked_requests} ({result.quota_blocked_requests/result.total_requests*100:.1f}%)"
        )
        print(
            f"   ❌ Errors: {result.error_requests} ({result.error_requests/result.total_requests*100:.1f}%)"
        )
        print(f"   ⚡ Requests/sec: {result.requests_per_second:.2f}")
        print(
            f"   ⏱️  Response Times: avg={result.avg_response_time*1000:.1f}ms, max={result.max_response_time*1000:.1f}ms, min={result.min_response_time*1000:.1f}ms"
        )
        print(f"   🎯 Quota Violations: {result.quota_violations_detected}")


async def main():
    """Execute comprehensive quota load testing"""
    print("🔥 M5.x Load Testing with Active Quotas")
    print("=" * 50)

    tester = QuotaLoadTester()

    # 1. Check initial quota status
    print("\n1️⃣ Initial Quota Status Check")
    quota_status = await tester.get_current_quota_status()
    print(f"   Current status: {json.dumps(quota_status, indent=2)}")

    # 2. Try to reset quotas for clean testing
    print("\n2️⃣ Attempting Quota Reset")
    reset_success = await tester.reset_quotas_if_possible()
    print(f"   Reset successful: {reset_success}")

    if reset_success:
        # Wait a moment for reset to propagate
        await asyncio.sleep(2)
        quota_status = await tester.get_current_quota_status()
        print(f"   Post-reset status: {json.dumps(quota_status, indent=2)}")

    # 3. Burst Test - Low intensity to warm up
    print("\n3️⃣ Burst Test - Low Intensity")
    result1 = await tester.burst_test(
        "/health", concurrent_requests=5, total_requests=20
    )
    tester.print_results("Low Intensity Burst", result1)

    # 4. Burst Test - High intensity to trigger quotas
    print("\n4️⃣ Burst Test - High Intensity")
    result2 = await tester.burst_test(
        "/health", concurrent_requests=20, total_requests=100
    )
    tester.print_results("High Intensity Burst", result2)

    # 5. Test quota endpoint under load
    print("\n5️⃣ Quota Endpoint Load Test")
    result3 = await tester.burst_test(
        "/quotas/my/usage", concurrent_requests=10, total_requests=50
    )
    tester.print_results("Quota Endpoint Load", result3)

    # 6. Sustained load test
    print("\n6️⃣ Sustained Load Test")
    result4 = await tester.sustained_load_test(
        "/health", duration_seconds=30, requests_per_second=5
    )
    tester.print_results("Sustained Load", result4)

    # 7. Final quota status
    print("\n7️⃣ Final Quota Status")
    final_status = await tester.get_current_quota_status()
    print(f"   Final status: {json.dumps(final_status, indent=2)}")

    # 8. Summary
    print("\n🏁 Load Testing Summary")
    print("=" * 50)
    total_requests = (
        result1.total_requests
        + result2.total_requests
        + result3.total_requests
        + result4.total_requests
    )
    total_quota_blocks = (
        result1.quota_blocked_requests
        + result2.quota_blocked_requests
        + result3.quota_blocked_requests
        + result4.quota_blocked_requests
    )

    print(f"   📈 Total Requests Sent: {total_requests}")
    print(f"   🚫 Total Quota Blocks: {total_quota_blocks}")
    print(f"   📊 Quota Block Rate: {total_quota_blocks/total_requests*100:.1f}%")

    if total_quota_blocks > 0:
        print("   ✅ QUOTA ENFORCEMENT WORKING - Detected blocking under load")
    else:
        print("   ⚠️  NO QUOTA BLOCKS - May need to adjust limits or increase load")

    print("\n🎯 M5.x Load Testing Complete!")


if __name__ == "__main__":
    asyncio.run(main())
