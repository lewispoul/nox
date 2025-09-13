#!/usr/bin/env python3
"""
Nox API Python SDK - Authentication Manager
v8.0.0 Developer Experience Enhancement

Comprehensive authentication handling for API tokens, OAuth2 flows,
and biometric authentication integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Authentication related errors."""

    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    pass


class AuthManager:
    """
    Comprehensive authentication manager for Nox API.

    Supports:
    - API token authentication
    - OAuth2 authorization code flow
    - Token refresh and automatic renewal
    - Biometric authentication challenges
    - Session management across requests
    """

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        oauth_config: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize authentication manager.

        Args:
            base_url: Base URL for the API
            api_token: Direct API token for authentication
            oauth_config: OAuth2 configuration
        """

        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.oauth_config = oauth_config or {}

        # Authentication state
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.authenticated: bool = False

        # OAuth2 state
        self.oauth_state: Optional[str] = None
        self.authorization_code: Optional[str] = None

        # Session information
        self.session_id: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None

        logger.info("AuthManager initialized")

    async def authenticate(self, **kwargs) -> bool:
        """
        Authenticate using available method.

        Args:
            **kwargs: Additional authentication parameters

        Returns:
            True if authentication successful
        """

        # Try API token first if available
        if self.api_token:
            return await self._authenticate_with_token()

        # Try OAuth2 if configured
        if self.oauth_config:
            return await self._authenticate_with_oauth2(**kwargs)

        raise AuthenticationError("No authentication method configured")

    async def _authenticate_with_token(self) -> bool:
        """Authenticate using API token."""

        try:
            # Test the token by making a simple API call
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_token}"}

                async with session.get(
                    f"{self.base_url}/api/user/profile", headers=headers
                ) as response:

                    if response.status == 200:
                        user_data = await response.json()
                        self.user_info = user_data
                        self.authenticated = True
                        self.access_token = self.api_token

                        logger.info("API token authentication successful")
                        return True

                    elif response.status == 401:
                        logger.error("API token authentication failed - invalid token")
                        return False

                    else:
                        logger.error(
                            f"API token validation failed - status: {response.status}"
                        )
                        return False

        except Exception as e:
            logger.error(f"API token authentication error: {e}")
            return False

    async def _authenticate_with_oauth2(
        self,
        authorization_code: Optional[str] = None,
        redirect_uri: str = "http://localhost:8080/callback",
    ) -> bool:
        """
        Authenticate using OAuth2 flow.

        Args:
            authorization_code: OAuth2 authorization code
            redirect_uri: OAuth2 redirect URI

        Returns:
            True if authentication successful
        """

        if authorization_code:
            # Exchange authorization code for tokens
            return await self._exchange_authorization_code(
                authorization_code, redirect_uri
            )

        # Generate authorization URL for user
        auth_url = self.get_oauth2_authorization_url(redirect_uri)

        logger.info(f"OAuth2 authentication required. Visit: {auth_url}")

        # In a real implementation, this would either:
        # 1. Open a browser window for user authentication
        # 2. Return the URL for manual processing
        # 3. Use a callback server to capture the authorization code

        # For SDK purposes, we'll return False and expect the authorization code
        # to be provided in a subsequent call
        return False

    def get_oauth2_authorization_url(
        self,
        redirect_uri: str = "http://localhost:8080/callback",
        scopes: List[str] = None,
    ) -> str:
        """
        Generate OAuth2 authorization URL.

        Args:
            redirect_uri: OAuth2 redirect URI
            scopes: Requested OAuth2 scopes

        Returns:
            Authorization URL string
        """

        if not self.oauth_config.get("client_id"):
            raise AuthenticationError("OAuth2 client_id not configured")

        # Generate random state for CSRF protection
        import secrets

        self.oauth_state = secrets.token_urlsafe(32)

        scopes = scopes or ["profile", "api"]

        params = {
            "client_id": self.oauth_config["client_id"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": self.oauth_state,
        }

        return f"{self.base_url}/oauth/authorize?" + urlencode(params)

    async def _exchange_authorization_code(
        self, authorization_code: str, redirect_uri: str
    ) -> bool:
        """
        Exchange OAuth2 authorization code for access token.

        Args:
            authorization_code: OAuth2 authorization code
            redirect_uri: OAuth2 redirect URI

        Returns:
            True if token exchange successful
        """

        if not self.oauth_config.get("client_id") or not self.oauth_config.get(
            "client_secret"
        ):
            raise AuthenticationError("OAuth2 credentials not configured")

        token_data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": self.oauth_config["client_id"],
            "client_secret": self.oauth_config["client_secret"],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/oauth/token",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:

                    if response.status == 200:
                        token_response = await response.json()

                        self.access_token = token_response.get("access_token")
                        self.refresh_token = token_response.get("refresh_token")

                        # Calculate token expiration
                        expires_in = token_response.get("expires_in", 3600)
                        self.token_expires_at = datetime.utcnow() + timedelta(
                            seconds=expires_in
                        )

                        # Get user information
                        await self._fetch_user_info()

                        self.authenticated = True
                        self.authorization_code = authorization_code

                        logger.info("OAuth2 token exchange successful")
                        return True

                    else:
                        error_data = await response.json()
                        logger.error(f"OAuth2 token exchange failed: {error_data}")
                        return False

        except Exception as e:
            logger.error(f"OAuth2 token exchange error: {e}")
            return False

    async def _fetch_user_info(self) -> bool:
        """Fetch user information using access token."""

        if not self.access_token:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/user/profile", headers=headers
                ) as response:

                    if response.status == 200:
                        self.user_info = await response.json()
                        return True

                    return False

        except Exception as e:
            logger.error(f"Failed to fetch user info: {e}")
            return False

    async def refresh_token(self) -> bool:
        """
        Refresh access token using refresh token.

        Returns:
            True if token refresh successful
        """

        if not self.refresh_token:
            logger.warning("No refresh token available")
            return False

        if not self.oauth_config.get("client_id") or not self.oauth_config.get(
            "client_secret"
        ):
            logger.error("OAuth2 credentials not configured for token refresh")
            return False

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.oauth_config["client_id"],
            "client_secret": self.oauth_config["client_secret"],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/oauth/token",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:

                    if response.status == 200:
                        token_response = await response.json()

                        # Update tokens
                        self.access_token = token_response.get("access_token")
                        if token_response.get("refresh_token"):
                            self.refresh_token = token_response["refresh_token"]

                        # Update expiration
                        expires_in = token_response.get("expires_in", 3600)
                        self.token_expires_at = datetime.utcnow() + timedelta(
                            seconds=expires_in
                        )

                        logger.info("Token refresh successful")
                        return True

                    else:
                        error_data = await response.json()
                        logger.error(f"Token refresh failed: {error_data}")
                        self.authenticated = False
                        return False

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            self.authenticated = False
            return False

    async def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.

        Returns:
            True if authenticated and token is valid
        """

        if not self.authenticated or not self.access_token:
            return False

        # Check if token is expired
        if self.token_expires_at and datetime.utcnow() >= self.token_expires_at:
            # Try to refresh token
            if await self.refresh_token():
                return True
            else:
                self.authenticated = False
                return False

        return True

    async def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Returns:
            Dictionary of authentication headers
        """

        if not await self.is_authenticated():
            raise AuthenticationError("Not authenticated")

        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}

        return {}

    async def logout(self) -> bool:
        """
        Logout and revoke tokens.

        Returns:
            True if logout successful
        """

        try:
            if self.access_token:
                # Revoke token on server
                headers = {"Authorization": f"Bearer {self.access_token}"}

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/oauth/revoke",
                        headers=headers,
                        data={"token": self.access_token},
                    ) as response:

                        if response.status not in [200, 204]:
                            logger.warning(
                                f"Token revocation failed: {response.status}"
                            )

        except Exception as e:
            logger.warning(f"Token revocation error: {e}")

        # Clear local authentication state
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.authenticated = False
        self.session_id = None
        self.user_info = None

        logger.info("Logout successful")
        return True

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current user information.

        Returns:
            User information dictionary or None
        """
        return self.user_info

    def get_session_id(self) -> Optional[str]:
        """
        Get current session ID.

        Returns:
            Session ID string or None
        """
        return self.session_id

    def is_token_expired(self) -> bool:
        """
        Check if current token is expired.

        Returns:
            True if token is expired
        """
        if not self.token_expires_at:
            return False

        return datetime.utcnow() >= self.token_expires_at

    def get_token_expiry_info(self) -> Optional[Dict[str, Any]]:
        """
        Get token expiration information.

        Returns:
            Token expiry information or None
        """
        if not self.token_expires_at:
            return None

        now = datetime.utcnow()
        time_remaining = self.token_expires_at - now

        return {
            "expires_at": self.token_expires_at.isoformat(),
            "expires_in_seconds": int(time_remaining.total_seconds()),
            "is_expired": time_remaining.total_seconds() <= 0,
        }

    # Biometric authentication support
    async def initiate_biometric_challenge(
        self, challenge_types: List[str], session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Initiate biometric authentication challenge.

        Args:
            challenge_types: List of biometric challenge types
            session_id: Optional session ID

        Returns:
            Challenge information or None
        """

        if not await self.is_authenticated():
            raise AuthenticationError(
                "Must be authenticated to initiate biometric challenge"
            )

        challenge_data = {
            "challenge_types": challenge_types,
            "session_id": session_id or self.session_id,
        }

        try:
            headers = await self.get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/biometric/challenge",
                    json=challenge_data,
                    headers=headers,
                ) as response:

                    if response.status == 200:
                        challenge_info = await response.json()
                        logger.info(
                            f"Biometric challenge initiated: {challenge_info.get('challenge_id')}"
                        )
                        return challenge_info

                    else:
                        logger.error(f"Biometric challenge failed: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Biometric challenge error: {e}")
            return None

    async def complete_biometric_challenge(
        self, challenge_id: str, biometric_data: Dict[str, Any]
    ) -> bool:
        """
        Complete biometric authentication challenge.

        Args:
            challenge_id: Challenge ID
            biometric_data: Biometric authentication data

        Returns:
            True if challenge completed successfully
        """

        if not await self.is_authenticated():
            raise AuthenticationError(
                "Must be authenticated to complete biometric challenge"
            )

        try:
            headers = await self.get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/biometric/verify/{challenge_id}",
                    json=biometric_data,
                    headers=headers,
                ) as response:

                    if response.status == 200:
                        verification_result = await response.json()
                        success = verification_result.get("success", False)

                        if success:
                            logger.info("Biometric challenge completed successfully")
                        else:
                            logger.warning("Biometric challenge failed")

                        return success

                    else:
                        logger.error(
                            f"Biometric verification failed: {response.status}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Biometric verification error: {e}")
            return False
