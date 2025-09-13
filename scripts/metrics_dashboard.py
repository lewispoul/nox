#!/usr/bin/env python3
"""
NOX Metrics Dashboard (CLI)
Displays key performance and health metrics from Redis and Prometheus endpoints.
"""
import os

import redis
import requests
from tabulate import tabulate

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASS = os.getenv("REDIS_PASSWORD", None)
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

METRIC_KEYS = [
    "metrics:requests",
    "metrics:latency",
    "metrics:errors",
    "metrics:rate_limit",
]


def get_redis_connection():
    return redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True
    )


def fetch_redis_metrics(r):
    data = []
    for key in METRIC_KEYS:
        value = r.get(key)
        data.append([key, value or "N/A"])
    return data


def fetch_prometheus_metric(metric):
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": metric}, timeout=5
        )
        result = resp.json()
        if result["status"] == "success" and result["data"]["result"]:
            return result["data"]["result"][0]["value"][1]
    except Exception:
        pass
    return "N/A"


def main():
    print("=== NOX Metrics Dashboard ===")
    r = get_redis_connection()
    redis_data = fetch_redis_metrics(r)
    print(tabulate(redis_data, headers=["Metric", "Value"], tablefmt="github"))
    print("\nPrometheus Metrics:")
    for metric in ["up", "http_requests_total", "api_latency_seconds"]:
        value = fetch_prometheus_metric(metric)
        print(f"{metric}: {value}")


if __name__ == "__main__":
    main()
