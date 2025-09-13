"""
Dépendances FastAPI pour l'authentification et l'autorisation
"""

from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import User, UserRole, db
from .utils import AuthUtils, RoleChecker

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Dépendance pour récupérer l'utilisateur actuel à partir du token JWT"""

    # Extraire le token
    token = credentials.credentials

    # Vérifier et décoder le token
    token_data = AuthUtils.verify_token(token)

    # Récupérer l'utilisateur depuis la base de données
    user = await db.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Vérifier que l'utilisateur est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    return user


def require_role(required_role: str) -> Callable:
    """Dépendance pour vérifier qu'un utilisateur a un rôle spécifique"""

    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        if not RoleChecker.has_role(current_user.role, [required_role]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires role: {required_role}",
            )
        return current_user

    return check_role


def require_any_role(required_roles: List[str]) -> Callable:
    """Dépendance pour vérifier qu'un utilisateur a un des rôles de la liste"""

    async def check_roles(current_user: User = Depends(get_current_user)) -> User:
        if not RoleChecker.has_role(current_user.role, required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires one of these roles: {required_roles}",
            )
        return current_user

    return check_roles


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[User]:
    """Dépendance pour récupérer l'utilisateur actuel de manière optionnelle"""

    if not credentials:
        return None

    try:
        # Extraire le token
        token = credentials.credentials

        # Vérifier et décoder le token
        token_data = AuthUtils.verify_token(token)

        # Récupérer l'utilisateur depuis la base de données
        user = await db.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            return None

        return user
    except:
        return None


def require_admin() -> Callable:
    """Dépendance spécialisée pour les endpoints admin uniquement"""
    return require_role(UserRole.ADMIN)


def require_user_or_admin() -> Callable:
    """Dépendance pour les endpoints accessibles aux users et admins"""
    return require_any_role([UserRole.USER, UserRole.ADMIN])


async def check_endpoint_permission(
    request: Request, current_user: User = Depends(get_current_user)
) -> User:
    """Dépendance générale pour vérifier les permissions d'accès aux endpoints"""

    endpoint = request.url.path

    if not RoleChecker.can_access_endpoint(current_user.role, endpoint):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to endpoint: {endpoint}",
        )

    return current_user


class OptionalAuth:
    """Classe pour gérer l'authentification optionnelle avec fallback"""

    def __init__(self, fallback_to_legacy: bool = True):
        self.fallback_to_legacy = fallback_to_legacy

    async def __call__(self, request: Request) -> Optional[User]:
        """Authentification optionnelle avec fallback vers l'ancien système"""

        # Essayer l'authentification JWT d'abord
        try:
            credentials = await security(request)
            if credentials:
                user = await get_current_user(credentials)
                return user
        except:
            pass

        # Fallback vers l'ancien système de token si activé
        if self.fallback_to_legacy:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                legacy_token = auth_header.removeprefix("Bearer ").strip()
                # Ici vous pourriez vérifier l'ancien token NOX_API_TOKEN
                # Pour l'instant, on retourne None pour forcer l'utilisation du nouveau système
                pass

        return None


# Instance pour l'authentification optionnelle
optional_auth = OptionalAuth(fallback_to_legacy=True)
