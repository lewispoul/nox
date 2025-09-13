#!/usr/bin/env python3
"""
Nox API Python SDK - Data Models
v8.0.0 Developer Experience Enhancement

Data models, response schemas, and utility classes for the Nox API platform.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ExecutionMode(Enum):
    """Script execution modes."""

    SAFE = "safe"
    NORMAL = "normal"
    PRIVILEGED = "privileged"


class ScriptLanguage(Enum):
    """Supported script languages."""

    PYTHON = "python"
    BASH = "bash"
    POWERSHELL = "powershell"
    JAVASCRIPT = "javascript"


class ExecutionStatus(Enum):
    """Execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResult:
    """Script execution result."""

    execution_id: str
    status: ExecutionStatus
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class ScriptInfo:
    """Script information."""

    script_id: str
    name: str
    description: str
    language: ScriptLanguage
    content: str
    created_at: str
    updated_at: Optional[str] = None
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRequest:
    """Script execution request."""

    script_content: Optional[str] = None
    script_id: Optional[str] = None
    language: Optional[ScriptLanguage] = None
    mode: ExecutionMode = ExecutionMode.SAFE
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300
    capture_output: bool = True
    working_directory: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserProfile:
    """User profile information."""

    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    profile_picture: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemInfo:
    """System information response."""

    version: str
    build_date: str
    environment: str
    features: List[str] = field(default_factory=list)
    limits: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "healthy"


@dataclass
class HealthStatus:
    """Health check response."""

    status: str
    version: str
    timestamp: str
    services: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIError:
    """API error response."""

    error_code: str
    message: str
    details: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None


@dataclass
class PaginatedResponse:
    """Paginated response wrapper."""

    data: List[Any]
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool = False
    has_previous: bool = False
    next_page: Optional[int] = None
    previous_page: Optional[int] = None


@dataclass
class FileInfo:
    """File information."""

    file_id: str
    filename: str
    size: int
    mime_type: str
    created_at: str
    updated_at: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    download_url: Optional[str] = None


@dataclass
class UploadRequest:
    """File upload request."""

    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_size: int = 8192
    allow_overwrite: bool = False


@dataclass
class LogEntry:
    """Log entry."""

    timestamp: str
    level: str
    message: str
    source: Optional[str] = None
    execution_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricValue:
    """Performance metric value."""

    name: str
    value: Union[int, float]
    unit: str
    timestamp: str
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""

    metrics: List[MetricValue]
    collected_at: str
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionInfo:
    """Session information."""

    session_id: str
    user_id: str
    created_at: str
    expires_at: str
    last_activity: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResponseBuilder:
    """Helper class for building API responses."""

    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """Build a success response."""
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if data is not None:
            response["data"] = data

        return response

    @staticmethod
    def error(
        error_code: str,
        message: str,
        details: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build an error response."""
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        if details:
            response["error"]["details"] = details

        if suggestions:
            response["error"]["suggestions"] = suggestions

        return response

    @staticmethod
    def paginated(
        data: List[Any], page: int, per_page: int, total: int
    ) -> Dict[str, Any]:
        """Build a paginated response."""
        total_pages = (total + per_page - 1) // per_page

        return {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "previous_page": page - 1 if page > 1 else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


class ModelConverter:
    """Utility class for model conversions."""

    @staticmethod
    def to_dict(obj: Any) -> Dict[str, Any]:
        """Convert a dataclass object to dictionary."""
        if hasattr(obj, "__dataclass_fields__"):
            result = asdict(obj)
            # Convert enums to their values
            for key, value in result.items():
                if isinstance(value, Enum):
                    result[key] = value.value
                elif isinstance(value, list):
                    result[key] = [
                        item.value if isinstance(item, Enum) else item for item in value
                    ]
            return result
        return obj

    @staticmethod
    def from_dict(cls, data: Dict[str, Any]) -> Any:
        """Create a dataclass object from dictionary."""
        if not hasattr(cls, "__dataclass_fields__"):
            return data

        # Handle enum conversions
        field_types = cls.__dataclass_fields__
        converted_data = {}

        for field_name, field_info in field_types.items():
            if field_name not in data:
                continue

            value = data[field_name]
            field_type = field_info.type

            # Handle Optional types
            if hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
                # Get the non-None type from Optional
                field_type = next(
                    (t for t in field_type.__args__ if t is not type(None)), field_type
                )

            # Convert enums
            if isinstance(field_type, type) and issubclass(field_type, Enum):
                if isinstance(value, str):
                    try:
                        converted_data[field_name] = field_type(value)
                    except ValueError:
                        converted_data[field_name] = value
                else:
                    converted_data[field_name] = value
            else:
                converted_data[field_name] = value

        return cls(**converted_data)

    @staticmethod
    def to_json(obj: Any, indent: Optional[int] = None) -> str:
        """Convert object to JSON string."""
        return json.dumps(ModelConverter.to_dict(obj), indent=indent, default=str)

    @staticmethod
    def from_json(cls, json_str: str) -> Any:
        """Create object from JSON string."""
        data = json.loads(json_str)
        return ModelConverter.from_dict(cls, data)


class ValidationError(Exception):
    """Model validation error."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error for field '{field}': {message}")


class ModelValidator:
    """Model validation utilities."""

    @staticmethod
    def validate_execution_request(request: ExecutionRequest) -> List[ValidationError]:
        """Validate execution request."""
        errors = []

        # Must have either script_content or script_id
        if not request.script_content and not request.script_id:
            errors.append(
                ValidationError(
                    "script", "Either script_content or script_id must be provided"
                )
            )

        # Validate timeout
        if request.timeout <= 0 or request.timeout > 3600:
            errors.append(
                ValidationError("timeout", "Timeout must be between 1 and 3600 seconds")
            )

        # Validate language if script_content is provided
        if request.script_content and not request.language:
            errors.append(
                ValidationError(
                    "language",
                    "Language must be specified when providing script_content",
                )
            )

        return errors

    @staticmethod
    def validate_upload_request(request: UploadRequest) -> List[ValidationError]:
        """Validate upload request."""
        errors = []

        # Validate filename
        if not request.filename or not request.filename.strip():
            errors.append(ValidationError("filename", "Filename cannot be empty"))

        # Validate size if provided
        if request.size is not None and request.size <= 0:
            errors.append(ValidationError("size", "File size must be greater than 0"))

        # Validate chunk size
        if request.chunk_size <= 0:
            errors.append(
                ValidationError("chunk_size", "Chunk size must be greater than 0")
            )

        return errors


# Export commonly used types
__all__ = [
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
]
