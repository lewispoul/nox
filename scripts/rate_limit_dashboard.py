#!/usr/bin/env python3
"""
NOX Rate Limiting Dashboard (CLI)
Displays current rate limit status for all API endpoints using Redis metrics.
"""
import os

import redis
from tabulate import tabulate

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASS = os.getenv("REDIS_PASSWORD", None)

RATE_LIMIT_KEY_PATTERN = "rate_limit:*"


def get_redis_connection():
    return redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True
    )


def fetch_rate_limits(r):
    keys = r.keys(RATE_LIMIT_KEY_PATTERN)
    data = []
    for key in keys:
        endpoint = key.split(":", 1)[-1]
        limit = r.get(key)
        data.append([endpoint, limit])
    return data


def main():
    r = get_redis_connection()
    data = fetch_rate_limits(r)
    if data:
        print(tabulate(data, headers=["Endpoint", "Current Usage"], tablefmt="github"))
    else:
        print("No rate limit data found.")


if __name__ == "__main__":
    main()
