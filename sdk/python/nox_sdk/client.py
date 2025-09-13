#!/usr/bin/env python3
"""
Nox API Python SDK - Main Client
v8.0.0 Developer Experience Enhancement

Comprehensive Python SDK with AI integration, async/sync support,
and intelligent error handling for the Nox API distributed platform.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

import aiohttp
import httpx

from .ai.biometric import BiometricClient
from .ai.policy import PolicyClient
from .ai.security import SecurityClient
from .auth import AuthManager
from .models.api import *
from .utils import ErrorHandler, RetryConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NoxAPIError(Exception):
    """Base exception for Nox API SDK errors."""

    pass


class AuthenticationError(NoxAPIError):
    """Authentication related errors."""

    pass


class RateLimitError(NoxAPIError):
    """Rate limiting errors."""

    pass


class ValidationError(NoxAPIError):
    """Request validation errors."""

    pass


@dataclass
class APIResponse:
    """Standardized API response wrapper."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    response_time_ms: Optional[float] = None


class NoxClient:
    """
    Main Nox API client with comprehensive AI integration.

    Features:
    - Async/sync API operations
    - Automatic authentication and token management
    - Built-in retry logic with exponential backoff
    - AI security integration (threat detection, biometric auth)
    - Real-time metrics and performance monitoring
    - Comprehensive error handling with actionable suggestions
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_token: Optional[str] = None,
        oauth_config: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        retry_config: Optional[RetryConfig] = None,
        enable_ai_security: bool = True,
    ):
        """
        Initialize Nox API client.

        Args:
            base_url: Base URL for the Nox API
            api_token: API token for authentication
            oauth_config: OAuth2 configuration (client_id, client_secret, etc.)
            timeout: Request timeout in seconds
            retry_config: Retry configuration for failed requests
            enable_ai_security: Enable AI security features
        """

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.enable_ai_security = enable_ai_security

        # Initialize auth manager
        self.auth = AuthManager(
            base_url=base_url, api_token=api_token, oauth_config=oauth_config
        )

        # Initialize AI clients if enabled
        if enable_ai_security:
            self.security = SecurityClient(self)
            self.biometric = BiometricClient(self)
            self.policy = PolicyClient(self)

        # HTTP clients
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[aiohttp.ClientSession] = None

        # Error handler
        self.error_handler = ErrorHandler()

        # Performance tracking
        self.request_count = 0
        self.total_response_time = 0.0

        logger.info(f"Nox SDK initialized for {base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_async_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._async_client:
            await self._async_client.close()

    def __enter__(self):
        """Sync context manager entry."""
        self._ensure_sync_client()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        if self._sync_client:
            self._sync_client.close()

    def _ensure_sync_client(self) -> httpx.Client:
        """Ensure sync HTTP client is initialized."""
        if not self._sync_client:
            self._sync_client = httpx.Client(
                timeout=self.timeout, headers=self._get_default_headers()
            )
        return self._sync_client

    async def _ensure_async_client(self) -> aiohttp.ClientSession:
        """Ensure async HTTP client is initialized."""
        if not self._async_client:
            self._async_client = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_default_headers(),
            )
        return self._async_client

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "User-Agent": "Nox-Python-SDK/8.0.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def authenticate(self, **kwargs) -> bool:
        """
        Authenticate with the Nox API.

        Returns:
            True if authentication successful
        """
        return await self.auth.authenticate(**kwargs)

    def authenticate_sync(self, **kwargs) -> bool:
        """
        Synchronous authentication.

        Returns:
            True if authentication successful
        """
        return asyncio.run(self.authenticate(**kwargs))

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Make an async HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters
            headers: Additional headers

        Returns:
            APIResponse object with response data
        """

        start_time = time.time()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Ensure authentication
        if not await self.auth.is_authenticated():
            await self.authenticate()

        # Prepare headers
        request_headers = self._get_default_headers()
        auth_headers = await self.auth.get_auth_headers()
        request_headers.update(auth_headers)

        if headers:
            request_headers.update(headers)

        # Retry loop
        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                client = await self._ensure_async_client()

                async with client.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                ) as response:

                    response_time = (time.time() - start_time) * 1000
                    self._update_performance_metrics(response_time)

                    # Handle different response types
                    try:
                        response_data = await response.json()
                    except:
                        response_data = {"message": await response.text()}

                    api_response = APIResponse(
                        success=response.status < 400,
                        data=response_data if response.status < 400 else None,
                        error=(
                            response_data.get("error")
                            if response.status >= 400
                            else None
                        ),
                        status_code=response.status,
                        headers=dict(response.headers),
                        response_time_ms=response_time,
                    )

                    # Handle specific error cases
                    if response.status == 401:
                        # Try to refresh authentication
                        if await self.auth.refresh_token():
                            # Retry with new token
                            continue
                        raise AuthenticationError("Authentication failed")

                    elif response.status == 429:
                        # Rate limiting
                        retry_after = response.headers.get("Retry-After", "60")
                        raise RateLimitError(
                            f"Rate limited. Retry after {retry_after} seconds"
                        )

                    elif response.status >= 500:
                        # Server error - retry if we have attempts left
                        if attempt < self.retry_config.max_retries:
                            await asyncio.sleep(
                                self.retry_config.base_delay * (2**attempt)
                            )
                            continue

                    # AI security integration
                    if self.enable_ai_security and api_response.success:
                        await self._process_ai_security_response(
                            api_response, method, endpoint
                        )

                    return api_response

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.base_delay * (2**attempt)
                    logger.warning(f"Request failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue

        # All retries exhausted
        error_message = self.error_handler.get_error_suggestion(last_exception)

        response_time = (time.time() - start_time) * 1000
        self._update_performance_metrics(response_time)

        return APIResponse(
            success=False,
            error=f"Request failed after {self.retry_config.max_retries} retries: {error_message}",
            response_time_ms=response_time,
        )

    def request_sync(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Synchronous version of request method.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers

        Returns:
            APIResponse object
        """
        return asyncio.run(self.request(method, endpoint, data, params, headers))

    # Convenience methods for common HTTP operations
    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """GET request."""
        return await self.request("GET", endpoint, params=params)

    def get_sync(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Synchronous GET request."""
        return self.request_sync("GET", endpoint, params=params)

    async def post(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """POST request."""
        return await self.request("POST", endpoint, data=data)

    def post_sync(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Synchronous POST request."""
        return self.request_sync("POST", endpoint, data=data)

    async def put(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """PUT request."""
        return await self.request("PUT", endpoint, data=data)

    def put_sync(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Synchronous PUT request."""
        return self.request_sync("PUT", endpoint, data=data)

    async def delete(self, endpoint: str) -> APIResponse:
        """DELETE request."""
        return await self.request("DELETE", endpoint)

    def delete_sync(self, endpoint: str) -> APIResponse:
        """Synchronous DELETE request."""
        return self.request_sync("DELETE", endpoint)

    # High-level API methods
    async def get_user_profile(self) -> APIResponse:
        """Get current user profile."""
        return await self.get("/api/user/profile")

    async def list_users(self, limit: int = 50, offset: int = 0) -> APIResponse:
        """List users with pagination."""
        return await self.get(
            "/api/admin/users", params={"limit": limit, "offset": offset}
        )

    async def create_user(self, user_data: Dict[str, Any]) -> APIResponse:
        """Create a new user."""
        return await self.post("/api/admin/users", data=user_data)

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> APIResponse:
        """Update user information."""
        return await self.put(f"/api/admin/users/{user_id}", data=user_data)

    async def delete_user(self, user_id: str) -> APIResponse:
        """Delete a user."""
        return await self.delete(f"/api/admin/users/{user_id}")

    async def get_quotas(self) -> APIResponse:
        """Get user quotas information."""
        return await self.get("/api/quotas")

    async def get_metrics(self) -> APIResponse:
        """Get system metrics."""
        return await self.get("/api/metrics")

    async def get_audit_logs(
        self, limit: int = 50, offset: int = 0, filters: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Get audit logs with filtering."""
        params = {"limit": limit, "offset": offset}
        if filters:
            params.update(filters)
        return await self.get("/api/admin/audit", params=params)

    async def stream_logs(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream real-time audit logs."""
        # WebSocket streaming implementation would go here
        # For now, return a placeholder generator
        yield {"type": "log", "message": "Real-time log streaming not yet implemented"}

    async def _process_ai_security_response(
        self, response: APIResponse, method: str, endpoint: str
    ):
        """Process response through AI security analysis."""
        if not self.enable_ai_security:
            return

        try:
            # Analyze the API call for security patterns
            security_event = {
                "method": method,
                "endpoint": endpoint,
                "response_time": response.response_time_ms,
                "status_code": response.status_code,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Process through security client
            await self.security.analyze_api_call(security_event)

        except Exception as e:
            logger.warning(f"AI security analysis failed: {e}")

    def _update_performance_metrics(self, response_time: float):
        """Update client performance metrics."""
        self.request_count += 1
        self.total_response_time += response_time

    def get_performance_stats(self) -> Dict[str, float]:
        """Get client performance statistics."""
        if self.request_count == 0:
            return {"average_response_time": 0.0, "total_requests": 0}

        return {
            "average_response_time": self.total_response_time / self.request_count,
            "total_requests": self.request_count,
            "total_response_time": self.total_response_time,
        }

    async def health_check(self) -> APIResponse:
        """Perform API health check."""
        start_time = time.time()

        try:
            response = await self.get("/api/health")

            # Add additional health metrics
            if response.success and response.data:
                response.data["sdk_response_time"] = response.response_time_ms
                response.data["sdk_performance"] = self.get_performance_stats()

            return response

        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Health check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )

    # Synchronous versions of high-level methods
    def get_user_profile_sync(self) -> APIResponse:
        """Synchronous get user profile."""
        return asyncio.run(self.get_user_profile())

    def list_users_sync(self, limit: int = 50, offset: int = 0) -> APIResponse:
        """Synchronous list users."""
        return asyncio.run(self.list_users(limit, offset))

    def health_check_sync(self) -> APIResponse:
        """Synchronous health check."""
        return asyncio.run(self.health_check())


# Convenience factory functions
def create_client(
    base_url: str = "http://localhost:8080", api_token: Optional[str] = None, **kwargs
) -> NoxClient:
    """
    Factory function to create a Nox API client.

    Args:
        base_url: API base URL
        api_token: API authentication token
        **kwargs: Additional client configuration

    Returns:
        Configured NoxClient instance
    """
    return NoxClient(base_url=base_url, api_token=api_token, **kwargs)


def create_oauth_client(
    base_url: str, client_id: str, client_secret: str, **kwargs
) -> NoxClient:
    """
    Factory function to create OAuth2-enabled Nox API client.

    Args:
        base_url: API base URL
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        **kwargs: Additional client configuration

    Returns:
        OAuth2-configured NoxClient instance
    """
    oauth_config = {"client_id": client_id, "client_secret": client_secret}

    return NoxClient(base_url=base_url, oauth_config=oauth_config, **kwargs)


# Example usage
if __name__ == "__main__":
    import asyncio

    async def example_usage():
        """Example SDK usage."""

        # Create client
        async with create_client(
            base_url="http://localhost:8080",
            api_token="test123",
            enable_ai_security=True,
        ) as client:

            # Authenticate
            if await client.authenticate():
                print("✅ Authentication successful")

            # Health check
            health = await client.health_check()
            print(f"Health check: {health.success}")
            if health.data:
                print(f"API version: {health.data.get('version')}")

            # Get user profile
            profile = await client.get_user_profile()
            if profile.success:
                print(f"User: {profile.data.get('username')}")

            # List users (admin endpoint)
            users = await client.list_users(limit=10)
            print(f"Found {len(users.data.get('users', []))} users")

            # Performance stats
            stats = client.get_performance_stats()
            print(f"Average response time: {stats['average_response_time']:.2f}ms")

    # Run example
    asyncio.run(example_usage())
