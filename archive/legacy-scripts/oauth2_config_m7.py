"""
Enhanced OAuth2 Configuration for Nox API v7.0.0 - M7 Implementation
Supports Google, GitHub, and Microsoft OAuth2 authentication providers
"""

import os
from typing import List, Optional

from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel
from starlette.config import Config


class OAuth2Settings(BaseModel):
    """OAuth2 configuration settings with Microsoft support"""

    # Google OAuth2
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

    # GitHub OAuth2
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None

    # Microsoft OAuth2 (Azure AD)
    microsoft_client_id: Optional[str] = None
    microsoft_client_secret: Optional[str] = None
    microsoft_tenant_id: Optional[str] = "common"  # 'common' for multi-tenant apps

    # OAuth2 URLs
    redirect_base_url: str = "http://localhost:8082"  # Updated to match M6 API port
    frontend_success_url: str = "http://localhost:8501?auth=success"
    frontend_error_url: str = "http://localhost:8501?auth=error"

    @property
    def google_enabled(self) -> bool:
        """Check if Google OAuth2 is configured"""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def github_enabled(self) -> bool:
        """Check if GitHub OAuth2 is configured"""
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def microsoft_enabled(self) -> bool:
        """Check if Microsoft OAuth2 is configured"""
        return bool(self.microsoft_client_id and self.microsoft_client_secret)

    @property
    def any_provider_enabled(self) -> bool:
        """Check if any OAuth2 provider is configured"""
        return self.google_enabled or self.github_enabled or self.microsoft_enabled

    @property
    def enabled_providers_count(self) -> int:
        """Get count of enabled providers"""
        count = 0
        if self.google_enabled:
            count += 1
        if self.github_enabled:
            count += 1
        if self.microsoft_enabled:
            count += 1
        return count


# Load OAuth2 settings from environment
oauth2_settings = OAuth2Settings(
    google_client_id=os.getenv(
        "GOOGLE_CLIENT_ID"
    ),  # Updated env var names for consistency
    google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    github_client_id=os.getenv("GITHUB_CLIENT_ID"),
    github_client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    microsoft_client_id=os.getenv("MICROSOFT_CLIENT_ID"),
    microsoft_client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
    microsoft_tenant_id=os.getenv("MICROSOFT_TENANT_ID", "common"),
    redirect_base_url=os.getenv("OAUTH_REDIRECT_BASE_URL", "http://localhost:8082"),
    frontend_success_url=os.getenv(
        "OAUTH_FRONTEND_SUCCESS_URL", "http://localhost:8501?auth=success"
    ),
    frontend_error_url=os.getenv(
        "OAUTH_FRONTEND_ERROR_URL", "http://localhost:8501?auth=error"
    ),
)

# Configure OAuth2 client
config = Config()
oauth = OAuth(config)

# Register Google OAuth2 provider
if oauth2_settings.google_enabled:
    oauth.register(
        name="google",
        client_id=oauth2_settings.google_client_id,
        client_secret=oauth2_settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid_configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    print("🌐 Google OAuth2 provider registered")

# Register GitHub OAuth2 provider
if oauth2_settings.github_enabled:
    oauth.register(
        name="github",
        client_id=oauth2_settings.github_client_id,
        client_secret=oauth2_settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        access_token_params=None,
        authorize_url="https://github.com/login/oauth/authorize",
        authorize_params=None,
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )
    print("🐙 GitHub OAuth2 provider registered")

# Register Microsoft OAuth2 provider (Azure AD)
if oauth2_settings.microsoft_enabled:
    # Construct Microsoft tenant-specific URLs
    tenant_id = oauth2_settings.microsoft_tenant_id
    oauth.register(
        name="microsoft",
        client_id=oauth2_settings.microsoft_client_id,
        client_secret=oauth2_settings.microsoft_client_secret,
        server_metadata_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid_configuration",
        client_kwargs={"scope": "openid email profile User.Read"},
    )
    print(f"🏢 Microsoft OAuth2 provider registered (tenant: {tenant_id})")


class OAuth2Provider:
    """OAuth2 provider information with enhanced metadata"""

    def __init__(
        self,
        name: str,
        display_name: str,
        icon: str,
        enabled: bool,
        description: str = "",
        scopes: List[str] = None,
    ):
        self.name = name
        self.display_name = display_name
        self.icon = icon
        self.enabled = enabled
        self.description = description
        self.scopes = scopes or []
        self.login_url = f"/auth/oauth2/{name}/login"
        self.callback_url = f"/auth/oauth2/{name}/callback"


# Available OAuth2 providers with enhanced metadata
OAUTH2_PROVIDERS = [
    OAuth2Provider(
        name="google",
        display_name="Google",
        icon="🌐",
        enabled=oauth2_settings.google_enabled,
        description="Sign in with your Google account",
        scopes=["openid", "email", "profile"],
    ),
    OAuth2Provider(
        name="github",
        display_name="GitHub",
        icon="🐙",
        enabled=oauth2_settings.github_enabled,
        description="Sign in with your GitHub account",
        scopes=["user:email"],
    ),
    OAuth2Provider(
        name="microsoft",
        display_name="Microsoft",
        icon="🏢",
        enabled=oauth2_settings.microsoft_enabled,
        description="Sign in with your Microsoft account",
        scopes=["openid", "email", "profile", "User.Read"],
    ),
]


def get_enabled_providers() -> List[OAuth2Provider]:
    """Get list of enabled OAuth2 providers"""
    return [provider for provider in OAUTH2_PROVIDERS if provider.enabled]


def get_provider_by_name(name: str) -> Optional[OAuth2Provider]:
    """Get OAuth2 provider by name"""
    for provider in OAUTH2_PROVIDERS:
        if provider.name == name:
            return provider
    return None


def get_providers_summary() -> dict:
    """Get summary of OAuth2 providers configuration"""
    enabled_providers = get_enabled_providers()

    return {
        "total_providers": len(OAUTH2_PROVIDERS),
        "enabled_providers": len(enabled_providers),
        "disabled_providers": len(OAUTH2_PROVIDERS) - len(enabled_providers),
        "providers": {
            provider.name: {
                "enabled": provider.enabled,
                "display_name": provider.display_name,
                "icon": provider.icon,
                "description": provider.description,
                "scopes": provider.scopes,
            }
            for provider in OAUTH2_PROVIDERS
        },
        "oauth2_enabled": oauth2_settings.any_provider_enabled,
    }


# Print OAuth2 configuration summary on import
enabled_count = oauth2_settings.enabled_providers_count
total_count = len(OAUTH2_PROVIDERS)

print(f"🔐 OAuth2 Configuration: {enabled_count}/{total_count} providers enabled")
if oauth2_settings.any_provider_enabled:
    enabled_names = [p.display_name for p in get_enabled_providers()]
    print(f"   ✅ Active providers: {', '.join(enabled_names)}")
else:
    print("   ⚠️  No OAuth2 providers configured")

# Export main objects
__all__ = [
    "oauth2_settings",
    "oauth",
    "OAuth2Provider",
    "OAUTH2_PROVIDERS",
    "get_enabled_providers",
    "get_provider_by_name",
    "get_providers_summary",
]
