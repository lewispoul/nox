"""
Quota management system for Nox API

This module provides:
- User quota models and enforcement
- PostgreSQL database operations
- Prometheus metrics collection
- FastAPI middleware and routes
- Admin and user endpoints
"""

from .database import QuotaDatabase
from .metrics import get_quota_metrics_output, quota_metrics
from .middleware import QuotaEnforcementMiddleware
from .migrations import run_migrations
from .models import QuotaCheckResult, QuotaType, QuotaViolation, UserQuota, UserUsage
from .routes import (
    admin_router,
    cleanup_quota_system,
    initialize_quota_system,
    user_router,
)

__all__ = [
    # Models
    "UserQuota",
    "UserUsage",
    "QuotaViolation",
    "QuotaCheckResult",
    "QuotaType",
    # Database
    "QuotaDatabase",
    # Middleware
    "QuotaEnforcementMiddleware",
    # Metrics
    "quota_metrics",
    "get_quota_metrics_output",
    # Routes
    "admin_router",
    "user_router",
    "initialize_quota_system",
    "cleanup_quota_system",
    # Migrations
    "run_migrations",
]

__version__ = "1.0.0"
