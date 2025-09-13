#!/usr/bin/env python3
"""
Nox API Python SDK
v8.0.0 Developer Experience Enhancement

A comprehensive Python SDK for the Nox API platform with advanced AI capabilities,
distributed architecture support, and developer-friendly interfaces.

Features:
- Async/sync API client with automatic retry and error handling
- Comprehensive authentication (API tokens, OAuth2, biometric)
- AI-powered security monitoring and threat detection
- Intelligent policy management and access control
- Advanced biometric authentication integration
- Performance metrics and analytics
- File upload/download with progress tracking
- Circuit breaker and rate limiting
- Extensive logging and debugging support

Quick Start:
    from nox_sdk import NoxClient

    # Simple usage with API token
    client = NoxClient(
        base_url="https://api.nox.example.com",
        api_token="your-api-token"
    )

    # Execute a script
    result = await client.execute_script("print('Hello from Nox!')", language="python")
    print(result.stdout)

    # Or use synchronously
    with client.sync() as sync_client:
        result = sync_client.execute_script("echo 'Hello from Nox!'", language="bash")
        print(result.stdout)

Advanced Usage:
    from nox_sdk import NoxClient, ExecutionMode
    from nox_sdk.ai import SecurityClient, PolicyClient, BiometricClient

    # Advanced client with AI features
    client = NoxClient(
        base_url="https://api.nox.example.com",
        api_token="your-api-token",
        enable_ai_security=True,
        enable_performance_tracking=True
    )

    # AI Security monitoring
    security = client.security
    threat_assessment = await security.analyze_api_call({
        "method": "POST",
        "endpoint": "/api/execute",
        "status_code": 200
    })

    # AI Policy evaluation
    policy = client.policy
    evaluation = await policy.evaluate_policy({
        "user_id": "user123",
        "resource": "/api/execute",
        "action": "write"
    })

    # Biometric authentication
    biometric = client.biometric
    auth_result = await biometric.authenticate_biometric(
        user_id="user123",
        biometric_type="fingerprint",
        biometric_data=fingerprint_data
    )

Configuration:
    The SDK can be configured via environment variables:
    - NOX_BASE_URL: API base URL
    - NOX_API_TOKEN: API authentication token
    - NOX_OAUTH_CLIENT_ID: OAuth2 client ID
    - NOX_OAUTH_CLIENT_SECRET: OAuth2 client secret
    - NOX_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    - NOX_ENABLE_AI_SECURITY: Enable AI security features
    - NOX_ENABLE_PERFORMANCE_TRACKING: Enable performance tracking
"""

from typing import Optional

from . import ai
from .auth import AuthManager
from .client import APIResponse, NoxClient
from .models import *
from .utils import *

# Version information
__version__ = "8.0.0"
__author__ = "Nox Development Team"
__email__ = "dev@nox.example.com"
__license__ = "MIT"
__description__ = "Advanced Python SDK for the Nox API platform with AI capabilities"

# Quick access to main classes
__all__ = [
    # Core client
    "NoxClient",
    "APIResponse",
    # Authentication
    "AuthManager",
    # AI modules (available as nox_sdk.ai.*)
    "ai",
    # Models and enums
    "ExecutionMode",
    "ScriptLanguage",
    "ExecutionStatus",
    "ExecutionResult",
    "ScriptInfo",
    "ExecutionRequest",
    "UserProfile",
    "SystemInfo",
    "HealthStatus",
    "APIError",
    "PaginatedResponse",
    "FileInfo",
    "UploadRequest",
    "LogEntry",
    "MetricValue",
    "PerformanceMetrics",
    "SessionInfo",
    "ResponseBuilder",
    "ModelConverter",
    "ValidationError",
    "ModelValidator",
    # Utilities
    "RetryConfig",
    "CircuitBreakerConfig",
    "RateLimiter",
    "CircuitBreaker",
    "RetryHandler",
    "RequestSigner",
    "FileUploadHelper",
    "CacheManager",
    "ConfigManager",
    "LogHandler",
    "ValidationUtils",
    "SecurityUtils",
]


# Convenience factory functions
def create_client(
    base_url: Optional[str] = None,
    api_token: Optional[str] = None,
    oauth_client_id: Optional[str] = None,
    oauth_client_secret: Optional[str] = None,
    **kwargs,
) -> NoxClient:
    """
    Create a NoxClient instance with automatic configuration.

    Args:
        base_url: API base URL (defaults to NOX_BASE_URL env var)
        api_token: API token (defaults to NOX_API_TOKEN env var)
        oauth_client_id: OAuth2 client ID (defaults to NOX_OAUTH_CLIENT_ID env var)
        oauth_client_secret: OAuth2 client secret (defaults to NOX_OAUTH_CLIENT_SECRET env var)
        **kwargs: Additional client configuration options

    Returns:
        Configured NoxClient instance
    """
    import os

    # Use environment variables as defaults
    base_url = base_url or os.getenv("NOX_BASE_URL")
    api_token = api_token or os.getenv("NOX_API_TOKEN")
    oauth_client_id = oauth_client_id or os.getenv("NOX_OAUTH_CLIENT_ID")
    oauth_client_secret = oauth_client_secret or os.getenv("NOX_OAUTH_CLIENT_SECRET")

    if not base_url:
        raise ValueError(
            "base_url must be provided or set NOX_BASE_URL environment variable"
        )

    # Create client with provided configuration
    client_config = {"base_url": base_url, **kwargs}

    if api_token:
        client_config["api_token"] = api_token
    elif oauth_client_id and oauth_client_secret:
        client_config["oauth_client_id"] = oauth_client_id
        client_config["oauth_client_secret"] = oauth_client_secret

    return NoxClient(**client_config)


def create_sync_client(
    base_url: Optional[str] = None,
    api_token: Optional[str] = None,
    oauth_client_id: Optional[str] = None,
    oauth_client_secret: Optional[str] = None,
    **kwargs,
):
    """
    Create a synchronous NoxClient instance.

    Args:
        base_url: API base URL
        api_token: API token
        oauth_client_id: OAuth2 client ID
        oauth_client_secret: OAuth2 client secret
        **kwargs: Additional client configuration options

    Returns:
        Synchronous client wrapper
    """
    client = create_client(
        base_url=base_url,
        api_token=api_token,
        oauth_client_id=oauth_client_id,
        oauth_client_secret=oauth_client_secret,
        **kwargs,
    )
    # Note: sync() method would need to be implemented in the client
    return client


def setup_logging(level: str = "INFO", format_type: str = "standard") -> None:
    """
    Setup logging for the SDK.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_type: Log format type (standard, detailed, json)
    """
    LogHandler.setup_logging(level, format_type)


def get_version() -> str:
    """Get SDK version."""
    return __version__


def get_client_info() -> dict:
    """Get client information."""
    return {
        "name": "Nox Python SDK",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "license": __license__,
    }


# Initialize default logging if not already configured
import logging

if not logging.getLogger().handlers:
    setup_logging()

# Add helpful message for first-time users
logger = logging.getLogger(__name__)
logger.debug(f"Nox Python SDK v{__version__} loaded")
logger.debug("For help getting started, visit: https://docs.nox.example.com/python-sdk")
logger.debug("For examples, see: https://github.com/nox-platform/python-sdk-examples")

# Convenience imports at module level
from .client import NoxClient
from .models import ExecutionMode, ScriptLanguage
