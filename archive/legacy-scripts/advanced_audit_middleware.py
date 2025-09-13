"""
Advanced Audit Middleware for Nox API - M6 Implementation
Date: August 13, 2025

This middleware implements comprehensive audit logging with:
- Session tracking with unique IDs
- Detailed per-user, per-action logging
- Resource usage monitoring
- Prometheus metrics integration
- Database persistence for all audit events
"""

import asyncio
import hashlib
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

import asyncpg
import psutil
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditMetrics:
    """Prometheus-compatible metrics for audit tracking"""

    def __init__(self):
        self.action_counter = defaultdict(int)
        self.response_time_histogram = defaultdict(list)
        self.error_counter = defaultdict(int)
        self.quota_violation_counter = defaultdict(int)
        self.session_counter = 0

    def increment_action(self, user_id: str, action_type: str, success: bool):
        self.action_counter[
            f"{user_id}_{action_type}_{'success' if success else 'error'}"
        ] += 1

    def record_response_time(self, endpoint: str, response_time_ms: int):
        self.response_time_histogram[endpoint].append(response_time_ms)
        # Keep only last 1000 measurements for memory efficiency
        if len(self.response_time_histogram[endpoint]) > 1000:
            self.response_time_histogram[endpoint] = self.response_time_histogram[
                endpoint
            ][-1000:]

    def increment_error(self, endpoint: str, status_code: int):
        self.error_counter[f"{endpoint}_{status_code}"] += 1

    def increment_quota_violation(self, user_id: str, quota_type: str):
        self.quota_violation_counter[f"{user_id}_{quota_type}"] += 1

    def new_session(self):
        self.session_counter += 1

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus format metrics"""
        metrics = []

        # Action counters
        for key, count in self.action_counter.items():
            user_id, action_type, status = key.rsplit("_", 2)
            metrics.append(
                f'nox_audit_actions_total{{user_id="{user_id}", action_type="{action_type}", status="{status}"}} {count}'
            )

        # Response time histograms
        for endpoint, times in self.response_time_histogram.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                metrics.append(
                    f'nox_audit_response_time_ms_avg{{endpoint="{endpoint}"}} {avg_time:.2f}'
                )
                metrics.append(
                    f'nox_audit_response_time_ms_max{{endpoint="{endpoint}"}} {max_time}'
                )

        # Error counters
        for key, count in self.error_counter.items():
            endpoint, status_code = key.rsplit("_", 1)
            metrics.append(
                f'nox_audit_errors_total{{endpoint="{endpoint}", status_code="{status_code}"}} {count}'
            )

        # Quota violations
        for key, count in self.quota_violation_counter.items():
            user_id, quota_type = key.rsplit("_", 1)
            metrics.append(
                f'nox_audit_quota_violations_total{{user_id="{user_id}", quota_type="{quota_type}"}} {count}'
            )

        # Session counter
        metrics.append(f"nox_audit_sessions_total {self.session_counter}")

        return "\n".join(metrics) + "\n"


# Global metrics instance
audit_metrics = AuditMetrics()


class DatabaseConnection:
    """Async database connection manager for audit logging"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self, database_url: str):
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                database_url, min_size=2, max_size=10, command_timeout=5
            )
            logger.info("Audit database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audit database pool: {e}")

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

    async def execute_query(self, query: str, *args):
        """Execute a query with connection from pool"""
        if not self.pool:
            logger.warning("Database pool not initialized")
            return None

        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return None

    async def execute_insert(self, query: str, *args):
        """Execute an insert query"""
        if not self.pool:
            logger.warning("Database pool not initialized")
            return None

        try:
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Database insert error: {e}")
            return None


# Global database connection
db_connection = DatabaseConnection()


