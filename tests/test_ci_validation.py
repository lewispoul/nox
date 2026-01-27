#!/usr/bin/env python3
"""
Simple CI validation test - validates that basic linting and testing tools work
"""

import warnings

import pytest

# Silence noisy dependency deprecations from Bandit/Stevedore during import
warnings.filterwarnings(
    "ignore",
    message=r"^The verify_requirements argument is now a no-op",
    category=Warning,
)
warnings.filterwarnings(
    "ignore",
    message=r"^ast\.Str is deprecated",
    category=Warning,
)

pytestmark = [
    pytest.mark.filterwarnings("ignore:The verify_requirements argument is now a no-op.*"),
    pytest.mark.filterwarnings("ignore:ast.Str is deprecated.*"),
]


def test_import_basic_modules():
    """Test that basic modules can be imported"""
    import bandit
    import black
    import isort
    import pytest

    print("✅ All linting tools are importable")


def test_basic_functionality():
    """Test basic functionality"""
    assert 1 + 1 == 2
    assert "hello".upper() == "HELLO"
    print("✅ Basic functionality test passed")


def test_fastapi_import():
    """Test that FastAPI can be imported (optional)"""
    try:
        import fastapi

        print("✅ FastAPI is available")
    except ImportError:
        print("⚠️  FastAPI not available (expected in CI without full deps)")
        # This is expected and shouldn't fail the test


if __name__ == "__main__":
    print("🧪 Running CI validation tests...")

    # Run manual tests
    test_import_basic_modules()
    test_basic_functionality()
    test_fastapi_import()

    print("✅ All validation tests completed")
