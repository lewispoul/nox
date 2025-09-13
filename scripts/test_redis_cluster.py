#!/usr/bin/env python3
"""
Test Redis Cluster functionality for Nox API v8.0.0
"""

import sys
import time

try:
    from redis.cluster import RedisCluster
except ImportError:
    print("❌ Redis Python library not installed. Run: pip install redis")
    sys.exit(1)


def test_redis_cluster():
    """Test Redis Cluster connectivity and operations."""

    print("🔍 Testing Redis Cluster for Nox API v8.0.0")
    print("=" * 50)

    # Redis Cluster connection configuration
    startup_nodes = [
        {"host": "localhost", "port": 7001},
        {"host": "localhost", "port": 7002},
        {"host": "localhost", "port": 7003},
    ]

    try:
        # Initialize cluster connection
        print("📡 Connecting to Redis Cluster...")
        cluster = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            skip_full_coverage_check=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        # Test basic connectivity
        cluster.ping()
        print("✅ Redis Cluster connection successful")

        # Test cluster info
        cluster_info = cluster.cluster_info()
        print(f"📊 Cluster State: {cluster_info.get('cluster_state', 'unknown')}")
        print(f"📋 Known Nodes: {cluster_info.get('cluster_known_nodes', 0)}")
        print(
            f"🎯 Slots Assigned: {cluster_info.get('cluster_slots_assigned', 0)}/16384"
        )

        # Test basic operations
        print("\n🧪 Testing basic operations...")

        # Set/Get test
        test_key = "nox:test:session:123"
        test_value = "test-session-data"
        cluster.setex(test_key, 60, test_value)

        retrieved_value = cluster.get(test_key)
        if retrieved_value == test_value:
            print("✅ Set/Get operation successful")
        else:
            print(
                f"❌ Set/Get operation failed: expected '{test_value}', got '{retrieved_value}'"
            )

        # Hash operations test
        hash_key = "nox:user:456"
        hash_data = {
            "email": "test@example.com",
            "name": "Test User",
            "last_login": str(int(time.time())),
        }

        cluster.hset(hash_key, mapping=hash_data)
        retrieved_hash = cluster.hgetall(hash_key)

        if all(retrieved_hash.get(k) == v for k, v in hash_data.items()):
            print("✅ Hash operations successful")
        else:
            print("❌ Hash operations failed")

        # Distributed keys test
        print("\n🌐 Testing key distribution across nodes...")
        test_keys = [f"nox:distributed:test:{i}" for i in range(10)]

        for key in test_keys:
            cluster.set(key, f"value-{key}")

        # Check if keys are distributed
        nodes_used = set()
        for key in test_keys:
            node_info = cluster.cluster_keyslot(key)
            nodes_used.add(node_info)

        print(f"📈 Keys distributed across {len(nodes_used)} different slots")

        # Cleanup test keys
        cluster.delete(*test_keys, test_key, hash_key)
        print("🧹 Test cleanup completed")

        print("\n🎉 Redis Cluster test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Redis Cluster test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_redis_cluster()
    sys.exit(0 if success else 1)
