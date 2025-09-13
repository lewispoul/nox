"""
OAuth2 Configuration for Nox API
Supports Google and GitHub authentication providers
"""

import os
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel
from starlette.config import Config


class OAuth2Settings(BaseModel):
    """OAuth2 configuration settings"""

    # Google OAuth2
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

    # GitHub OAuth2
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None

    # OAuth2 URLs
    redirect_base_url: str = "http://localhost:8000"
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
    def any_provider_enabled(self) -> bool:
        """Check if any OAuth2 provider is configured"""
        return self.google_enabled or self.github_enabled


# Load OAuth2 settings from environment
oauth2_settings = OAuth2Settings(
    google_client_id=os.getenv("OAUTH_GOOGLE_CLIENT_ID"),
    google_client_secret=os.getenv("OAUTH_GOOGLE_CLIENT_SECRET"),
    github_client_id=os.getenv("OAUTH_GITHUB_CLIENT_ID"),
    github_client_secret=os.getenv("OAUTH_GITHUB_CLIENT_SECRET"),
    redirect_base_url=os.getenv("OAUTH_REDIRECT_BASE_URL", "http://localhost:8000"),
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


class OAuth2Provider:
    """OAuth2 provider information"""

    def __init__(self, name: str, display_name: str, icon: str, enabled: bool):
        self.name = name
        self.display_name = display_name
        self.icon = icon
        self.enabled = enabled


# Available OAuth2 providers
OAUTH2_PROVIDERS = [
    OAuth2Provider(
        name="google",
        display_name="Google",
        icon="🌐",
        enabled=oauth2_settings.google_enabled,
    ),
    OAuth2Provider(
        name="github",
        display_name="GitHub",
        icon="🐙",
        enabled=oauth2_settings.github_enabled,
    ),
]


def get_enabled_providers() -> list[OAuth2Provider]:
    """Get list of enabled OAuth2 providers"""
    return [provider for provider in OAUTH2_PROVIDERS if provider.enabled]
