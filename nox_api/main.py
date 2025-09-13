"""
NOX API Main Module

This module serves as the main entry point for the NOX API.
"""

# Import the FastAPI app from the existing api module
try:
    from api.main import app

    __all__ = ["app"]
except ImportError:
    # Fallback if api.main is not available
    app = None
    __all__ = []
