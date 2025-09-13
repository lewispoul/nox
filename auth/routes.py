"""
Routes d'authentification pour l'API Nox
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from .dependencies import get_current_user, require_role
from .models import User, UserRole, db
from .schemas import Token, UserCreate, UserLogin, UserOut, UserStats, UserUpdate
from .utils import AuthUtils

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Inscription d'un nouvel utilisateur"""
    # Vérifier si l'email existe déjà
    existing_user = await db.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Créer l'utilisateur
    user = User(
        id=AuthUtils.generate_user_id(),
        email=user_data.email,
        hashed_password=AuthUtils.hash_password(user_data.password),
        role=user_data.role or UserRole.USER,
        quota_files=user_data.quota_files or 100,
        quota_cpu_seconds=user_data.quota_cpu_seconds or 3600,
        quota_memory_mb=user_data.quota_memory_mb or 512,
    )

    await db.create_user(user)

    # Générer le token
    token_data = AuthUtils.create_access_token(user)
    return Token(**token_data)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Connexion utilisateur"""
    # Récupérer l'utilisateur
    user = await db.get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Vérifier le mot de passe
    if not AuthUtils.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Vérifier que l'utilisateur est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    # Générer le token
    token_data = AuthUtils.create_access_token(user)
    return Token(**token_data)


@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Informations de l'utilisateur connecté"""
    return UserOut(**current_user.to_dict())


@router.get("/users", response_model=List[UserOut])
async def list_users(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Liste tous les utilisateurs (admin uniquement)"""
    users = await db.list_users(limit=limit, offset=offset)
    return [UserOut(**user.to_dict()) for user in users]


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str, current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Récupère un utilisateur par ID (admin uniquement)"""
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserOut(**user.to_dict())


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Met à jour un utilisateur (admin uniquement)"""
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Mettre à jour les champs fournis
    if user_data.email is not None:
        # Vérifier que l'email n'est pas déjà utilisé
        existing_user = await db.get_user_by_email(user_data.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already used by another user",
            )
        user.email = user_data.email

    if user_data.role is not None:
        user.role = user_data.role

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    if user_data.quota_files is not None:
        user.quota_files = user_data.quota_files

    if user_data.quota_cpu_seconds is not None:
        user.quota_cpu_seconds = user_data.quota_cpu_seconds

    if user_data.quota_memory_mb is not None:
        user.quota_memory_mb = user_data.quota_memory_mb

    updated_user = await db.update_user(user)
    return UserOut(**updated_user.to_dict())


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str, current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Supprime un utilisateur (admin uniquement)"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    success = await db.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {"message": "User deleted successfully"}


@router.get("/stats", response_model=UserStats)
async def get_user_stats(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Statistiques des utilisateurs (admin uniquement)"""
    all_users = await db.list_users(limit=10000)  # Récupérer tous les utilisateurs

    total_users = len(all_users)
    active_users = sum(1 for user in all_users if user.is_active)
    admin_users = sum(1 for user in all_users if user.role == UserRole.ADMIN)
    regular_users = sum(1 for user in all_users if user.role == UserRole.USER)

    return UserStats(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        regular_users=regular_users,
    )


@router.post("/init-admin", response_model=UserOut)
async def init_default_admin():
    """Initialise l'utilisateur admin par défaut (uniquement si aucun admin existe)"""
    # Vérifier s'il y a déjà un admin
    all_users = await db.list_users(limit=1000)
    existing_admin = any(user.role == UserRole.ADMIN for user in all_users)

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Admin user already exists"
        )

    # Créer l'admin par défaut
    admin_user = AuthUtils.create_default_admin()

    # Vérifier si l'email existe déjà
    existing_user = await db.get_user_by_email(admin_user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin email already registered",
        )

    created_admin = await db.create_user(admin_user)
    return UserOut(**created_admin.to_dict())
