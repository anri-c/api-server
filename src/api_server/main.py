"""FastAPI application entry point.

This module initializes the FastAPI application with all routers,
middleware, database lifecycle management, configuration, logging,
and global exception handlers for consistent error responses.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import lifespan
from .exceptions import (
    APIException,
    api_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from .logging_config import LoggingMiddleware, setup_logging
from .middleware import (
    AuthenticationContextMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from .routers import auth_router, health_router, items_router

# Configure logger for this module
logger = logging.getLogger(__name__)

# Initialize logging before creating the app
setup_logging(settings)
logger.info("Starting FastAPI application initialization")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    This function creates the FastAPI application instance with all necessary
    configuration including middleware, exception handlers, and routers.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Create FastAPI application with comprehensive configuration
    app = FastAPI(
        title="API Server",
        description="FastAPI server with PostgreSQL, SQLModel, and LINE authentication",
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,  # Disable docs in production
        redoc_url="/redoc" if settings.debug else None,  # Disable redoc in production
        openapi_url="/openapi.json"
        if settings.debug
        else None,  # Disable OpenAPI in production
        contact={"name": "API Server Support", "email": "support@example.com"},
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    logger.info("FastAPI application created with basic configuration")

    # Configure middleware stack (order matters!)
    configure_middleware(app)

    # Register exception handlers
    configure_exception_handlers(app)

    # Register routers
    configure_routers(app)

    # Add root endpoint
    configure_root_endpoints(app)

    logger.info("FastAPI application configuration completed")
    return app


def configure_middleware(app: FastAPI) -> None:
    """Configure middleware stack for the application.

    Args:
        app: FastAPI application instance
    """
    logger.info("Configuring middleware stack")

    # Security headers middleware (should be first)
    app.add_middleware(SecurityHeadersMiddleware)

    # Trusted host middleware for production security
    if settings.is_production:
        # In production, configure with actual allowed hosts
        allowed_hosts = ["api.yourdomain.com", "*.yourdomain.com"]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
        logger.info(f"Trusted host middleware configured with hosts: {allowed_hosts}")

    # CORS middleware configuration
    configure_cors_middleware(app)

    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Authentication context middleware
    app.add_middleware(AuthenticationContextMiddleware)

    # Legacy logging middleware (keeping for compatibility)
    app.add_middleware(LoggingMiddleware)

    logger.info("Middleware stack configuration completed")


def configure_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware based on environment.

    Args:
        app: FastAPI application instance
    """
    if settings.is_development:
        # Development: Allow all origins for easier testing
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS configured for development (allow all origins)")
    elif settings.is_production:
        # Production: Restrict to specific origins
        allowed_origins = [
            "https://yourdomain.com",
            "https://www.yourdomain.com",
            "https://app.yourdomain.com",
        ]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
            max_age=86400,  # Cache preflight requests for 24 hours
        )
        logger.info(f"CORS configured for production with origins: {allowed_origins}")
    else:
        # Testing or other environments: Minimal CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )
        logger.info("CORS configured for testing environment")


def configure_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers.

    Args:
        app: FastAPI application instance
    """
    logger.info("Configuring exception handlers")

    # Register custom API exception handler
    app.add_exception_handler(APIException, api_exception_handler)

    # Register FastAPI HTTP exception handler
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Register validation exception handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Register service-specific exception handlers
    configure_service_exception_handlers(app)

    # Register generic exception handler (must be last)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers configuration completed")


def configure_service_exception_handlers(app: FastAPI) -> None:
    """Configure service-specific exception handlers.

    Args:
        app: FastAPI application instance
    """
    try:
        from .services.auth_service import JWTError, LineAuthError
        from .services.item_service import (
            ItemAccessDeniedServiceError,
            ItemNotFoundServiceError,
            ItemServiceError,
            ItemValidationError,
        )

        async def service_exception_handler(
            request: Request, exc: Exception
        ) -> JSONResponse:
            """Handle service-specific exceptions by converting to APIException."""
            if isinstance(exc, (LineAuthError, JWTError)):
                api_exc = APIException(
                    message=exc.message,
                    status_code=exc.status_code,
                    error_code=type(exc).__name__.lower().replace("error", "_error"),
                )
            elif isinstance(
                exc,
                (
                    ItemServiceError,
                    ItemNotFoundServiceError,
                    ItemAccessDeniedServiceError,
                    ItemValidationError,
                ),
            ):
                api_exc = APIException(
                    message=exc.message,
                    status_code=exc.status_code,
                    error_code=type(exc)
                    .__name__.lower()
                    .replace("serviceerror", "_error")
                    .replace("error", "_error"),
                )
            else:
                api_exc = APIException(
                    message=str(exc), status_code=500, error_code="service_error"
                )

            return await api_exception_handler(request, api_exc)

        # Register service exception handlers
        app.add_exception_handler(LineAuthError, service_exception_handler)
        app.add_exception_handler(JWTError, service_exception_handler)
        app.add_exception_handler(ItemServiceError, service_exception_handler)
        app.add_exception_handler(ItemNotFoundServiceError, service_exception_handler)
        app.add_exception_handler(
            ItemAccessDeniedServiceError, service_exception_handler
        )
        app.add_exception_handler(ItemValidationError, service_exception_handler)

        logger.info("Service-specific exception handlers registered")

    except ImportError as e:
        logger.warning(f"Could not import service exceptions: {e}")


def configure_routers(app: FastAPI) -> None:
    """Configure and register API routers.

    Args:
        app: FastAPI application instance
    """
    logger.info("Configuring API routers")

    # Register routers in order of priority
    app.include_router(health_router, tags=["health"])
    app.include_router(auth_router, tags=["authentication"])
    app.include_router(items_router, tags=["items"])

    logger.info("API routers registered successfully")


def configure_root_endpoints(app: FastAPI) -> None:
    """Configure root and utility endpoints.

    Args:
        app: FastAPI application instance
    """

    @app.get("/", tags=["root"], summary="API Information")
    async def root() -> dict[str, Any]:
        """Root endpoint providing API information.

        Returns basic information about the API server including version,
        available endpoints, and health check URL.

        Returns:
            Dict[str, Any]: API information
        """
        return {
            "message": "API Server is running",
            "version": "1.0.0",
            "environment": settings.environment,
            "debug": settings.debug,
            "docs": "/docs" if settings.debug else None,
            "health": "/api/health",
            "endpoints": {
                "health": "/api/health",
                "auth": "/api/auth",
                "items": "/api/items",
            },
        }

    @app.get("/version", tags=["root"], summary="API Version")
    async def version() -> dict[str, str]:
        """Get API version information.

        Returns:
            Dict[str, str]: Version information
        """
        return {"version": "1.0.0", "environment": settings.environment}

    logger.info("Root endpoints configured")


# Create the FastAPI application instance
app = create_app()

# Log application startup
logger.info(
    "FastAPI application initialized successfully",
    extra={
        "environment": settings.environment,
        "debug": settings.debug,
        "database_url": settings.database_url.split("@")[-1]
        if "@" in settings.database_url
        else settings.database_url,
    },
)
