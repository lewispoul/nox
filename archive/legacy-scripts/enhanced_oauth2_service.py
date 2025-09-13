"""
Enhanced OAuth2 Service for Nox API v7.0.0 - M7 Complete Integration
Handles OAuth2 authentication, token management, and profile synchronization
Supports Google, GitHub, and Microsoft OAuth2 providers
"""

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import asyncpg
import httpx
from passlib.context import CryptContext

# Import OAuth2 configuration

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OAuth2TokenPair:
    """OAuth2 access and refresh token pair"""

    def __init__(
        self,
        access_token: str,
        refresh_token: str = None,
        expires_in: int = 3600,
        token_type: str = "Bearer",
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.token_type = token_type

    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        result = {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "expires_at": self.expires_at.isoformat(),
        }
        if self.refresh_token:
            result["refresh_token"] = self.refresh_token
        return result


class OAuth2Profile:
    """OAuth2 user profile information"""

    def __init__(
        self,
        provider: str,
        provider_user_id: str,
        email: str,
        name: str = None,
        username: str = None,
        avatar_url: str = None,
    ):
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.email = email
        self.name = name
        self.username = username
        self.avatar_url = avatar_url
        self.profile_data = {}
        self.email_verified = False

    @classmethod
    def from_google(cls, user_info: dict) -> "OAuth2Profile":
        """Create profile from Google user info"""
        return cls(
            provider="google",
            provider_user_id=user_info["id"],
            email=user_info["email"],
            name=user_info.get("name"),
            username=user_info.get("email", "").split("@")[0],
            avatar_url=user_info.get("picture"),
        )

    @classmethod
    def from_github(cls, user_info: dict) -> "OAuth2Profile":
        """Create profile from GitHub user info"""
        return cls(
            provider="github",
            provider_user_id=str(user_info["id"]),
            email=user_info.get("email", ""),
            name=user_info.get("name"),
            username=user_info.get("login"),
            avatar_url=user_info.get("avatar_url"),
        )

    @classmethod
    def from_microsoft(cls, user_info: dict) -> "OAuth2Profile":
        """Create profile from Microsoft user info"""
        return cls(
            provider="microsoft",
            provider_user_id=user_info["id"],
            email=user_info.get("mail") or user_info.get("userPrincipalName", ""),
            name=user_info.get("displayName"),
            username=user_info.get("mailNickname")
            or user_info.get("userPrincipalName", "").split("@")[0],
            avatar_url=None,  # Microsoft Graph API requires separate call for profile photo
        )


class EnhancedOAuth2Service:
    """Enhanced OAuth2 service with comprehensive provider support"""

    def __init__(self, database_url: str, jwt_secret: str):
        self.database_url = database_url
        self.jwt_secret = jwt_secret
        self.pool: Optional[asyncpg.Pool] = None

        # Token settings
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 30

    async def init_db_pool(self):
        """Initialize database connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=5, max_size=20, command_timeout=10
            )

    async def close_db_pool(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    # ===== PROVIDER-SPECIFIC USER INFO METHODS =====

    async def get_user_info_google(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google OAuth2"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            user_info = response.json()

            # Mark email as verified for Google (Google verifies emails)
            user_info["email_verified"] = True
            return user_info

    async def get_user_info_github(self, access_token: str) -> Dict[str, Any]:
        """Get user information from GitHub OAuth2"""
        async with httpx.AsyncClient() as client:
            # Get basic user info
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_response.raise_for_status()
            user_info = user_response.json()

            # Get verified email addresses
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary_email = next(
                    (email for email in emails if email.get("primary")),
                    emails[0] if emails else None,
                )
                if primary_email:
                    user_info["email"] = primary_email["email"]
                    user_info["email_verified"] = primary_email.get("verified", False)

            return user_info

    async def get_user_info_microsoft(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft OAuth2"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            user_info = response.json()

            # Microsoft emails are typically verified
            user_info["email_verified"] = True
            return user_info

    async def get_user_info(self, provider: str, access_token: str) -> Dict[str, Any]:
        """Get user information from OAuth2 provider"""
        if provider == "google":
            return await self.get_user_info_google(access_token)
        elif provider == "github":
            return await self.get_user_info_github(access_token)
        elif provider == "microsoft":
            return await self.get_user_info_microsoft(access_token)
        else:
            raise ValueError(f"Unsupported OAuth2 provider: {provider}")

    # ===== TOKEN MANAGEMENT =====

    def generate_token_hash(self, token: str) -> str:
        """Generate SHA-256 hash of token for audit purposes"""
        return hashlib.sha256(token.encode()).hexdigest()

    async def store_oauth2_tokens(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str = None,
        expires_in: int = 3600,
        scope: str = None,
    ) -> str:
        """Store OAuth2 tokens in database"""
        token_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        refresh_expires_at = (
            datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
            if refresh_token
            else None
        )

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO oauth2_tokens (
                    id, user_id, provider, access_token, refresh_token,
                    expires_at, refresh_expires_at, scope
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                token_id,
                user_id,
                provider,
                access_token,
                refresh_token,
                expires_at,
                refresh_expires_at,
                scope,
            )

        return token_id

    async def get_valid_oauth2_token(
        self, user_id: str, provider: str
    ) -> Optional[Dict]:
        """Get valid OAuth2 token for user and provider"""
        async with self.pool.acquire() as conn:
            token_record = await conn.fetchrow(
                """
                SELECT * FROM oauth2_tokens
                WHERE user_id = $1 AND provider = $2 
                  AND expires_at > NOW() AND is_revoked = false
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id,
                provider,
            )

            return dict(token_record) if token_record else None

    async def refresh_oauth2_token(
        self, token_id: str, client_ip: str = None, user_agent: str = None
    ) -> Optional[OAuth2TokenPair]:
        """Refresh OAuth2 access token using refresh token"""
        async with self.pool.acquire() as conn:
            # Get current token record
            token_record = await conn.fetchrow(
                """
                SELECT * FROM oauth2_tokens
                WHERE id = $1 AND refresh_expires_at > NOW() AND is_revoked = false
                """,
                token_id,
            )

            if not token_record:
                return None

            # Generate new tokens
            new_access_token = secrets.token_urlsafe(32)
            new_refresh_token = secrets.token_urlsafe(32)
            new_expires_at = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

            # Update token record
            await conn.execute(
                """
                UPDATE oauth2_tokens 
                SET access_token = $1, refresh_token = $2, expires_at = $3, updated_at = NOW()
                WHERE id = $4
                """,
                new_access_token,
                new_refresh_token,
                new_expires_at,
                token_id,
            )

            # Log token refresh for audit
            await conn.execute(
                """
                INSERT INTO oauth2_token_refreshes (
                    token_id, user_id, old_access_token_hash, new_access_token_hash,
                    client_ip, user_agent, success
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                token_id,
                token_record["user_id"],
                self.generate_token_hash(token_record["access_token"]),
                self.generate_token_hash(new_access_token),
                client_ip,
                user_agent,
                True,
            )

            return OAuth2TokenPair(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=self.access_token_expire_minutes * 60,
            )

    # ===== PROFILE MANAGEMENT =====

    async def store_oauth2_profile(
        self, user_id: str, profile: OAuth2Profile, raw_profile_data: dict
    ) -> None:
        """Store or update OAuth2 profile information"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO oauth2_profiles (
                    user_id, provider, provider_user_id, email, name, username,
                    avatar_url, profile_data, email_verified, last_sync
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                ON CONFLICT (user_id, provider) 
                DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    username = EXCLUDED.username,
                    avatar_url = EXCLUDED.avatar_url,
                    profile_data = EXCLUDED.profile_data,
                    email_verified = EXCLUDED.email_verified,
                    last_sync = NOW(),
                    updated_at = NOW()
                """,
                user_id,
                profile.provider,
                profile.provider_user_id,
                profile.email,
                profile.name,
                profile.username,
                profile.avatar_url,
                json.dumps(raw_profile_data),
                profile.email_verified,
            )

    async def get_oauth2_profile(self, user_id: str, provider: str) -> Optional[Dict]:
        """Get OAuth2 profile for user and provider"""
        async with self.pool.acquire() as conn:
            profile_record = await conn.fetchrow(
                """
                SELECT * FROM oauth2_profiles
                WHERE user_id = $1 AND provider = $2
                """,
                user_id,
                provider,
            )

            return dict(profile_record) if profile_record else None

    # ===== USER AUTHENTICATION =====

    async def create_or_update_oauth2_user(
        self, profile: OAuth2Profile, raw_profile_data: dict
    ) -> str:
        """Create new user or update existing user from OAuth2 profile"""
        async with self.pool.acquire() as conn:
            # Check if user already exists with this OAuth2 provider
            existing_user = await conn.fetchrow(
                """
                SELECT id FROM users
                WHERE oauth_provider = $1 AND oauth_id = $2
                """,
                profile.provider,
                profile.provider_user_id,
            )

            if existing_user:
                user_id = str(existing_user["id"])

                # Update user info from profile
                await conn.execute(
                    """
                    UPDATE users SET
                        email = $1,
                        updated_at = NOW()
                    WHERE id = $2
                    """,
                    profile.email,
                    user_id,
                )
            else:
                # Create new user
                user_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO users (
                        id, email, hashed_password, role, oauth_provider, oauth_id,
                        quota_files, quota_cpu_seconds, quota_memory_mb, quota_storage_mb
                    ) VALUES ($1, $2, $3, 'user', $4, $5, $6, $7, $8, $9)
                    """,
                    user_id,
                    profile.email,
                    "",
                    profile.provider,
                    profile.provider_user_id,
                    100,
                    3600,
                    512,
                    1024,  # Default quotas for OAuth2 users
                )

            # Store/update profile information
            await self.store_oauth2_profile(user_id, profile, raw_profile_data)

            return user_id

    # ===== ADMIN FUNCTIONS =====

    async def get_oauth2_statistics(self) -> Dict[str, Any]:
        """Get OAuth2 usage statistics"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetch("SELECT * FROM get_oauth2_user_stats()")

            total_stats = {
                "providers": {},
                "totals": {
                    "total_users": 0,
                    "active_tokens": 0,
                    "expired_tokens": 0,
                    "revoked_tokens": 0,
                },
            }

            for stat in stats:
                provider_stats = {
                    "total_users": stat["total_users"],
                    "active_tokens": stat["active_tokens"],
                    "expired_tokens": stat["expired_tokens"],
                    "revoked_tokens": stat["revoked_tokens"],
                }
                total_stats["providers"][stat["provider"]] = provider_stats

                # Add to totals
                total_stats["totals"]["total_users"] += stat["total_users"]
                total_stats["totals"]["active_tokens"] += stat["active_tokens"]
                total_stats["totals"]["expired_tokens"] += stat["expired_tokens"]
                total_stats["totals"]["revoked_tokens"] += stat["revoked_tokens"]

            return total_stats

    async def revoke_user_oauth2_tokens(
        self, user_id: str, provider: str = None
    ) -> int:
        """Revoke OAuth2 tokens for user"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT revoke_oauth2_tokens($1, $2)", user_id, provider
            )
            return result

    async def cleanup_expired_sessions(self) -> int:
        """Cleanup expired OAuth2 login sessions"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT cleanup_expired_oauth2_sessions()")
            return result


# Global OAuth2 service instance
oauth2_service = EnhancedOAuth2Service(
    database_url="postgresql://noxuser:test_password_123@localhost:5432/noxdb",
    jwt_secret="nox-oauth2-secret-change-in-production",
)
