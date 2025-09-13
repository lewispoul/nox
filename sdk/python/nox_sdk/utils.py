#!/usr/bin/env python3
"""
Nox API Python SDK - Utilities
v8.0.0 Developer Experience Enhancement

Utility functions and helpers for the Nox API Python SDK.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, BinaryIO, Callable, Dict, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RetryConfig:
    """Retry configuration."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout


class RateLimiter:
    """Rate limiter implementation."""

    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Acquire permission to make a call."""
        async with self._lock:
            now = time.time()
            # Remove old calls outside the time window
            self.calls = [
                call_time
                for call_time in self.calls
                if now - call_time < self.time_window
            ]

            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True

            return False

    async def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded."""
        while not await self.acquire():
            await asyncio.sleep(0.1)


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == "open":
                if time.time() - self.last_failure_time < self.config.timeout:
                    raise Exception("Circuit breaker is open")
                self.state = "half-open"
                self.success_count = 0

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self.failure_count = 0
            if self.state == "half-open":
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = "closed"

    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.config.failure_threshold:
                self.state = "open"


class RetryHandler:
    """Retry handler with exponential backoff."""

    def __init__(self, config: RetryConfig):
        self.config = config

    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt == self.config.max_attempts - 1:
                    break

                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.config.base_delay * (self.config.exponential_base**attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            import random

            delay = delay * (0.5 + random.random() * 0.5)

        return delay


class RequestSigner:
    """Request signature utilities."""

    @staticmethod
    def sign_request(
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        secret_key: str,
        timestamp: Optional[int] = None,
    ) -> str:
        """Sign an HTTP request."""
        if timestamp is None:
            timestamp = int(time.time())

        # Create canonical string
        canonical_parts = [
            method.upper(),
            urlparse(url).path,
            str(timestamp),
            json.dumps(dict(sorted(headers.items())), separators=(",", ":")),
            body or "",
        ]

        canonical_string = "\n".join(canonical_parts)

        # Create signature
        signature = hmac.new(
            secret_key.encode(), canonical_string.encode(), hashlib.sha256
        ).hexdigest()

        return f"NOX-HMAC-SHA256 Timestamp={timestamp}, Signature={signature}"

    @staticmethod
    def verify_signature(
        received_signature: str,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        secret_key: str,
        tolerance: int = 300,
    ) -> bool:
        """Verify request signature."""
        try:
            # Parse signature
            parts = received_signature.replace("NOX-HMAC-SHA256 ", "").split(", ")
            timestamp = None
            signature = None

            for part in parts:
                key, value = part.split("=", 1)
                if key == "Timestamp":
                    timestamp = int(value)
                elif key == "Signature":
                    signature = value

            if not timestamp or not signature:
                return False

            # Check timestamp tolerance
            if abs(int(time.time()) - timestamp) > tolerance:
                return False

            # Calculate expected signature
            expected = RequestSigner.sign_request(
                method, url, headers, body, secret_key, timestamp
            )

            expected_signature = expected.split("Signature=")[1]
            return hmac.compare_digest(signature, expected_signature)

        except Exception:
            return False


class FileUploadHelper:
    """Helper for file upload operations."""

    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size

    async def upload_file(
        self,
        file_path: str,
        upload_func: Callable,
        progress_callback: Optional[Callable] = None,
    ) -> Any:
        """Upload a file with progress tracking."""
        file_size = os.path.getsize(file_path)
        uploaded = 0

        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(self.chunk_size)
                if not chunk:
                    break

                # Upload chunk
                await upload_func(chunk)
                uploaded += len(chunk)

                # Call progress callback
                if progress_callback:
                    progress = (uploaded / file_size) * 100
                    await progress_callback(progress, uploaded, file_size)

    async def upload_stream(
        self,
        stream: BinaryIO,
        upload_func: Callable,
        total_size: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Any:
        """Upload from a stream with progress tracking."""
        uploaded = 0

        while True:
            chunk = stream.read(self.chunk_size)
            if not chunk:
                break

            # Upload chunk
            await upload_func(chunk)
            uploaded += len(chunk)

            # Call progress callback
            if progress_callback and total_size:
                progress = (uploaded / total_size) * 100
                await progress_callback(progress, uploaded, total_size)


class CacheManager:
    """Simple in-memory cache manager."""

    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return None

            return entry["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        async with self._lock:
            expires_at = time.time() + (ttl or self.default_ttl)
            self._cache[key] = {"value": value, "expires_at": expires_at}

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        async with self._lock:
            return self._cache.pop(key, None) is not None

    async def clear(self) -> None:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items() if now > entry["expires_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)


class ConfigManager:
    """Configuration management utilities."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or os.path.expanduser("~/.nox/config.json")
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    self._config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        # Check environment variables first
        env_key = f"NOX_{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # Check config file
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        self._save_config()

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")


class LogHandler:
    """Enhanced logging utilities."""

    @staticmethod
    def setup_logging(level: str = "INFO", format_type: str = "standard") -> None:
        """Setup logging configuration."""
        formats = {
            "standard": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            "json": '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
        }

        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=formats.get(format_type, formats["standard"]),
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    @staticmethod
    def create_request_logger() -> logging.Logger:
        """Create logger for HTTP requests."""
        logger = logging.getLogger("nox.requests")

        # Add custom handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - NOX-SDK - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger


class ValidationUtils:
    """Validation utility functions."""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe usage."""
        import re

        # Remove or replace unsafe characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove control characters
        sanitized = re.sub(r"[\x00-\x1f\x7f]", "", sanitized)
        # Limit length
        return sanitized[:255]

    @staticmethod
    def validate_json(json_str: str) -> bool:
        """Validate JSON string."""
        try:
            json.loads(json_str)
            return True
        except:
            return False


class SecurityUtils:
    """Security utility functions."""

    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """Generate cryptographically secure random string."""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt."""
        import bcrypt

        if salt is None:
            salt = bcrypt.gensalt()
        elif isinstance(salt, str):
            salt = salt.encode()

        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode(), salt.decode() if isinstance(salt, bytes) else salt

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        import bcrypt

        return bcrypt.checkpw(password.encode(), hashed.encode())

    @staticmethod
    def encode_base64(data: Union[str, bytes]) -> str:
        """Encode data to base64."""
        if isinstance(data, str):
            data = data.encode()
        return base64.b64encode(data).decode()

    @staticmethod
    def decode_base64(data: str) -> bytes:
        """Decode base64 data."""
        return base64.b64decode(data)


# Export all utilities
__all__ = [
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
