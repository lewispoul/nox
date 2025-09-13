#!/usr/bin/env python3
"""
Nox API v8.0.0 - Distributed Session Manager
Redis Cluster Integration for Multi-node Session Management

Handles distributed session storage, OAuth2 token distribution,
and cross-node session synchronization.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis
from redis.cluster import RedisCluster
from redis.exceptions import RedisClusterException, RedisError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributedSessionManager:
    """
    Manages user sessions across a Redis Cluster for multi-node Nox API deployment.

    Features:
    - Distributed session storage across Redis Cluster
    - OAuth2 token distribution and synchronization
    - Session failover and recovery
    - Cross-node session consistency
    """

    def __init__(
        self,
        redis_nodes: List[Dict[str, Any]] = None,
        password: str = None,
        session_ttl: int = 3600,  # 1 hour default
        token_ttl: int = 86400,
    ):  # 24 hours default
        """
        Initialize the distributed session manager.

        Args:
            redis_nodes: List of Redis cluster node configurations
            password: Redis authentication password
            session_ttl: Session time-to-live in seconds
            token_ttl: Token time-to-live in seconds
        """

        # Default Redis cluster nodes
        if redis_nodes is None:
            redis_nodes = [
                {"host": "redis-node1", "port": 6379},
                {"host": "redis-node2", "port": 6379},
                {"host": "redis-node3", "port": 6379},
            ]

        self.redis_nodes = redis_nodes
        self.password = password
        self.session_ttl = session_ttl
        self.token_ttl = token_ttl

        # Initialize Redis Cluster connection
        self.cluster = self._initialize_cluster()

        # Session key prefixes
        self.SESSION_PREFIX = "nox:session:"
        self.TOKEN_PREFIX = "nox:token:"
        self.USER_SESSION_PREFIX = "nox:user_sessions:"
        self.OAUTH_PREFIX = "nox:oauth:"

        logger.info(
            f"Distributed Session Manager initialized with {len(redis_nodes)} nodes"
        )

    def _initialize_cluster(self) -> RedisCluster:
        """Initialize Redis Cluster connection with retry logic."""

        startup_nodes = [
            redis.cluster.ClusterNode(node["host"], node["port"])
            for node in self.redis_nodes
        ]

        try:
            cluster = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                password=self.password,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test cluster connectivity
            cluster.ping()
            cluster_info = cluster.cluster_info()
            logger.info(
                f"Redis Cluster connected: {cluster_info.get('cluster_state', 'unknown')}"
            )

            return cluster

        except RedisClusterException as e:
            logger.error(f"Failed to connect to Redis Cluster: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis Cluster: {e}")
            raise

    def create_session(
        self,
        user_id: str,
        user_data: Dict[str, Any],
        oauth_provider: str = None,
        oauth_tokens: Dict[str, Any] = None,
    ) -> str:
        """
        Create a new distributed session.

        Args:
            user_id: Unique user identifier
            user_data: User profile and metadata
            oauth_provider: OAuth2 provider name (google, github, microsoft)
            oauth_tokens: OAuth2 token information

        Returns:
            session_id: Unique session identifier
        """

        session_id = str(uuid.uuid4())
        session_key = f"{self.SESSION_PREFIX}{session_id}"

        # Create session data
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "user_data": user_data,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "oauth_provider": oauth_provider,
            "node_id": self._get_node_id(),
            "expires_at": (
                datetime.utcnow() + timedelta(seconds=self.session_ttl)
            ).isoformat(),
        }

        try:
            # Store session data with TTL
            self.cluster.setex(session_key, self.session_ttl, json.dumps(session_data))

            # Store OAuth tokens if provided
            if oauth_tokens:
                self._store_oauth_tokens(session_id, oauth_tokens)

            # Track user sessions for multi-device support
            self._add_user_session(user_id, session_id)

            logger.info(f"Session created: {session_id} for user {user_id}")
            return session_id

        except RedisError as e:
            logger.error(f"Failed to create session: {e}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from the distributed store.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found/expired
        """

        session_key = f"{self.SESSION_PREFIX}{session_id}"

        try:
            session_data_json = self.cluster.get(session_key)

            if not session_data_json:
                logger.debug(f"Session not found: {session_id}")
                return None

            session_data = json.loads(session_data_json)

            # Check if session is expired
            if self._is_session_expired(session_data):
                logger.info(f"Session expired: {session_id}")
                self.delete_session(session_id)
                return None

            # Update last accessed timestamp
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            self.cluster.setex(session_key, self.session_ttl, json.dumps(session_data))

            return session_data

        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}")
            return None

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data in the distributed store.

        Args:
            session_id: Session identifier
            updates: Data to update in the session

        Returns:
            Success status
        """

        session_data = self.get_session(session_id)
        if not session_data:
            return False

        # Apply updates
        session_data.update(updates)
        session_data["last_accessed"] = datetime.utcnow().isoformat()

        session_key = f"{self.SESSION_PREFIX}{session_id}"

        try:
            self.cluster.setex(session_key, self.session_ttl, json.dumps(session_data))
            return True

        except RedisError as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session and associated data from the distributed store.

        Args:
            session_id: Session identifier

        Returns:
            Success status
        """

        try:
            # Get session data to clean up user tracking
            session_data = self.get_session(session_id)
            if session_data:
                user_id = session_data.get("user_id")
                if user_id:
                    self._remove_user_session(user_id, session_id)

            # Delete session and OAuth tokens
            session_key = f"{self.SESSION_PREFIX}{session_id}"
            oauth_key = f"{self.OAUTH_PREFIX}{session_id}"

            deleted_count = self.cluster.delete(session_key, oauth_key)

            logger.info(f"Session deleted: {session_id} (cleaned {deleted_count} keys)")
            return deleted_count > 0

        except RedisError as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def _store_oauth_tokens(
        self, session_id: str, oauth_tokens: Dict[str, Any]
    ) -> bool:
        """Store OAuth2 tokens in the distributed store."""

        oauth_key = f"{self.OAUTH_PREFIX}{session_id}"
        oauth_data = {
            "session_id": session_id,
            "tokens": oauth_tokens,
            "stored_at": datetime.utcnow().isoformat(),
            "expires_at": (
                datetime.utcnow() + timedelta(seconds=self.token_ttl)
            ).isoformat(),
        }

        try:
            self.cluster.setex(oauth_key, self.token_ttl, json.dumps(oauth_data))
            return True

        except RedisError as e:
            logger.error(f"Failed to store OAuth tokens for session {session_id}: {e}")
            return False

    def get_oauth_tokens(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth2 tokens for a session."""

        oauth_key = f"{self.OAUTH_PREFIX}{session_id}"

        try:
            oauth_data_json = self.cluster.get(oauth_key)
            if not oauth_data_json:
                return None

            oauth_data = json.loads(oauth_data_json)
            return oauth_data.get("tokens")

        except (RedisError, json.JSONDecodeError) as e:
            logger.error(
                f"Failed to retrieve OAuth tokens for session {session_id}: {e}"
            )
            return None

    def refresh_oauth_tokens(self, session_id: str, new_tokens: Dict[str, Any]) -> bool:
        """Update OAuth2 tokens in the distributed store."""

        oauth_key = f"{self.OAUTH_PREFIX}{session_id}"

        try:
            # Get existing OAuth data
            oauth_data_json = self.cluster.get(oauth_key)
            if not oauth_data_json:
                return self._store_oauth_tokens(session_id, new_tokens)

            oauth_data = json.loads(oauth_data_json)
            oauth_data["tokens"].update(new_tokens)
            oauth_data["updated_at"] = datetime.utcnow().isoformat()

            self.cluster.setex(oauth_key, self.token_ttl, json.dumps(oauth_data))
            return True

        except (RedisError, json.JSONDecodeError) as e:
            logger.error(
                f"Failed to refresh OAuth tokens for session {session_id}: {e}"
            )
            return False

    def _add_user_session(self, user_id: str, session_id: str) -> None:
        """Track active sessions for a user."""

        user_sessions_key = f"{self.USER_SESSION_PREFIX}{user_id}"
        try:
            self.cluster.sadd(user_sessions_key, session_id)
            self.cluster.expire(
                user_sessions_key, self.session_ttl * 2
            )  # Longer TTL for tracking
        except RedisError as e:
            logger.warning(f"Failed to track user session {user_id}: {e}")

    def _remove_user_session(self, user_id: str, session_id: str) -> None:
        """Remove session from user tracking."""

        user_sessions_key = f"{self.USER_SESSION_PREFIX}{user_id}"
        try:
            self.cluster.srem(user_sessions_key, session_id)
        except RedisError as e:
            logger.warning(f"Failed to remove user session tracking {user_id}: {e}")

    def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all active sessions for a user."""

        user_sessions_key = f"{self.USER_SESSION_PREFIX}{user_id}"
        try:
            return list(self.cluster.smembers(user_sessions_key))
        except RedisError as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []

    def revoke_user_sessions(self, user_id: str, exclude_session: str = None) -> int:
        """Revoke all sessions for a user, optionally excluding one session."""

        sessions = self.get_user_sessions(user_id)
        revoked_count = 0

        for session_id in sessions:
            if exclude_session and session_id == exclude_session:
                continue

            if self.delete_session(session_id):
                revoked_count += 1

        logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
        return revoked_count

    def _is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """Check if a session is expired."""

        try:
            expires_at = datetime.fromisoformat(session_data.get("expires_at", ""))
            return datetime.utcnow() > expires_at
        except (ValueError, TypeError):
            return True

    def _get_node_id(self) -> str:
        """Get current node identifier."""
        import os

        return os.environ.get("NODE_ID", "unknown")

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions across the cluster."""

        try:
            # Scan for all session keys
            session_keys = []
            for key in self.cluster.scan_iter(match=f"{self.SESSION_PREFIX}*"):
                session_keys.append(key)

            cleaned_count = 0
            for session_key in session_keys:
                try:
                    session_data_json = self.cluster.get(session_key)
                    if session_data_json:
                        session_data = json.loads(session_data_json)
                        if self._is_session_expired(session_data):
                            session_id = session_data.get("session_id")
                            if self.delete_session(session_id):
                                cleaned_count += 1
                except (json.JSONDecodeError, RedisError):
                    continue

            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count

        except RedisError as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get Redis Cluster status information."""

        try:
            cluster_info = self.cluster.cluster_info()
            cluster_nodes = self.cluster.cluster_nodes()

            return {
                "cluster_state": cluster_info.get("cluster_state"),
                "cluster_slots_assigned": cluster_info.get("cluster_slots_assigned"),
                "cluster_slots_ok": cluster_info.get("cluster_slots_ok"),
                "cluster_known_nodes": cluster_info.get("cluster_known_nodes"),
                "cluster_size": cluster_info.get("cluster_size"),
                "nodes": cluster_nodes,
                "session_count": len(
                    list(self.cluster.scan_iter(match=f"{self.SESSION_PREFIX}*"))
                ),
                "oauth_token_count": len(
                    list(self.cluster.scan_iter(match=f"{self.OAUTH_PREFIX}*"))
                ),
            }

        except RedisError as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {"error": str(e)}


# Example usage and testing
if __name__ == "__main__":
    # Initialize distributed session manager
    session_manager = DistributedSessionManager()

    # Create a test session
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "avatar_url": "https://example.com/avatar.jpg",
    }

    oauth_tokens = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
    }

    # Test session operations
    session_id = session_manager.create_session(
        user_id="user123",
        user_data=user_data,
        oauth_provider="google",
        oauth_tokens=oauth_tokens,
    )

    print(f"Created session: {session_id}")

    # Retrieve session
    retrieved_session = session_manager.get_session(session_id)
    print(f"Retrieved session: {retrieved_session}")

    # Get cluster information
    cluster_info = session_manager.get_cluster_info()
    print(f"Cluster info: {cluster_info}")
