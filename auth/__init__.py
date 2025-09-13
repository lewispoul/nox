"""
Module d'authentification pour l'API Nox
"""

from .dependencies import get_current_user, optional_auth, require_admin, require_role
from .models import Database, User, UserRole, db
from .routes import router as auth_router
from .schemas import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserOut,
    UserStats,
    UserUpdate,
)
from .utils import AuthUtils, RoleChecker

__all__ = [
    # Models
    "User",
    "UserRole",
    "Database",
    "db",
    # Schemas
    "UserCreate",
    "UserLogin",
    "UserOut",
    "Token",
    "TokenData",
    "UserUpdate",
    "UserStats",
    # Utils
    "AuthUtils",
    "RoleChecker",
    # Dependencies
    "get_current_user",
    "require_role",
    "require_admin",
    "optional_auth",
    # Router
    "auth_router",
]
