"""
Schémas Pydantic pour l'authentification et les utilisateurs
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from .models import UserRole


class UserCreate(BaseModel):
    """Schéma pour créer un utilisateur"""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    role: Optional[str] = Field(default=UserRole.USER)
    quota_files: Optional[int] = Field(default=100, ge=1, le=10000)
    quota_cpu_seconds: Optional[int] = Field(default=3600, ge=60, le=86400)
    quota_memory_mb: Optional[int] = Field(default=512, ge=64, le=8192)

    @validator("role")
    def validate_role(cls, v):
        if not UserRole.is_valid_role(v):
            raise ValueError(f"Invalid role. Must be one of: {UserRole.all_roles()}")
        return v


class UserLogin(BaseModel):
    """Schéma pour la connexion utilisateur"""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=100)


class UserOut(BaseModel):
    """Schéma de sortie utilisateur (sans mot de passe)"""

    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    quota_files: int
    quota_cpu_seconds: int
    quota_memory_mb: int


class UserUpdate(BaseModel):
    """Schéma pour mettre à jour un utilisateur"""

    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    quota_files: Optional[int] = Field(default=None, ge=1, le=10000)
    quota_cpu_seconds: Optional[int] = Field(default=None, ge=60, le=86400)
    quota_memory_mb: Optional[int] = Field(default=None, ge=64, le=8192)

    @validator("role")
    def validate_role(cls, v):
        if v is not None and not UserRole.is_valid_role(v):
            raise ValueError(f"Invalid role. Must be one of: {UserRole.all_roles()}")
        return v


class Token(BaseModel):
    """Schéma pour le token JWT"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # en secondes


class TokenData(BaseModel):
    """Données contenues dans le token"""

    user_id: str
    email: str
    role: str


class UserStats(BaseModel):
    """Statistiques utilisateur"""

    total_users: int
    active_users: int
    admin_users: int
    regular_users: int


class ErrorResponse(BaseModel):
    """Schéma de réponse d'erreur"""

    error: str
    detail: Optional[str] = None
