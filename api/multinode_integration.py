#!/usr/bin/env python3
"""
Nox API v8.0.0 - Multi-node Integration Layer
Integrates distributed session management and database clustering

Provides unified interface for multi-node operations including
session management, database operations, and cluster coordination.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from database_manager_multinode import MultiNodeDatabaseManager
from session_manager_distributed import DistributedSessionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ClusterHealth:
    """Overall cluster health status"""

    redis_healthy: bool
    database_healthy: bool
    overall_status: str
    details: Dict[str, Any]


class MultiNodeNoxAPI:
    """
    Multi-node Nox API integration layer for distributed operations.

    Combines distributed session management with database clustering
    to provide a unified interface for multi-node API operations.
    """

    def __init__(self):
        """Initialize multi-node components."""

        # Initialize distributed session manager
        self.session_manager = DistributedSessionManager(
            session_ttl=int(os.getenv("SESSION_TTL", "3600")),
            token_ttl=int(os.getenv("TOKEN_TTL", "86400")),
        )

        # Initialize multi-node database manager
        self.db_manager = MultiNodeDatabaseManager()

        # Node identification
        self.node_id = os.getenv("NODE_ID", f"node-{os.getpid()}")

        logger.info(f"Multi-node Nox API initialized for node: {self.node_id}")

    async def authenticate_user(
        self,
        oauth_provider: str,
        oauth_tokens: Dict[str, Any],
        user_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Authenticate user across distributed system.

        Creates or updates user in database cluster and establishes
        distributed session across Redis cluster.
        """

        try:
            # Extract user information
            user_email = user_data.get("email")
            user_id = user_data.get("id") or user_email

            if not user_email or not user_id:
                raise ValueError("Missing required user information")

            # Store/update user in database cluster
            user_record = await self._create_or_update_user(user_data)

            # Create distributed session
            session_id = self.session_manager.create_session(
                user_id=str(user_record["id"]),
                user_data=user_data,
                oauth_provider=oauth_provider,
                oauth_tokens=oauth_tokens,
            )

            # Log authentication event
            await self._log_auth_event(user_record["id"], oauth_provider, "success")

            return {
                "session_id": session_id,
                "user": user_record,
                "node_id": self.node_id,
                "cluster_status": "distributed",
            }

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            # Log failed authentication
            if user_data.get("email"):
                await self._log_auth_event(
                    user_data["email"], oauth_provider, "failure", str(e)
                )
            raise

    async def _create_or_update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user in database cluster."""

        email = user_data["email"]
        name = user_data.get("name", "")
        avatar_url = user_data.get("avatar_url", "")

        # Check if user exists (read operation - can use replica)
        existing_users = self.db_manager.execute_read_query(
            "SELECT * FROM users WHERE email = %s LIMIT 1;",
            (email,),
            prefer_replica=True,
        )

        if existing_users:
            # Update existing user (write operation - uses primary)
            user_id = existing_users[0]["id"]
            self.db_manager.execute_write_query(
                """UPDATE users SET 
                   name = %s, 
                   avatar_url = %s, 
                   last_login = NOW() 
                   WHERE id = %s;""",
                (name, avatar_url, user_id),
            )

            # Fetch updated user record
            updated_users = self.db_manager.execute_read_query(
                "SELECT * FROM users WHERE id = %s;", (user_id,)
            )
            return updated_users[0]

        else:
            # Create new user (write operation - uses primary)
            result = self.db_manager.execute_write_query(
                """INSERT INTO users (email, name, avatar_url, created_at, last_login) 
                   VALUES (%s, %s, %s, NOW(), NOW()) 
                   RETURNING *;""",
                (email, name, avatar_url),
                fetch_result=True,
            )
            return result[0]

    async def _log_auth_event(
        self,
        user_identifier: str,
        provider: str,
        status: str,
        error_message: str = None,
    ):
        """Log authentication events to database cluster."""

        try:
            self.db_manager.execute_write_query(
                """INSERT INTO auth_logs 
                   (user_identifier, oauth_provider, status, error_message, node_id, timestamp) 
                   VALUES (%s, %s, %s, %s, %s, NOW());""",
                (user_identifier, provider, status, error_message, self.node_id),
            )
        except Exception as e:
            logger.warning(f"Failed to log auth event: {e}")

    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user session from distributed store."""

        try:
            session_data = self.session_manager.get_session(session_id)
            if not session_data:
                return None

            # Enrich session with current user data from database
            user_id = session_data.get("user_id")
            if user_id:
                current_users = self.db_manager.execute_read_query(
                    "SELECT * FROM users WHERE id = %s;",
                    (user_id,),
                    prefer_replica=True,
                )

                if current_users:
                    session_data["current_user_data"] = current_users[0]

            return session_data

        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}")
            return None

    async def update_user_session(
        self, session_id: str, updates: Dict[str, Any]
    ) -> bool:
        """Update session data in distributed store."""

        return self.session_manager.update_session(session_id, updates)

    async def revoke_user_session(self, session_id: str) -> bool:
        """Revoke a specific user session."""

        try:
            # Get session info for logging
            session_data = self.session_manager.get_session(session_id)

            # Delete the session
            success = self.session_manager.delete_session(session_id)

            # Log session revocation
            if success and session_data:
                user_id = session_data.get("user_id")
                await self._log_session_event(user_id, session_id, "revoked")

            return success

        except Exception as e:
            logger.error(f"Failed to revoke session {session_id}: {e}")
            return False

    async def revoke_all_user_sessions(
        self, user_id: str, exclude_session: str = None
    ) -> int:
        """Revoke all sessions for a user except optionally one."""

        try:
            revoked_count = self.session_manager.revoke_user_sessions(
                user_id, exclude_session
            )

            # Log bulk session revocation
            await self._log_session_event(
                user_id, f"{revoked_count} sessions", "bulk_revoked"
            )

            return revoked_count

        except Exception as e:
            logger.error(f"Failed to revoke user sessions for {user_id}: {e}")
            return 0

    async def _log_session_event(
        self, user_id: str, session_info: str, event_type: str
    ):
        """Log session events to database cluster."""

        try:
            self.db_manager.execute_write_query(
                """INSERT INTO session_logs 
                   (user_id, session_info, event_type, node_id, timestamp) 
                   VALUES (%s, %s, %s, %s, NOW());""",
                (user_id, session_info, event_type, self.node_id),
            )
        except Exception as e:
            logger.warning(f"Failed to log session event: {e}")

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from database cluster."""

        try:
            users = self.db_manager.execute_read_query(
                "SELECT * FROM users WHERE id = %s;", (user_id,), prefer_replica=True
            )
            return users[0] if users else None

        except Exception as e:
            logger.error(f"Failed to get user profile {user_id}: {e}")
            return None

    async def update_user_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> bool:
        """Update user profile in database cluster."""

        try:
            # Build dynamic update query
            update_fields = []
            update_values = []

            allowed_fields = ["name", "avatar_url", "email"]
            for field in allowed_fields:
                if field in profile_data:
                    update_fields.append(f"{field} = %s")
                    update_values.append(profile_data[field])

            if not update_fields:
                return False

            update_values.append(user_id)
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s;"

            self.db_manager.execute_write_query(query, tuple(update_values))

            # Log profile update
            await self._log_user_event(
                user_id, "profile_updated", f"Fields: {', '.join(update_fields)}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to update user profile {user_id}: {e}")
            return False

    async def _log_user_event(self, user_id: str, event_type: str, details: str = None):
        """Log user events to database cluster."""

        try:
            self.db_manager.execute_write_query(
                """INSERT INTO user_logs 
                   (user_id, event_type, details, node_id, timestamp) 
                   VALUES (%s, %s, %s, %s, NOW());""",
                (user_id, event_type, details, self.node_id),
            )
        except Exception as e:
            logger.warning(f"Failed to log user event: {e}")

    async def get_cluster_health(self) -> ClusterHealth:
        """Get comprehensive cluster health status."""

        try:
            # Check Redis cluster health
            redis_info = self.session_manager.get_cluster_info()
            redis_healthy = redis_info.get("cluster_state") == "ok"

            # Check database cluster health
            db_status = self.db_manager.get_cluster_status()
            db_healthy = db_status.get("cluster_health") == "healthy"

            # Determine overall status
            if redis_healthy and db_healthy:
                overall_status = "healthy"
            elif redis_healthy or db_healthy:
                overall_status = "degraded"
            else:
                overall_status = "critical"

            return ClusterHealth(
                redis_healthy=redis_healthy,
                database_healthy=db_healthy,
                overall_status=overall_status,
                details={
                    "redis_cluster": redis_info,
                    "database_cluster": db_status,
                    "node_id": self.node_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return ClusterHealth(
                redis_healthy=False,
                database_healthy=False,
                overall_status="error",
                details={"error": str(e), "node_id": self.node_id},
            )

    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired sessions and old log entries."""

        cleanup_results = {}

        try:
            # Clean up expired sessions from Redis
            expired_sessions = self.session_manager.cleanup_expired_sessions()
            cleanup_results["expired_sessions"] = expired_sessions

            # Clean up old log entries from database (older than 30 days)
            old_auth_logs = self.db_manager.execute_write_query(
                "DELETE FROM auth_logs WHERE timestamp < NOW() - INTERVAL '30 days';"
            )

            old_session_logs = self.db_manager.execute_write_query(
                "DELETE FROM session_logs WHERE timestamp < NOW() - INTERVAL '30 days';"
            )

            old_user_logs = self.db_manager.execute_write_query(
                "DELETE FROM user_logs WHERE timestamp < NOW() - INTERVAL '30 days';"
            )

            cleanup_results.update(
                {
                    "old_auth_logs": old_auth_logs,
                    "old_session_logs": old_session_logs,
                    "old_user_logs": old_user_logs,
                }
            )

            logger.info(f"Cleanup completed: {cleanup_results}")
            return cleanup_results

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            cleanup_results["error"] = str(e)
            return cleanup_results

    def shutdown(self):
        """Graceful shutdown of multi-node components."""

        logger.info(f"Shutting down multi-node API for node: {self.node_id}")

        try:
            # Clean up database connections
            self.db_manager.cleanup_connections()
            logger.info("Database connections cleaned up")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Example usage and health check endpoint
if __name__ == "__main__":
    import json

    # Initialize multi-node API
    api = MultiNodeNoxAPI()

    # Test cluster health
    async def test_health():
        health = await api.get_cluster_health()
        print(f"Cluster Health: {health.overall_status}")
        print(json.dumps(health.details, indent=2))

    # Test user authentication flow
    async def test_auth():
        user_data = {
            "id": "test-user-123",
            "email": "test@example.com",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
        }

        oauth_tokens = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
        }

        try:
            auth_result = await api.authenticate_user(
                oauth_provider="google", oauth_tokens=oauth_tokens, user_data=user_data
            )
            print(f"Authentication successful: {auth_result['session_id']}")

            # Test session retrieval
            session = await api.get_user_session(auth_result["session_id"])
            print(f"Session retrieved: {session is not None}")

        except Exception as e:
            print(f"Authentication test failed: {e}")

    # Run tests
    async def main():
        await test_health()
        print()
        await test_auth()

        # Cleanup
        api.shutdown()

    asyncio.run(main())