class SessionManager:
    """Manage user sessions for audit tracking"""

    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}

    def get_session_token_hash(self, auth_header: str) -> str:
        """Generate hash of authentication token for session tracking"""
        if not auth_header or not auth_header.startswith("Bearer "):
            return "anonymous"
        token = auth_header.removeprefix("Bearer ").strip()
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    async def get_or_create_session(
        self, user_id: str, token_hash: str, client_ip: str, user_agent: str
    ) -> str:
        """Get existing session or create new one"""
        session_key = f"{user_id}_{token_hash}"

        if session_key in self.active_sessions:
            # Update last activity
            self.active_sessions[session_key]["last_activity"] = datetime.utcnow()
            return self.active_sessions[session_key]["session_id"]

        # Create new session
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "token_hash": token_hash,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "started_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "is_active": True,
        }

        self.active_sessions[session_key] = session_data

        # Store in database
        await db_connection.execute_insert(
            """
            INSERT INTO audit_sessions (id, user_id, session_token_hash, client_ip, user_agent, started_at, last_activity, is_active, login_method)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO UPDATE SET
                last_activity = EXCLUDED.last_activity,
                is_active = EXCLUDED.is_active
            """,
            session_id,
            user_id,
            token_hash,
            client_ip,
            user_agent[:500] if user_agent else None,
            session_data["started_at"],
            session_data["last_activity"],
            True,
            "api_token",
        )

        audit_metrics.new_session()
        return session_id


# Global session manager
session_manager = SessionManager()


