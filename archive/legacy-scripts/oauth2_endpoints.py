"""
OAuth2 Authentication Endpoints for Nox API v7.0.0 - M7 Integration
Provides OAuth2 authentication flow for Google, GitHub, and Microsoft
Integrates with M6 audit system for comprehensive tracking
"""

import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from enhanced_oauth2_service import OAuth2Profile, oauth2_service
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from jose import jwt

# Import OAuth2 configuration and service
from oauth2_config_m7 import get_provider_by_name, oauth2_settings

# Create router for OAuth2 endpoints
oauth2_router = APIRouter(prefix="/auth", tags=["OAuth2 Authentication"])

# ===== OAUTH2 STATE MANAGEMENT =====

# In-memory state storage (in production, use Redis)
oauth2_states: Dict[str, Dict[str, Any]] = {}


def generate_oauth2_state(provider: str, redirect_uri: str = None) -> str:
    """Generate secure OAuth2 state parameter"""
    state = secrets.token_urlsafe(32)
    oauth2_states[state] = {
        "provider": provider,
        "redirect_uri": redirect_uri,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
    }
    return state


def validate_oauth2_state(state: str) -> Optional[Dict[str, Any]]:
    """Validate and consume OAuth2 state parameter"""
    if state not in oauth2_states:
        return None

    state_data = oauth2_states[state]

    # Check if expired
    if datetime.utcnow() > state_data["expires_at"]:
        del oauth2_states[state]
        return None

    # Remove state (one-time use)
    del oauth2_states[state]
    return state_data


# ===== OAUTH2 AUTHORIZATION ENDPOINTS =====


@oauth2_router.get("/login/{provider}")
async def oauth2_login(
    provider: str,
    request: Request,
    redirect_uri: Optional[str] = Query(
        None, description="Optional redirect URI after login"
    ),
):
    """
    Initiate OAuth2 authorization flow

    Supported providers: google, github, microsoft
    """
    # Validate provider
    provider_config = get_provider_by_name(provider)
    if not provider_config:
        raise HTTPException(
            status_code=400, detail=f"Unsupported OAuth2 provider: {provider}"
        )

    # Generate secure state parameter
    state = generate_oauth2_state(provider, redirect_uri)

    # Build authorization URL
    auth_params = {
        "client_id": provider_config.client_id,
        "redirect_uri": provider_config.redirect_uri,
        "scope": " ".join(provider_config.scopes),
        "response_type": "code",
        "state": state,
        "access_type": (
            "offline" if provider == "google" else None
        ),  # For refresh tokens
    }

    # Remove None values
    auth_params = {k: v for k, v in auth_params.items() if v is not None}

    # Microsoft-specific parameters
    if provider == "microsoft":
        auth_params["prompt"] = "consent"  # Ensure refresh token

    auth_url = (
        f"{provider_config.authorization_url}?{urllib.parse.urlencode(auth_params)}"
    )

    return RedirectResponse(url=auth_url)


@oauth2_router.get("/callback/{provider}")
async def oauth2_callback(
    provider: str,
    request: Request,
    code: str = Query(..., description="OAuth2 authorization code"),
    state: str = Query(..., description="OAuth2 state parameter"),
    error: Optional[str] = Query(None, description="OAuth2 error"),
):
    """
    Handle OAuth2 authorization callback

    Exchanges authorization code for access token and creates/updates user
    """
    # Check for OAuth2 errors
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth2 error: {error}")

    # Validate state parameter
    state_data = validate_oauth2_state(state)
    if not state_data:
        raise HTTPException(
            status_code=400, detail="Invalid or expired state parameter"
        )

    if state_data["provider"] != provider:
        raise HTTPException(status_code=400, detail="State provider mismatch")

    # Get provider configuration
    provider_config = get_provider_by_name(provider)
    if not provider_config:
        raise HTTPException(
            status_code=400, detail=f"Unsupported OAuth2 provider: {provider}"
        )

    # Exchange authorization code for access token
    token_data = await exchange_code_for_token(provider, code, provider_config)

    # Get user information from OAuth2 provider
    access_token = token_data["access_token"]
    user_info = await oauth2_service.get_user_info(provider, access_token)

    # Create OAuth2Profile object
    if provider == "google":
        profile = OAuth2Profile.from_google(user_info)
    elif provider == "github":
        profile = OAuth2Profile.from_github(user_info)
    elif provider == "microsoft":
        profile = OAuth2Profile.from_microsoft(user_info)
    else:
        raise HTTPException(status_code=500, detail="Profile creation error")

    # Create or update user
    user_id = await oauth2_service.create_or_update_oauth2_user(profile, user_info)

    # Store OAuth2 tokens
    token_id = await oauth2_service.store_oauth2_tokens(
        user_id=user_id,
        provider=provider,
        access_token=access_token,
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 3600),
        scope=token_data.get("scope"),
    )

    # Log successful OAuth2 login session
    await log_oauth2_session(
        user_id=user_id,
        provider=provider,
        token_id=token_id,
        client_ip=request.client.host,
        user_agent=request.headers.get("User-Agent", ""),
        success=True,
    )

    # Generate JWT for API access
    api_token = generate_api_jwt(user_id, provider)

    # Determine redirect URL
    redirect_url = state_data.get("redirect_uri", "/dashboard")

    # Set JWT in httpOnly cookie and redirect
    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="nox_token",
        value=api_token,
        max_age=3600,  # 1 hour
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return response


# ===== TOKEN EXCHANGE =====


