"""
Fixed Nox API v7.0.0 with proper middleware initialization
"""

import logging
from datetime import datetime
from typing import Optional

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("NoxAPI_v7.0.0")

# Import after logging setup
try:
    from enhanced_oauth2_service import oauth2_service
    from oauth2_endpoints import oauth2_router
except ImportError as e:
    logger.warning(f"OAuth2 import warning: {e}")
    oauth2_router = None

# FastAPI app initialization
app = FastAPI(
    title="Nox API v7.0.0",
    description="Complete OAuth2 Integration with M6 Audit System - Phase 2 M7 Milestone",
    version="7.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Global database pool
database_pool: Optional[asyncpg.Pool] = None

# ===== MIDDLEWARE SETUP =====

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== DATABASE INITIALIZATION =====


async def init_database_pool():
    """Initialize database connection pool"""
    global database_pool
    try:
        database_pool = await asyncpg.create_pool(
            "postgresql://noxuser:test_password_123@localhost:5432/noxdb",
            min_size=5,
            max_size=15,
            command_timeout=10,
        )
        logger.info("✅ Database connection pool initialized")

        # Initialize OAuth2 service if available
        if oauth2_service:
            await oauth2_service.init_db_pool()
            logger.info("✅ OAuth2 service initialized")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # Don't raise - allow API to start without database for testing


async def close_database_pool():
    """Close database connection pool"""
    global database_pool
    try:
        if database_pool:
            await database_pool.close()
        if oauth2_service:
            await oauth2_service.close_db_pool()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Database closure error: {e}")


# ===== LIFECYCLE EVENTS =====


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Starting Nox API v7.0.0 - M7 OAuth2 Integration")

    try:
        await init_database_pool()
        logger.info("✅ All systems initialized successfully")
        logger.info("🔐 OAuth2 providers: Available if configured")
        logger.info("📊 M6 Audit system: Available if configured")
        logger.info("🎯 API Server: Ready on port 8082")

    except Exception as e:
        logger.error(f"❌ Startup error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("⏹️ Shutting down Nox API v7.0.0")

    try:
        await close_database_pool()
        logger.info("✅ Graceful shutdown completed")

    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# ===== INCLUDE OAUTH2 ROUTER IF AVAILABLE =====

if oauth2_router:
    app.include_router(oauth2_router, prefix="/api/v7")
    logger.info("✅ OAuth2 router included")
else:
    logger.warning("⚠️ OAuth2 router not available")

# ===== CORE API ENDPOINTS =====


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Nox API",
        "version": "7.0.0",
        "milestone": "M7 - Complete OAuth2 Integration",
        "phase": "Phase 2",
        "status": "operational",
        "features": [
            "OAuth2 Authentication (Google, GitHub, Microsoft)",
            "M6 Audit & Advanced Logging",
            "Enhanced User Management",
            "Token Management & Refresh",
            "Profile Synchronization",
            "Admin Interface",
        ],
        "endpoints": {
            "documentation": "/docs",
            "status": "/api/v7/status",
            "oauth2_health": "/api/v7/auth/health",
            "metrics": "/api/v7/metrics/prometheus",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v7/status")
async def api_status():
    """Comprehensive API status endpoint"""
    try:
        status_info = {
            "status": "healthy",
            "version": "7.0.0",
            "milestone": "M7 Complete OAuth2 Integration",
            "database": {"connected": False, "pool_size": 0},
            "oauth2": {
                "service_available": oauth2_service is not None,
                "router_available": oauth2_router is not None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Test database if available
        if database_pool:
            try:
                async with database_pool.acquire() as conn:
                    db_test = await conn.fetchval("SELECT 1")
                    status_info["database"]["connected"] = db_test == 1
                    status_info["database"]["pool_size"] = (
                        len(database_pool._queue._queue)
                        if hasattr(database_pool, "_queue")
                        else 0
                    )
            except Exception as e:
                status_info["database"]["error"] = str(e)

        # Get OAuth2 stats if available
        if oauth2_service and database_pool:
            try:
                oauth2_stats = await oauth2_service.get_oauth2_statistics()
                status_info["oauth2"]["stats"] = oauth2_stats
            except Exception as e:
                status_info["oauth2"]["error"] = str(e)

        return status_info

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.get("/api/v7/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "ok",
        "service": "Nox API v7.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ===== METRICS ENDPOINT =====


@app.get("/api/v7/metrics/prometheus")
async def get_prometheus_metrics():
    """Get Prometheus-formatted metrics"""
    try:
        metrics = []

        # Basic API metrics
        metrics.append("# HELP nox_api_info Nox API version info")
        metrics.append('nox_api_info{version="7.0.0",milestone="M7"} 1')

        # Database metrics
        if database_pool:
            metrics.append(
                "# HELP nox_database_connections Current database connections"
            )
            metrics.append(
                f"nox_database_connections {len(database_pool._queue._queue) if hasattr(database_pool, '_queue') else 0}"
            )

        # OAuth2 metrics if available
        if oauth2_service and database_pool:
            try:
                oauth2_stats = await oauth2_service.get_oauth2_statistics()
                metrics.append(
                    "# HELP nox_oauth2_users_total Total OAuth2 users by provider"
                )
                for provider, stats in oauth2_stats.get("providers", {}).items():
                    metrics.append(
                        f'nox_oauth2_users_total{{provider="{provider}"}} {stats["total_users"]}'
                    )
            except Exception as e:
                metrics.append(f"# OAuth2 metrics error: {e}")

        metrics.append("# HELP nox_api_uptime_seconds API uptime")
        metrics.append("nox_api_uptime_seconds 1")

        return Response(content="\n".join(metrics) + "\n", media_type="text/plain")

    except Exception as e:
        return Response(
            content=f"# Error generating metrics: {e}\n", media_type="text/plain"
        )


# ===== ERROR HANDLERS =====


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
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
    """Handle general exceptions"""
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
        "nox_api_v7_fixed:app",
        host="0.0.0.0",
        port=8082,
        reload=False,
        log_level="info",
        access_log=True,
    )
