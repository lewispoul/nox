"""
Nox API v7.0.0 - Complete M7 OAuth2 Integration
Incorporates comprehensive OAuth2 authentication, M6 audit system, and enhanced capabilities
Supports Google, GitHub, and Microsoft OAuth2 providers
"""

import logging
from datetime import datetime
from typing import Optional

import asyncpg
import uvicorn

# Import core components
from advanced_audit_middleware import AdvancedAuditMiddleware, SessionManager
from enhanced_oauth2_service import oauth2_service
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from oauth2_endpoints import oauth2_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/lppoulin/nox-api-src/logs/nox_api_v7.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("NoxAPI_v7.0.0")

# FastAPI app initialization
app = FastAPI(
    title="Nox API v7.0.0",
    description="Complete OAuth2 Integration with M6 Audit System - Phase 2 M7 Milestone",
    version="7.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Global components
session_manager = SessionManager()
database_pool: Optional[asyncpg.Pool] = None

# ===== MIDDLEWARE SETUP =====

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# M6 Advanced Audit Middleware
audit_middleware = AdvancedAuditMiddleware()
app.add_middleware(AdvancedAuditMiddleware)

# ===== DATABASE INITIALIZATION =====


async def init_database_pool():
    """Initialize database connection pool"""
    global database_pool
    try:
        database_pool = await asyncpg.create_pool(
            "postgresql://noxuser:test_password_123@localhost:5432/noxdb",
            min_size=10,
            max_size=30,
            command_timeout=15,
        )
        logger.info("✅ Database connection pool initialized")

        # Initialize OAuth2 service
        await oauth2_service.init_db_pool()
        logger.info("✅ OAuth2 service initialized")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def close_database_pool():
    """Close database connection pool"""
    global database_pool
    if database_pool:
        await database_pool.close()
        await oauth2_service.close_db_pool()
        logger.info("✅ Database connections closed")


# ===== LIFECYCLE EVENTS =====


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Starting Nox API v7.0.0 - M7 OAuth2 Integration")

    try:
        await init_database_pool()
        await session_manager.start_cleanup_task()

        logger.info("✅ All systems initialized successfully")
        logger.info("🔐 OAuth2 providers: Google, GitHub, Microsoft")
        logger.info("📊 M6 Audit system: Active")
        logger.info("🎯 API Server: Ready on port 8082")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("⏹️ Shutting down Nox API v7.0.0")

    try:
        await session_manager.stop_cleanup_task()
        await close_database_pool()
        logger.info("✅ Graceful shutdown completed")

    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# ===== INCLUDE OAUTH2 ROUTER =====

app.include_router(oauth2_router, prefix="/api/v7")

# ===== CORE API ENDPOINTS =====


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Nox API",
        "version": "7.0.0",
        "milestone": "M7 - Complete OAuth2 Integration",
        "phase": "Phase 2",
        "features": [
            "OAuth2 Authentication (Google, GitHub, Microsoft)",
            "M6 Audit & Advanced Logging",
            "Enhanced User Management",
            "Token Management & Refresh",
            "Profile Synchronization",
            "Admin Interface",
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v7/status")
async def api_status():
    """Comprehensive API status endpoint"""
    try:
        # Test database connectivity
        async with database_pool.acquire() as conn:
            db_status = await conn.fetchval("SELECT 1")
            db_healthy = db_status == 1

        # Get OAuth2 stats
        oauth2_stats = await oauth2_service.get_oauth2_statistics()

        # Get audit stats
        async with database_pool.acquire() as conn:
            audit_stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as sessions_24h
                FROM audit_sessions
                """
            )

        return {
            "status": "healthy",
            "version": "7.0.0",
            "database": {
                "connected": db_healthy,
                "pool_size": len(database_pool._holders) if database_pool else 0,
            },
            "oauth2": {
                "enabled_providers": list(oauth2_stats["providers"].keys()),
                "total_users": oauth2_stats["totals"]["total_users"],
                "active_tokens": oauth2_stats["totals"]["active_tokens"],
            },
            "audit": {
                "total_sessions": audit_stats["total_sessions"] if audit_stats else 0,
                "sessions_24h": audit_stats["sessions_24h"] if audit_stats else 0,
            },
            "session_manager": {
                "active_sessions": session_manager.get_active_session_count()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ===== USER MANAGEMENT ENDPOINTS =====


@app.get("/api/v7/users/profile")
async def get_user_profile(user_id: str = Query(..., description="User ID")):
    """Get comprehensive user profile including OAuth2 data"""
    try:
        async with database_pool.acquire() as conn:
            # Get user basic info
            user = await conn.fetchrow(
                "SELECT id, email, role, oauth_provider, created_at, updated_at FROM users WHERE id = $1",
                user_id,
            )

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Get OAuth2 profiles
            oauth2_profiles = await conn.fetch(
                """
                SELECT provider, email, name, username, avatar_url, 
                       email_verified, last_sync
                FROM oauth2_profiles 
                WHERE user_id = $1
                """,
                user_id,
            )

            # Get quota information
            quota = await conn.fetchrow(
                "SELECT quota_files, quota_cpu_seconds, quota_memory_mb, quota_storage_mb FROM users WHERE id = $1",
                user_id,
            )

            return {
                "user": dict(user),
                "oauth2_profiles": [dict(profile) for profile in oauth2_profiles],
                "quotas": dict(quota) if quota else {},
                "generated_at": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== ADMIN ENDPOINTS =====


@app.get("/api/v7/admin/audit/summary")
async def get_audit_summary():
    """Get comprehensive audit summary"""
    try:
        async with database_pool.acquire() as conn:
            # Get daily summaries
            daily_summaries = await conn.fetch(
                """
                SELECT summary_date, total_sessions, unique_users, total_actions,
                       avg_session_duration, most_common_action
                FROM audit_daily_summaries
                ORDER BY summary_date DESC
                LIMIT 30
                """
            )

            # Get recent high-impact actions
            high_impact_actions = await conn.fetch(
                """
                SELECT aa.id, aa.user_id, aa.action, aa.details, aa.created_at,
                       u.email as user_email
                FROM audit_admin_actions aa
                JOIN users u ON aa.user_id = u.id
                WHERE aa.created_at > NOW() - INTERVAL '7 days'
                ORDER BY aa.created_at DESC
                LIMIT 50
                """
            )

            return {
                "daily_summaries": [dict(summary) for summary in daily_summaries],
                "recent_high_impact": [dict(action) for action in high_impact_actions],
                "generated_at": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        logger.error(f"Error getting audit summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v7/admin/oauth2/tokens")
async def get_oauth2_tokens_admin(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    active_only: bool = Query(True, description="Show only active tokens"),
):
    """Get OAuth2 tokens for administration"""
    try:
        async with database_pool.acquire() as conn:
            query = """
                SELECT ot.id, ot.user_id, ot.provider, ot.expires_at, 
                       ot.is_revoked, ot.created_at, u.email as user_email
                FROM oauth2_tokens ot
                JOIN users u ON ot.user_id = u.id
                WHERE 1=1
            """
            params = []

            if provider:
                query += " AND ot.provider = $1"
                params.append(provider)

            if active_only:
                if provider:
                    query += " AND ot.expires_at > NOW() AND ot.is_revoked = false"
                else:
                    query += " AND ot.expires_at > NOW() AND ot.is_revoked = false"

            query += " ORDER BY ot.created_at DESC LIMIT 100"

            tokens = await conn.fetch(query, *params)

            return {
                "tokens": [dict(token) for token in tokens],
                "filters": {"provider": provider, "active_only": active_only},
                "generated_at": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        logger.error(f"Error getting OAuth2 tokens: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== METRICS ENDPOINTS =====


@app.get("/api/v7/metrics/prometheus")
async def get_prometheus_metrics():
    """Get Prometheus-formatted metrics"""
    try:
        metrics = []

        async with database_pool.acquire() as conn:
            # API metrics
            total_requests = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_actions WHERE created_at > NOW() - INTERVAL '1 hour'"
            )
            metrics.append(f"nox_api_requests_total {total_requests}")

            # OAuth2 metrics
            oauth2_stats = await oauth2_service.get_oauth2_statistics()
            for provider, stats in oauth2_stats["providers"].items():
                metrics.append(
                    f'nox_oauth2_users_total{{provider="{provider}"}} {stats["total_users"]}'
                )
                metrics.append(
                    f'nox_oauth2_active_tokens{{provider="{provider}"}} {stats["active_tokens"]}'
                )

            # Session metrics
            active_sessions = session_manager.get_active_session_count()
            metrics.append(f"nox_active_sessions {active_sessions}")

            # Database metrics
            db_connections = len(database_pool._holders) if database_pool else 0
            metrics.append(f"nox_database_connections {db_connections}")

        return Response(content="\n".join(metrics), media_type="text/plain")

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}", media_type="text/plain"
        )


# ===== ERROR HANDLERS =====


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with audit logging"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with audit logging"""
    logger.error(f"Unhandled exception: {exc} - {request.url}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ===== MAIN FUNCTION =====

if __name__ == "__main__":
    logger.info("🎯 Starting Nox API v7.0.0 - M7 OAuth2 Integration")

    # Run the server
    uvicorn.run(
        "nox_api_v7:app",
        host="0.0.0.0",
        port=8082,
        reload=False,
        log_level="info",
        access_log=True,
    )
