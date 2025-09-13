#!/usr/bin/env python3
"""
Test to debug quota middleware enforcement
"""
import asyncio
import os

os.environ["NOX_QUOTAS_ENABLED"] = "1"

import pytest

from quotas.database import QuotaDatabase
from quotas.middleware import QuotaEnforcementMiddleware


@pytest.mark.asyncio
async def test_quota_check():
    print("🔍 Testing Quota Enforcement Middleware")

    # Initialize database
    db = QuotaDatabase()
    await db.init_db()

    user_id = "81dfa919-4604-4fdf-8038-4b862ee2a469"

    print(f"\n📊 Testing user: {user_id}")

    # Get current quotas
    user = await db.get_user(user_id)
    if user:
        print(f"✅ User found: {user['oauth_id']}")

    # Get current usage
    usage = await db.get_user_usage(user_id)
    if usage:
        print(f"📈 Current usage: {usage.req_hour} requests/hour")

    # Get quota limits
    quotas = await db.get_user_quotas(user_id)
    if quotas:
        print(f"🎯 Quota limit: {quotas.quota_req_hour} requests/hour")

    # Check if quota should be exceeded
    is_exceeded = usage.req_hour >= quotas.quota_req_hour if usage and quotas else False
    print(f"🚫 Quota exceeded: {is_exceeded}")
    print(
        f"   {usage.req_hour if usage else 0} >= {quotas.quota_req_hour if quotas else 0}"
    )

    # Test the middleware check logic directly
    middleware = QuotaEnforcementMiddleware(None, db)
    quota_check = await middleware._check_hourly_requests(user_id)

    print("\n🔬 Middleware Check Result:")
    print(f"   Allowed: {quota_check.allowed}")
    print(f"   Current: {quota_check.current_usage}")
    print(f"   Limit: {quota_check.limit}")
    print(f"   Percentage: {quota_check.percentage:.2%}")
    print(f"   Message: {quota_check.message}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(test_quota_check())
