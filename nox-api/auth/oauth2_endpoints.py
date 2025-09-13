"""
OAuth2 Authentication Endpoints for Nox API
Handles OAuth2 login flows with Google and GitHub
"""

import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from .oauth2_config import get_enabled_providers, oauth, oauth2_settings
from .oauth2_service import OAuth2Service

# Initialize OAuth2 service
oauth2_service = OAuth2Service(
    db_url=os.getenv(
        "DATABASE_URL", "postgresql://noxuser:password@localhost:5432/noxdb"
    ),
    jwt_secret=os.getenv("JWT_SECRET_KEY", "your-secret-key"),
)

router = APIRouter(prefix="/auth/oauth2", tags=["OAuth2 Authentication"])


@router.get("/providers")
async def get_oauth2_providers():
    """Get list of available OAuth2 providers"""
    providers = get_enabled_providers()

    return {
        "providers": [
            {
                "name": provider.name,
                "display_name": provider.display_name,
                "icon": provider.icon,
                "login_url": f"/auth/oauth2/{provider.name}/login",
            }
            for provider in providers
        ],
        "enabled": len(providers) > 0,
    }


@router.get("/{provider}/login")
async def oauth2_login(provider: str, request: Request):
    """Initiate OAuth2 login flow"""

    if not oauth2_settings.any_provider_enabled:
        raise HTTPException(
            status_code=501, detail="OAuth2 authentication is not configured"
        )

    # Check if provider is enabled
    enabled_providers = [p.name for p in get_enabled_providers()]
    if provider not in enabled_providers:
        raise HTTPException(
            status_code=400, detail=f"OAuth2 provider '{provider}' is not enabled"
        )

    try:
        # Get OAuth2 client for provider
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(
                status_code=500, detail=f"OAuth2 client for '{provider}' not found"
            )

        # Generate redirect URI
        redirect_uri = (
            f"{oauth2_settings.redirect_base_url}/auth/oauth2/{provider}/callback"
        )

        # Redirect to OAuth2 provider
        return await client.authorize_redirect(request, redirect_uri)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"OAuth2 login initiation failed: {str(e)}"
        )


@router.get("/{provider}/callback")
async def oauth2_callback(provider: str, request: Request):
    """Handle OAuth2 callback from provider"""

    try:
        # Get OAuth2 client for provider
        client = oauth.create_client(provider)
        if not client:
            return RedirectResponse(
                url=f"{oauth2_settings.frontend_error_url}&error=client_not_found"
            )

        # Exchange code for token
        token = await client.authorize_access_token(request)

        if not token:
            return RedirectResponse(
                url=f"{oauth2_settings.frontend_error_url}&error=token_exchange_failed"
            )

        # Authenticate user
        access_token = token.get("access_token")
        if not access_token:
            return RedirectResponse(
                url=f"{oauth2_settings.frontend_error_url}&error=no_access_token"
            )

        user, error = await oauth2_service.authenticate_oauth_user(
            provider, access_token
        )

        if error or not user:
            error_msg = error or "User authentication failed"
            return RedirectResponse(
                url=f"{oauth2_settings.frontend_error_url}&error={error_msg}"
            )

        # Create JWT tokens
        jwt_tokens = oauth2_service.create_jwt_tokens(user)

        # Redirect to frontend with success parameters
        success_params = {
            "auth": "success",
            "access_token": jwt_tokens["access_token"],
            "refresh_token": jwt_tokens["refresh_token"],
            "user_email": user.email,
            "user_role": user.role,
        }

        success_url = (
            f"{oauth2_settings.frontend_success_url}&{urlencode(success_params)}"
        )

        # Set secure cookies for tokens
        response = RedirectResponse(url=success_url)
        response.set_cookie(
            key="nox_access_token",
            value=jwt_tokens["access_token"],
            max_age=900,  # 15 minutes
            httponly=True,
            secure=True,
            samesite="lax",
        )
        response.set_cookie(
            key="nox_refresh_token",
            value=jwt_tokens["refresh_token"],
            max_age=604800,  # 7 days
            httponly=True,
            secure=True,
            samesite="lax",
        )

        return response

    except Exception as e:
        return RedirectResponse(
            url=f"{oauth2_settings.frontend_error_url}&error={str(e)}"
        )


@router.post("/{provider}/token")
async def oauth2_token_exchange(provider: str, request: Request):
    """
    Exchange OAuth2 authorization code for JWT tokens
    Alternative endpoint for SPA/mobile apps
    """

    try:
        data = await request.json()
        code = data.get("code")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code required")

        # Get OAuth2 client for provider
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(
                status_code=500, detail=f"OAuth2 client for '{provider}' not found"
            )

        # Exchange code for token manually
        redirect_uri = (
            f"{oauth2_settings.redirect_base_url}/auth/oauth2/{provider}/callback"
        )

        # This would require manual token exchange implementation
        # For now, redirect users to use the callback flow
        raise HTTPException(
            status_code=501,
            detail="Token exchange endpoint not yet implemented. Use callback flow.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")


@router.get("/status")
async def oauth2_status():
    """Get OAuth2 configuration status"""

    enabled_providers = get_enabled_providers()

    return {
        "enabled": oauth2_settings.any_provider_enabled,
        "providers": {
            "google": oauth2_settings.google_enabled,
            "github": oauth2_settings.github_enabled,
        },
        "available_providers": len(enabled_providers),
        "redirect_base_url": oauth2_settings.redirect_base_url,
        "configuration_valid": oauth2_settings.any_provider_enabled,
    }


# Startup event to initialize OAuth2 service
@router.on_event("startup")
async def startup_oauth2_service():
    """Initialize OAuth2 service on startup"""
    await oauth2_service.init_db_pool()


@router.on_event("shutdown")
async def shutdown_oauth2_service():
    """Cleanup OAuth2 service on shutdown"""
    await oauth2_service.close_db_pool()
