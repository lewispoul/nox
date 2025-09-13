"""
OAuth2 Service for Nox API
Handles OAuth2 user creation, authentication, and profile management
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import asyncpg
import httpx
from jose import jwt
from passlib.context import CryptContext

from .models import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OAuth2Service:
    """Service for OAuth2 authentication and user management"""

    def __init__(self, db_url: str, jwt_secret: str):
        self.db_url = db_url
        self.jwt_secret = jwt_secret
        self.pool: Optional[asyncpg.Pool] = None

    async def init_db_pool(self):
        """Initialize database connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url)

    async def close_db_pool(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def get_user_info_google(self, token: str) -> Dict[str, Any]:
        """Get user information from Google OAuth2"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info_github(self, token: str) -> Dict[str, Any]:
        """Get user information from GitHub OAuth2"""
        async with httpx.AsyncClient() as client:
            # Get user profile
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {token}"},
            )
            user_response.raise_for_status()
            user_data = user_response.json()

            # Get user email (may be private)
            if not user_data.get("email"):
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"token {token}"},
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    primary_email = next(
                        (email["email"] for email in emails if email["primary"]), None
                    )
                    if primary_email:
                        user_data["email"] = primary_email

            return user_data

    async def create_or_get_oauth_user(
        self, provider: str, oauth_id: str, email: str, profile_data: Dict[str, Any]
    ) -> User:
        """Create or retrieve OAuth2 user"""
        await self.init_db_pool()

        async with self.pool.acquire() as conn:
            # Check if user exists by OAuth provider
            existing_user = await conn.fetchrow(
                "SELECT * FROM users WHERE oauth_provider = $1 AND oauth_id = $2",
                provider,
                oauth_id,
            )

            if existing_user:
                # Update profile data
                await conn.execute(
                    """UPDATE users 
                       SET email = $3, updated_at = $4 
                       WHERE oauth_provider = $1 AND oauth_id = $2""",
                    provider,
                    oauth_id,
                    email,
                    datetime.utcnow(),
                )
                return User(**dict(existing_user))

            # Check if user exists by email
            existing_email_user = await conn.fetchrow(
                "SELECT * FROM users WHERE email = $1", email
            )

            if existing_email_user:
                # Link OAuth provider to existing user
                await conn.execute(
                    """UPDATE users 
                       SET oauth_provider = $2, oauth_id = $3, updated_at = $4
                       WHERE email = $1""",
                    email,
                    provider,
                    oauth_id,
                    datetime.utcnow(),
                )
                return User(**dict(existing_email_user))

            # Create new user
            user_id = uuid.uuid4()
            hashed_password = pwd_context.hash(
                f"oauth_{provider}_{oauth_id}"
            )  # Placeholder password

            await conn.execute(
                """INSERT INTO users (
                    id, email, hashed_password, role, is_active, 
                    oauth_provider, oauth_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                user_id,
                email,
                hashed_password,
                UserRole.USER.value,
                True,
                provider,
                oauth_id,
                datetime.utcnow(),
                datetime.utcnow(),
            )

            # Fetch the created user
            new_user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

            return User(**dict(new_user))

    async def authenticate_oauth_user(
        self, provider: str, access_token: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user via OAuth2 provider
        Returns (User, error_message)
        """
        try:
            # Get user info from provider
            if provider == "google":
                user_info = await self.get_user_info_google(access_token)
                oauth_id = user_info["id"]
                email = user_info["email"]
            elif provider == "github":
                user_info = await self.get_user_info_github(access_token)
                oauth_id = str(user_info["id"])
                email = user_info.get("email")
                if not email:
                    return (
                        None,
                        "GitHub email not available. Please make your email public.",
                    )
            else:
                return None, f"Unsupported OAuth2 provider: {provider}"

            # Create or get user
            user = await self.create_or_get_oauth_user(
                provider, oauth_id, email, user_info
            )

            return user, None

        except httpx.HTTPStatusError as e:
            return None, f"OAuth2 provider error: {e.response.status_code}"
        except Exception as e:
            return None, f"OAuth2 authentication failed: {str(e)}"

    def create_jwt_tokens(self, user: User) -> Dict[str, Any]:
        """Create JWT access and refresh tokens for user"""
        now = datetime.utcnow()

        # Access token (15 minutes)
        access_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=15),
        }
        access_token = jwt.encode(access_token_data, self.jwt_secret, algorithm="HS256")

        # Refresh token (7 days)
        refresh_token_data = {
            "sub": str(user.id),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=7),
        }
        refresh_token = jwt.encode(
            refresh_token_data, self.jwt_secret, algorithm="HS256"
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 900,  # 15 minutes
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "oauth_provider": user.oauth_provider,
            },
        }

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        await self.init_db_pool()

        async with self.pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

            if user_row:
                return User(**dict(user_row))
            return None
