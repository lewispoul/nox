#!/usr/bin/env python3
"""
Nox API v8.0.0 - Multi-node Database Manager
PostgreSQL High Availability Cluster Integration

Manages database connections across primary-replica PostgreSQL cluster
with automatic failover and load balancing for read/write operations.
"""

import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """Database node roles"""

    PRIMARY = "primary"
    REPLICA = "replica"
    UNKNOWN = "unknown"


@dataclass
class DatabaseNode:
    """Database node configuration"""

    host: str
    port: int
    database: str
    username: str
    password: str
    role: NodeRole = NodeRole.UNKNOWN
    max_connections: int = 20
    min_connections: int = 5


class MultiNodeDatabaseManager:
    """
    Manages PostgreSQL High Availability cluster with automatic failover.

    Features:
    - Primary-replica cluster management
    - Automatic failover detection and handling
    - Read/write query routing
    - Connection pooling per node
    - Health monitoring and recovery
    """

    def __init__(self, nodes: List[DatabaseNode] = None):
        """
        Initialize multi-node database manager.

        Args:
            nodes: List of database node configurations
        """

        # Default PostgreSQL HA cluster configuration
        if nodes is None:
            nodes = self._load_default_nodes()

        self.nodes = nodes
        self.connection_pools = {}
        self.node_health = {}
        self.last_health_check = {}
        self.health_check_interval = 30  # seconds

        # Initialize connection pools and health monitoring
        self._initialize_pools()
        self._discover_node_roles()

        logger.info(f"Multi-node Database Manager initialized with {len(nodes)} nodes")

    def _load_default_nodes(self) -> List[DatabaseNode]:
        """Load default PostgreSQL HA cluster configuration from environment."""

        # Primary database node
        primary_node = DatabaseNode(
            host=os.getenv("PG_PRIMARY_HOST", "postgres-primary"),
            port=int(os.getenv("PG_PRIMARY_PORT", "5432")),
            database=os.getenv("PG_DATABASE", "nox_api"),
            username=os.getenv("PG_USERNAME", "nox_user"),
            password=os.getenv("PG_PASSWORD", "secure_password"),
            role=NodeRole.PRIMARY,
        )

        # Replica database nodes
        replica_nodes = []
        replica_count = int(os.getenv("PG_REPLICA_COUNT", "2"))

        for i in range(1, replica_count + 1):
            replica_node = DatabaseNode(
                host=os.getenv(f"PG_REPLICA{i}_HOST", f"postgres-replica{i}"),
                port=int(os.getenv(f"PG_REPLICA{i}_PORT", "5432")),
                database=os.getenv("PG_DATABASE", "nox_api"),
                username=os.getenv("PG_USERNAME", "nox_user"),
                password=os.getenv("PG_PASSWORD", "secure_password"),
                role=NodeRole.REPLICA,
            )
            replica_nodes.append(replica_node)

        return [primary_node] + replica_nodes

    def _initialize_pools(self) -> None:
        """Initialize connection pools for each database node."""

        for node in self.nodes:
            try:
                # Create connection pool for the node
                connection_string = (
                    f"host={node.host} "
                    f"port={node.port} "
                    f"dbname={node.database} "
                    f"user={node.username} "
                    f"password={node.password} "
                    f"connect_timeout=5 "
                    f"application_name=nox_api_v8_multinode"
                )

                pool_instance = psycopg2.pool.ThreadedConnectionPool(
                    minconn=node.min_connections,
                    maxconn=node.max_connections,
                    dsn=connection_string,
                    cursor_factory=RealDictCursor,
                )

                self.connection_pools[node.host] = pool_instance
                self.node_health[node.host] = True
                self.last_health_check[node.host] = 0

                logger.info(
                    f"Connection pool created for {node.host}:{node.port} ({node.role.value})"
                )

            except Exception as e:
                logger.error(f"Failed to create connection pool for {node.host}: {e}")
                self.node_health[node.host] = False

    def _discover_node_roles(self) -> None:
        """Discover actual node roles by querying PostgreSQL replication status."""

        for node in self.nodes:
            if not self.node_health.get(node.host, False):
                continue

            try:
                with self._get_connection(node.host) as conn:
                    with conn.cursor() as cursor:
                        # Check if this node is in recovery (replica)
                        cursor.execute("SELECT pg_is_in_recovery();")
                        is_in_recovery = cursor.fetchone()[0]

                        if is_in_recovery:
                            node.role = NodeRole.REPLICA
                            logger.info(f"Node {node.host} identified as REPLICA")
                        else:
                            node.role = NodeRole.PRIMARY
                            logger.info(f"Node {node.host} identified as PRIMARY")

            except Exception as e:
                logger.error(f"Failed to discover role for {node.host}: {e}")
                node.role = NodeRole.UNKNOWN

    @contextmanager
    def _get_connection(self, node_host: str):
        """Get a database connection from the pool for a specific node."""

        pool_instance = self.connection_pools.get(node_host)
        if not pool_instance:
            raise Exception(f"No connection pool available for {node_host}")

        connection = None
        try:
            connection = pool_instance.getconn()
            yield connection
        finally:
            if connection:
                pool_instance.putconn(connection)

    def _check_node_health(self, node_host: str) -> bool:
        """Check health status of a database node."""

        current_time = time.time()
        last_check = self.last_health_check.get(node_host, 0)

        # Skip if recently checked
        if current_time - last_check < self.health_check_interval:
            return self.node_health.get(node_host, False)

        try:
            with self._get_connection(node_host) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    cursor.fetchone()

            self.node_health[node_host] = True
            self.last_health_check[node_host] = current_time
            return True

        except Exception as e:
            logger.warning(f"Health check failed for {node_host}: {e}")
            self.node_health[node_host] = False
            self.last_health_check[node_host] = current_time
            return False

    def _get_healthy_node(self, role: NodeRole = None) -> Optional[DatabaseNode]:
        """Get a healthy database node, optionally filtered by role."""

        candidates = []

        for node in self.nodes:
            # Filter by role if specified
            if role and node.role != role:
                continue

            # Check node health
            if self._check_node_health(node.host):
                candidates.append(node)

        # Return the first healthy node
        return candidates[0] if candidates else None

    def _get_primary_node(self) -> Optional[DatabaseNode]:
        """Get the healthy primary database node."""
        return self._get_healthy_node(NodeRole.PRIMARY)

    def _get_replica_node(self) -> Optional[DatabaseNode]:
        """Get a healthy replica database node."""
        return self._get_healthy_node(NodeRole.REPLICA)

    @contextmanager
    def get_write_connection(self):
        """
        Get a database connection for write operations (primary node).

        Yields:
            Database connection to primary node

        Raises:
            Exception: If no healthy primary node is available
        """

        primary_node = self._get_primary_node()
        if not primary_node:
            # Try to find any healthy node as fallback
            fallback_node = self._get_healthy_node()
            if not fallback_node:
                raise Exception(
                    "No healthy database nodes available for write operations"
                )

            logger.warning(
                f"Using fallback node {fallback_node.host} for write operations"
            )
            primary_node = fallback_node

        with self._get_connection(primary_node.host) as conn:
            yield conn

    @contextmanager
    def get_read_connection(self, prefer_replica: bool = True):
        """
        Get a database connection for read operations.

        Args:
            prefer_replica: Whether to prefer replica nodes for read operations

        Yields:
            Database connection for read operations
        """

        target_node = None

        if prefer_replica:
            # Try to get a replica node first
            target_node = self._get_replica_node()

        if not target_node:
            # Fallback to primary or any healthy node
            target_node = self._get_primary_node() or self._get_healthy_node()

        if not target_node:
            raise Exception("No healthy database nodes available for read operations")

        with self._get_connection(target_node.host) as conn:
            yield conn

    def execute_write_query(
        self, query: str, params: Tuple = None, fetch_result: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a write query on the primary database node.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_result: Whether to fetch and return query results

        Returns:
            Query results if fetch_result is True, otherwise None
        """

        try:
            with self.get_write_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)

                    if fetch_result:
                        return cursor.fetchall()
                    else:
                        conn.commit()
                        return None

        except Exception as e:
            logger.error(f"Write query failed: {e}")
            raise

    def execute_read_query(
        self, query: str, params: Tuple = None, prefer_replica: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query, optionally preferring replica nodes.

        Args:
            query: SQL query string
            params: Query parameters
            prefer_replica: Whether to prefer replica nodes

        Returns:
            Query results
        """

        try:
            with self.get_read_connection(prefer_replica=prefer_replica) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchall()

        except Exception as e:
            logger.error(f"Read query failed: {e}")
            raise

    def execute_transaction(self, queries: List[Tuple[str, Tuple]]) -> bool:
        """
        Execute multiple queries in a single transaction on the primary node.

        Args:
            queries: List of (query, params) tuples

        Returns:
            Success status
        """

        try:
            with self.get_write_connection() as conn:
                with conn.cursor() as cursor:
                    for query, params in queries:
                        cursor.execute(query, params)

                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status information."""

        cluster_status = {
            "nodes": [],
            "healthy_nodes": 0,
            "primary_available": False,
            "replicas_available": 0,
            "cluster_health": "unknown",
        }

        for node in self.nodes:
            node_status = {
                "host": node.host,
                "port": node.port,
                "role": node.role.value,
                "healthy": self._check_node_health(node.host),
                "last_check": self.last_health_check.get(node.host, 0),
            }

            if node_status["healthy"]:
                cluster_status["healthy_nodes"] += 1

                if node.role == NodeRole.PRIMARY:
                    cluster_status["primary_available"] = True
                elif node.role == NodeRole.REPLICA:
                    cluster_status["replicas_available"] += 1

            # Add connection pool stats
            pool_instance = self.connection_pools.get(node.host)
            if pool_instance:
                node_status["pool_stats"] = {
                    "total_connections": pool_instance.maxconn,
                    "available_connections": len(pool_instance._pool),
                    "used_connections": pool_instance.maxconn
                    - len(pool_instance._pool),
                }

            cluster_status["nodes"].append(node_status)

        # Determine overall cluster health
        if cluster_status["primary_available"] and cluster_status["healthy_nodes"] > 0:
            cluster_status["cluster_health"] = "healthy"
        elif cluster_status["healthy_nodes"] > 0:
            cluster_status["cluster_health"] = "degraded"
        else:
            cluster_status["cluster_health"] = "critical"

        return cluster_status

    def cleanup_connections(self) -> None:
        """Clean up all connection pools."""

        for host, pool_instance in self.connection_pools.items():
            try:
                pool_instance.closeall()
                logger.info(f"Connection pool closed for {host}")
            except Exception as e:
                logger.error(f"Failed to close connection pool for {host}: {e}")

        self.connection_pools.clear()


# Example usage and testing
if __name__ == "__main__":
    # Initialize multi-node database manager
    db_manager = MultiNodeDatabaseManager()

    # Test cluster status
    cluster_status = db_manager.get_cluster_status()
    print(f"Cluster Status: {cluster_status}")

    # Test read query
    try:
        users = db_manager.execute_read_query(
            "SELECT id, email, created_at FROM users LIMIT 5;"
        )
        print(f"Sample users: {users}")
    except Exception as e:
        print(f"Read query failed: {e}")

    # Test write query
    try:
        db_manager.execute_write_query(
            "INSERT INTO health_checks (timestamp, status) VALUES (NOW(), 'healthy');"
        )
        print("Health check record inserted successfully")
    except Exception as e:
        print(f"Write query failed: {e}")

    # Clean up
    db_manager.cleanup_connections()