class AdvancedAuditMiddleware(BaseHTTPMiddleware):
    """Advanced audit middleware with comprehensive tracking"""

    def __init__(self, app, database_url: str = None):
        super().__init__(app)
        self.database_url = (
            database_url
            or "postgresql://noxuser:test_password_123@localhost:5432/noxdb"
        )

    async def dispatch(self, request: Request, call_next):
        # Skip audit for health and metrics endpoints to avoid noise
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Extract request context
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        auth_header = request.headers.get("authorization", "")
        user_id = self.extract_user_id(auth_header)  # You'll need to implement this

        # Get or create session
        token_hash = session_manager.get_session_token_hash(auth_header)
        session_id = await session_manager.get_or_create_session(
            user_id, token_hash, client_ip, user_agent
        )

        # Get request size
        request_size = self.get_request_size(request)

        # Categorize action
        action_type, action_category = self.categorize_action(request)

        # Process request
        response = None
        error_details = None
        cpu_start = time.process_time()
        memory_start = self.get_memory_usage()

        try:
            response = await call_next(request)
            success = 200 <= response.status_code < 400
        except Exception as e:
            success = False
            error_details = str(e)
            response = Response(content="Internal Server Error", status_code=500)

        # Calculate metrics
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        cpu_time_ms = int((time.process_time() - cpu_start) * 1000)
        memory_peak_mb = self.get_memory_usage() - memory_start

        # Get response size
        response_size = self.get_response_size(response)

        # Check for quota violation
        quota_violation = response.status_code == 429

        # Update metrics
        audit_metrics.increment_action(user_id, action_type, success)
        audit_metrics.record_response_time(request.url.path, response_time_ms)
        if not success:
            audit_metrics.increment_error(request.url.path, response.status_code)
        if quota_violation:
            audit_metrics.increment_quota_violation(user_id, "api_requests")

        # Log to database (async, don't block response)
        asyncio.create_task(
            self.log_audit_action(
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                endpoint=request.url.path,
                http_method=request.method,
                action_type=action_type,
                action_category=action_category,
                client_ip=client_ip,
                user_agent=user_agent,
                request_size=request_size,
                response_size=response_size,
                status_code=response.status_code,
                success=success,
                response_time_ms=response_time_ms,
                cpu_time_ms=cpu_time_ms,
                memory_peak_mb=memory_peak_mb,
                quota_violation=quota_violation,
                error_details=error_details,
            )
        )

        return response

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def extract_user_id(self, auth_header: str) -> str:
        """Extract user ID from auth header - implement based on your auth system"""
        # For now, return a valid UUID format for demonstration
        if not auth_header or not auth_header.startswith("Bearer "):
            return str(uuid.uuid4())  # anonymous user gets random UUID
        # This should decode your JWT or lookup token to get user ID
        # For demo, create UUID from token hash
        token = auth_header.removeprefix("Bearer ").strip()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        # Create a valid UUID from the hash
        uuid_string = (
            token_hash[:8]
            + "-"
            + token_hash[8:12]
            + "-"
            + token_hash[12:16]
            + "-"
            + token_hash[16:20]
            + "-"
            + token_hash[20:32]
        )
        return uuid_string

    def get_request_size(self, request: Request) -> int:
        """Estimate request size"""
        size = len(request.url.path.encode("utf-8"))
        for key, value in request.headers.items():
            size += len(key.encode("utf-8")) + len(value.encode("utf-8"))
        return size

    def get_response_size(self, response: Response) -> int:
        """Get response content size"""
        if hasattr(response, "body") and response.body:
            return len(response.body)
        return 0

    def get_memory_usage(self) -> int:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return int(process.memory_info().rss / 1024 / 1024)
        except:
            return 0

    def categorize_action(self, request: Request) -> tuple[str, str]:
        """Categorize the action based on endpoint and method"""
        path = request.url.path.lower()
        method = request.method.upper()

        # File operations
        if path.startswith("/ls") or path.startswith("/cat"):
            return "file_read", "filesystem"
        elif path.startswith("/upload") or path.startswith("/write"):
            return "file_write", "filesystem"
        elif path.startswith("/delete") or path.startswith("/rm"):
            return "file_delete", "filesystem"

        # Code execution
        elif path.startswith("/run") or path.startswith("/exec"):
            return "code_exec", "execution"

        # Admin operations
        elif path.startswith("/admin"):
            return "admin_action", "admin"

        # Authentication
        elif path.startswith("/auth") or path.startswith("/login"):
            return "auth", "auth"

        # Quota operations
        elif "quota" in path:
            return "quota_check", "quota"

        # Default
        else:
            return "api_call", "general"

    async def log_audit_action(self, **kwargs):
        """Log audit action to database"""
        try:
            await db_connection.execute_insert(
                """
                INSERT INTO audit_actions (
                    session_id, user_id, request_id, endpoint, http_method,
                    action_type, action_category, client_ip, user_agent,
                    request_size, response_size, status_code, success,
                    response_time_ms, cpu_time_ms, memory_peak_mb,
                    quota_violation, error_details, timestamp
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, NOW()
                )
                """,
                kwargs.get("session_id"),
                kwargs.get("user_id"),
                kwargs.get("request_id"),
                kwargs.get("endpoint"),
                kwargs.get("http_method"),
                kwargs.get("action_type"),
                kwargs.get("action_category"),
                kwargs.get("client_ip"),
                kwargs.get("user_agent", "")[:500],  # Truncate user agent
                kwargs.get("request_size", 0),
                kwargs.get("response_size", 0),
                kwargs.get("status_code"),
                kwargs.get("success"),
                kwargs.get("response_time_ms"),
                kwargs.get("cpu_time_ms"),
                kwargs.get("memory_peak_mb"),
                kwargs.get("quota_violation", False),
                kwargs.get("error_details", "")[:1000],  # Truncate error details
            )
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")


async def initialize_audit_system(database_url: str = None):
    """Initialize the audit system with database connection"""
    if not database_url:
        database_url = "postgresql://noxuser:test_password_123@localhost:5432/noxdb"
    await db_connection.initialize(database_url)


async def shutdown_audit_system():
    """Shutdown audit system and close connections"""
    await db_connection.close()


def get_audit_metrics() -> str:
    """Get Prometheus format audit metrics"""
    return audit_metrics.get_prometheus_metrics()


# Export for use in main API
__all__ = [
    "AdvancedAuditMiddleware",
    "initialize_audit_system",
    "shutdown_audit_system",
    "get_audit_metrics",
    "audit_metrics",
]
