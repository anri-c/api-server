"""API route handlers.

This module exports all API routers for the FastAPI application.
"""

from .auth import router as auth_router
from .health import router as health_router
from .items import router as items_router

__all__ = ["health_router", "auth_router", "items_router"]
