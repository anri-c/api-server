"""Custom exception classes and global exception handlers.

This module defines custom exception classes for different error types
and provides FastAPI global exception handlers for consistent error responses
with proper HTTP status codes and error message formatting.
"""

import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base exception class for API errors.

    This is the base class for all custom API exceptions, providing
    consistent error structure and HTTP status code handling.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize API exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code for the error
            error_code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__.lower().replace(
            "exception", "_error"
        )
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(APIException):
    """Exception for input validation errors."""

    def __init__(
        self, message: str, field: str | None = None, value: Any | None = None
    ) -> None:
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="validation_error",
            details=details,
        )


class AuthenticationException(APIException):
    """Exception for authentication errors."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="authentication_error",
        )


class AuthorizationException(APIException):
    """Exception for authorization/permission errors."""

    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="authorization_error",
        )


class NotFoundException(APIException):
    """Exception for resource not found errors."""

    def __init__(
        self, resource: str, identifier: str | int, message: str | None = None
    ) -> None:
        if not message:
            message = f"{resource} with identifier '{identifier}' not found"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="not_found_error",
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictException(APIException):
    """Exception for resource conflict errors."""

    def __init__(
        self,
        message: str,
        resource: str | None = None,
        identifier: str | int | None = None,
    ) -> None:
        details = {}
        if resource:
            details["resource"] = resource
        if identifier:
            details["identifier"] = str(identifier)

        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="conflict_error",
            details=details,
        )


class BusinessLogicException(APIException):
    """Exception for business logic violations."""

    def __init__(self, message: str, rule: str | None = None) -> None:
        details = {}
        if rule:
            details["rule"] = rule

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="business_logic_error",
            details=details,
        )


class ExternalServiceException(APIException):
    """Exception for external service errors."""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="external_service_error",
            details={"service": service},
        )


class RateLimitException(APIException):
    """Exception for rate limiting errors."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ) -> None:
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="rate_limit_error",
            details=details,
        )


class DatabaseException(APIException):
    """Exception for database operation errors."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: str | None = None,
    ) -> None:
        details = {}
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="database_error",
            details=details,
        )


def create_error_response(
    status_code: int,
    message: str,
    error_code: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Create standardized error response.

    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Machine-readable error code
        details: Additional error details
        request_id: Request ID for tracking

    Returns:
        JSONResponse: Standardized error response
    """
    error_data = {
        "error": {"code": error_code, "message": message, "status_code": status_code}
    }

    if details:
        error_data["error"]["details"] = details

    if request_id:
        error_data["error"]["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=error_data)


# Global Exception Handlers


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions.

    Args:
        request: FastAPI request object
        exc: API exception instance

    Returns:
        JSONResponse: Standardized error response
    """
    # Log the error with context
    logger.error(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
        },
    )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=getattr(request.state, "request_id", None),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions.

    Args:
        request: FastAPI request object
        exc: HTTP exception instance

    Returns:
        JSONResponse: Standardized error response
    """
    # Log the error
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
        },
    )

    return create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code="http_error",
        request_id=getattr(request.state, "request_id", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: Validation error instance

    Returns:
        JSONResponse: Standardized error response with validation details
    """
    # Extract validation error details
    validation_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        validation_errors.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    # Log the validation error
    logger.warning(
        f"Validation Error: {len(validation_errors)} field(s) failed validation",
        extra={
            "validation_errors": validation_errors,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
        },
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed",
        error_code="validation_error",
        details={"validation_errors": validation_errors},
        request_id=getattr(request.state, "request_id", None),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSONResponse: Generic error response
    """
    # Log the unexpected error with full traceback
    logger.error(
        f"Unexpected Exception: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
        },
    )

    # Don't expose internal error details in production
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
        error_code="internal_error",
        request_id=getattr(request.state, "request_id", None),
    )


# Exception mapping for existing service exceptions
def map_service_exceptions() -> dict[type, type]:
    """Map existing service exceptions to new API exceptions.

    Returns:
        Dict mapping old exception types to new ones
    """
    from .services.auth_service import JWTError, LineAuthError
    from .services.item_service import (
        ItemAccessDeniedServiceError,
        ItemNotFoundServiceError,
        ItemServiceError,
        ItemValidationError,
    )

    return {
        LineAuthError: ExternalServiceException,
        JWTError: AuthenticationException,
        ItemNotFoundServiceError: NotFoundException,
        ItemAccessDeniedServiceError: AuthorizationException,
        ItemValidationError: ValidationException,
        ItemServiceError: APIException,
    }