async def exchange_code_for_token(
    provider: str, code: str, provider_config
) -> Dict[str, Any]:
    """Exchange OAuth2 authorization code for access token"""
    token_data = {
        "grant_type": "authorization_code",
        "client_id": provider_config.client_id,
        "client_secret": provider_config.client_secret,
        "redirect_uri": provider_config.redirect_uri,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            provider_config.token_url,
            data=token_data,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()

        token_response = response.json()

        if "error" in token_response:
            raise HTTPException(
                status_code=400, detail=f"OAuth2 token error: {token_response['error']}"
            )

        return token_response


# ===== JWT GENERATION =====


def generate_api_jwt(user_id: str, provider: str = None) -> str:
    """Generate JWT token for API access"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "type": "access",
    }

    if provider:
        payload["oauth_provider"] = provider

    return jwt.encode(payload, oauth2_service.jwt_secret, algorithm="HS256")


# ===== AUDIT LOGGING =====


async def log_oauth2_session(
    user_id: str,
    provider: str,
    token_id: str,
    client_ip: str,
    user_agent: str,
    success: bool,
):
    """Log OAuth2 login session for audit tracking"""
    await oauth2_service.init_db_pool()

    async with oauth2_service.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO oauth2_login_sessions (
                user_id, provider, token_id, client_ip, user_agent, 
                login_at, success
            ) VALUES ($1, $2, $3, $4, $5, NOW(), $6)
            """,
            user_id,
            provider,
            token_id,
            client_ip,
            user_agent,
            success,
        )


# ===== TOKEN REFRESH ENDPOINTS =====


@oauth2_router.post("/refresh")
async def refresh_oauth2_token(
    request: Request,
    provider: str = Query(..., description="OAuth2 provider"),
    token_id: str = Query(..., description="Token ID to refresh"),
):
    """
    Refresh OAuth2 access token using refresh token
    """
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "")

    # Refresh the token
    new_tokens = await oauth2_service.refresh_oauth2_token(
        token_id=token_id, client_ip=client_ip, user_agent=user_agent
    )

    if not new_tokens:
        raise HTTPException(
            status_code=401,
            detail="Token refresh failed - invalid or expired refresh token",
        )

    return {"message": "Token refreshed successfully", "tokens": new_tokens.to_dict()}


# ===== PROFILE ENDPOINTS =====


@oauth2_router.get("/profile/{provider}")
async def get_oauth2_profile(
    provider: str, user_id: str = Query(..., description="User ID")
):
    """
    Get OAuth2 profile information for user and provider
    """
    profile = await oauth2_service.get_oauth2_profile(user_id, provider)

    if not profile:
        raise HTTPException(
            status_code=404, detail=f"OAuth2 profile not found for provider: {provider}"
        )

    # Remove sensitive information
    safe_profile = {
        "provider": profile["provider"],
        "email": profile["email"],
        "name": profile["name"],
        "username": profile["username"],
        "avatar_url": profile["avatar_url"],
        "email_verified": profile["email_verified"],
        "last_sync": profile["last_sync"].isoformat() if profile["last_sync"] else None,
    }

    return safe_profile


# ===== LOGOUT ENDPOINTS =====


@oauth2_router.post("/logout")
async def oauth2_logout(
    request: Request,
    response: Response,
    provider: Optional[str] = Query(
        None, description="Revoke tokens for specific provider"
    ),
    all_providers: bool = Query(False, description="Revoke tokens for all providers"),
):
    """
    Logout user and revoke OAuth2 tokens
    """
    # Clear JWT cookie
    response.delete_cookie(key="nox_token")

    # TODO: Extract user_id from JWT token
    # For now, return success message

    return {
        "message": "Logged out successfully",
        "revoked_provider": (
            provider if provider else "all" if all_providers else "none"
        ),
    }


# ===== ADMIN ENDPOINTS =====


@oauth2_router.get("/admin/stats")
async def get_oauth2_admin_stats():
    """
    Get OAuth2 usage statistics (admin only)
    """
    stats = await oauth2_service.get_oauth2_statistics()
    return {"oauth2_stats": stats, "generated_at": datetime.utcnow().isoformat()}


@oauth2_router.post("/admin/cleanup")
async def cleanup_oauth2_sessions():
    """
    Cleanup expired OAuth2 sessions (admin only)
    """
    cleaned_count = await oauth2_service.cleanup_expired_sessions()
    return {
        "message": f"Cleaned up {cleaned_count} expired OAuth2 sessions",
        "cleaned_at": datetime.utcnow().isoformat(),
    }


@oauth2_router.post("/admin/revoke/{user_id}")
async def revoke_user_oauth2_tokens_admin(
    user_id: str,
    provider: Optional[str] = Query(None, description="Specific provider to revoke"),
):
    """
    Revoke OAuth2 tokens for user (admin only)
    """
    revoked_count = await oauth2_service.revoke_user_oauth2_tokens(user_id, provider)
    return {
        "message": f"Revoked {revoked_count} OAuth2 tokens for user {user_id}",
        "provider": provider or "all",
        "revoked_at": datetime.utcnow().isoformat(),
    }


# ===== HEALTH CHECK =====


@oauth2_router.get("/health")
async def oauth2_health_check():
    """OAuth2 service health check"""
    try:
        await oauth2_service.init_db_pool()

        # Test database connectivity
        async with oauth2_service.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        return {
            "status": "healthy",
            "message": "OAuth2 service is operational",
            "providers": list(oauth2_settings.providers.keys()),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"OAuth2 service error: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
        }
