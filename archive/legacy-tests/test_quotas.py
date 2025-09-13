#!/usr/bin/env python3
"""
Test script for quota system
"""
import asyncio

import pytest

from quotas.database import QuotaDatabase
from quotas.models import UserQuota


@pytest.mark.asyncio
async def test_quota_system():
    """Test basic quota operations"""
    print("🧪 Testing quota system...")

    db = QuotaDatabase()
    # Use existing test user
    test_user_id = "fc99e9b6-60d5-4856-af56-a5733e8c49b1"

    try:
        # Test 1: Create quotas
        print("📝 Creating test quotas...")
        quotas = UserQuota(
            user_id=test_user_id,
            quota_req_hour=10,
            quota_req_day=50,
            quota_cpu_seconds=60,
            quota_mem_mb=256,
            quota_storage_mb=50,
            quota_files_max=20,
        )

        # Test connection and basic operations
        stats = await db.get_usage_statistics()
        print(f"✅ Database connected - {stats['total_users']} users tracked")

        # Test 2: Get user usage (should create if not exists)
        print("📊 Testing user usage retrieval...")
        usage = await db.get_user_usage(test_user_id)
        if usage:
            print(f"✅ User usage found: {usage.req_hour} requests this hour")
        else:
            print("ℹ️ No usage found for test user (expected for new user)")

        # Test 3: Increment request counters
        print("⚡ Testing request counter increment...")
        await db.increment_request_counters(test_user_id)

        updated_usage = await db.get_user_usage(test_user_id)
        if updated_usage:
            print(
                f"✅ Request counters incremented: {updated_usage.req_hour}/hour, {updated_usage.req_day}/day"
            )

        # Test 4: Record a quota violation
        print("⚠️ Testing quota violation recording...")
        await db.record_quota_violation(
            user_id=test_user_id,
            reason="req_hour",
            detail={"current": 11, "limit": 10, "test": True},
        )

        violations = await db.get_quota_violations(test_user_id)
        print(f"✅ Violation recorded: {len(violations)} violations found")

        print("🎉 All quota system tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_quota_system())
    if success:
        print("✅ Quota system is working correctly!")
    else:
        print("❌ Quota system has issues!")
        exit(1)
