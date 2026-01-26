import pytest
from pydantic import ValidationError

from api.services.settings import Settings


def test_iam_base_url_required_when_iam_use_remote():
    """Test that iam_base_url is required when iam_use_remote is True."""
    with pytest.raises(ValidationError, match="iam_base_url must be configured"):
        Settings(iam_use_remote=True, iam_base_url="")


def test_iam_base_url_must_be_valid_url():
    """Test that iam_base_url must be a valid HTTP(S) URL."""
    with pytest.raises(ValidationError, match="must be a valid HTTP"):
        Settings(iam_use_remote=True, iam_base_url="invalid-url")


def test_iam_base_url_valid_http():
    """Test that valid http URL is accepted."""
    settings = Settings(iam_use_remote=True, iam_base_url="http://localhost:8080")
    assert settings.iam_base_url == "http://localhost:8080"


def test_iam_base_url_valid_https():
    """Test that valid https URL is accepted."""
    settings = Settings(iam_use_remote=True, iam_base_url="https://example.com")
    assert settings.iam_base_url == "https://example.com"


def test_iam_base_url_not_required_when_iam_use_remote_false():
    """Test that iam_base_url is not required when iam_use_remote is False."""
    settings = Settings(iam_use_remote=False, iam_base_url="")
    assert settings.iam_base_url == ""
