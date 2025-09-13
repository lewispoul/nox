"""
Utilitaires pour l'authentification JWT et le hachage des mots de passe
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .models import User, UserRole
from .schemas import TokenData

# Configuration JWT
SECRET_KEY = os.getenv("NOX_JWT_SECRET", "nox-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("NOX_TOKEN_EXPIRE_MINUTES", "480")
)  # 8 heures par défaut

# Context de cryptage pour les mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthUtils:
    """Utilitaires d'authentification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hache un mot de passe"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifie un mot de passe"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        user: User, expires_delta: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Crée un token JWT pour l'utilisateur"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": user.id,  # subject = user ID
            "email": user.email,
            "role": user.role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # JWT ID pour l'invalidation éventuelle
        }

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "expires_in": int(
                expires_delta.total_seconds()
                if expires_delta
                else ACCESS_TOKEN_EXPIRE_MINUTES * 60
            ),
        }

    @staticmethod
    def verify_token(token: str) -> TokenData:
        """Vérifie et décode un token JWT"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            role: str = payload.get("role")

            if user_id is None or email is None or role is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing claims",
                )

            return TokenData(user_id=user_id, email=email, role=role)

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )

    @staticmethod
    def generate_user_id() -> str:
        """Génère un ID utilisateur unique"""
        return str(uuid.uuid4())

    @staticmethod
    def create_default_admin() -> User:
        """Crée un utilisateur admin par défaut"""
        admin_email = os.getenv("NOX_ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("NOX_ADMIN_PASSWORD", "admin123")

        if admin_password == "admin123":
            print("⚠️  WARNING: Using default admin password 'admin123'")
            print("   Please set NOX_ADMIN_PASSWORD environment variable")

        return User(
            id=AuthUtils.generate_user_id(),
            email=admin_email,
            hashed_password=AuthUtils.hash_password(admin_password),
            role=UserRole.ADMIN,
            quota_files=10000,
            quota_cpu_seconds=86400,  # 24h
            quota_memory_mb=4096,
        )


class RoleChecker:
    """Vérificateur de rôles pour les endpoints"""

    @staticmethod
    def has_role(user_role: str, required_roles: list) -> bool:
        """Vérifie si l'utilisateur a un des rôles requis"""
        if not required_roles:
            return True
        return user_role in required_roles

    @staticmethod
    def is_admin(user_role: str) -> bool:
        """Vérifie si l'utilisateur est admin"""
        return user_role == UserRole.ADMIN

    @staticmethod
    def can_access_endpoint(user_role: str, endpoint: str) -> bool:
        """Vérifie les permissions d'accès aux endpoints"""
        # Règles de permissions par endpoint
        admin_only_endpoints = [
            "/admin/users",
            "/admin/stats",
            "/auth/users",
            "/delete",  # Seuls les admins peuvent supprimer des fichiers
        ]

        user_endpoints = [
            "/health",
            "/metrics",
            "/put",
            "/run_py",
            "/run_sh",
            "/list",
            "/cat",
            "/auth/me",
            "/auth/login",
            "/auth/register",
        ]

        # Admin peut tout faire
        if user_role == UserRole.ADMIN:
            return True

        # User peut accéder aux endpoints de base
        if user_role == UserRole.USER:
            for allowed in user_endpoints:
                if endpoint.startswith(allowed):
                    return True

            # Vérifier si c'est un endpoint admin-only
            for admin_endpoint in admin_only_endpoints:
                if endpoint.startswith(admin_endpoint):
                    return False

            return True

        return False
