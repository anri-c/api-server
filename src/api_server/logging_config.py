"""Logging configuration for structured logging.

This module provides structured logging configuration with proper log levels,
request/response logging middleware, error logging with context information,
and configurable log formatting and output destinations.
"""

import json
import logging
import logging.config
import sys
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .config import Settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.

    This formatter outputs log records as JSON objects with consistent
    structure including timestamp, level, message, and additional context.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON formatted log string
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
                if record.exc_info
                else None,
            }

        # Add extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
                "message",
            }:
                extra_fields[key] = value

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """Logging filter to add request context to log records.

    This filter adds request-specific information like request ID,
    client IP, and user ID to log records when available.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record.

        Args:
            record: Log record to modify

        Returns:
            True to allow the record to be logged
        """
        # Try to get request context from contextvars or thread-local storage
        # This is a simplified implementation - in production you might use
        # contextvars for proper async context handling

        # Add default values
        record.request_id = getattr(record, "request_id", None)
        record.client_ip = getattr(record, "client_ip", None)
        record.user_id = getattr(record, "user_id", None)
        record.path = getattr(record, "path", None)
        record.method = getattr(record, "method", None)

        return True


def setup_logging(settings: Settings) -> None:
    """Setup logging configuration based on settings.

    Args:
        settings: Application settings containing logging configuration
    """
    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "filters": {
            "request_context": {
                "()": RequestContextFilter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if not settings.debug else "simple",
                "filters": ["request_context"],
                "stream": sys.stdout,
            }
        },
        "loggers": {
            # Application loggers
            "api_server": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # FastAPI and Uvicorn loggers
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {
                "level": "INFO" if settings.debug else "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Database loggers
            "sqlalchemy.engine": {
                "level": "INFO" if settings.debug else "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.pool": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            # HTTP client loggers
            "httpx": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "httpcore": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {"level": "WARNING", "handlers": ["console"]},
    }

    # Apply logging configuration
    logging.config.dictConfig(logging_config)

    # Set up application logger
    logger = logging.getLogger("api_server")
    logger.info(
        "Logging configured",
        extra={
            "log_level": settings.log_level,
            "debug_mode": settings.debug,
            "formatter": "json" if not settings.debug else "simple",
        },
    )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging.

    This middleware logs incoming requests and outgoing responses with
    timing information, status codes, and request context.
    """

    def __init__(self, app: ASGIApp, logger_name: str = "api_server.requests") -> None:
        """Initialize logging middleware.

        Args:
            app: ASGI application
            logger_name: Name of the logger to use
        """
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log request/response information.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response from the application
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract client information
        client_ip = None
        if request.client:
            client_ip = request.client.host

        # Get forwarded IP if behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Start timing
        start_time = time.time()

        # Log incoming request
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": request.headers.get("User-Agent"),
                "content_type": request.headers.get("Content-Type"),
                "content_length": request.headers.get("Content-Length"),
                "event_type": "request_started",
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log successful response
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4),
                    "client_ip": client_ip,
                    "response_size": response.headers.get("Content-Length"),
                    "event_type": "request_completed",
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Calculate processing time
            process_time = time.time() - start_time

            # Log error response
            self.logger.error(
                f"Request failed: {request.method} {request.url.path} - {type(exc).__name__}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "process_time": round(process_time, 4),
                    "client_ip": client_ip,
                    "event_type": "request_failed",
                },
            )

            # Re-raise the exception
            raise


class SecurityLoggingMixin:
    """Mixin for security-related logging.

    This mixin provides methods for logging security events like
    authentication attempts, authorization failures, and suspicious activity.
    """

    def __init__(self) -> None:
        self.security_logger = logging.getLogger("api_server.security")

    def log_authentication_attempt(
        self,
        user_id: str | None = None,
        line_user_id: str | None = None,
        success: bool = True,
        reason: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log authentication attempt.

        Args:
            user_id: Internal user ID
            line_user_id: LINE user ID
            success: Whether authentication was successful
            reason: Reason for failure (if applicable)
            client_ip: Client IP address
            user_agent: Client user agent
        """
        level = logging.INFO if success else logging.WARNING
        message = (
            "Authentication successful"
            if success
            else f"Authentication failed: {reason}"
        )

        self.security_logger.log(
            level,
            message,
            extra={
                "event_type": "authentication_attempt",
                "user_id": user_id,
                "line_user_id": line_user_id,
                "success": success,
                "reason": reason,
                "client_ip": client_ip,
                "user_agent": user_agent,
            },
        )

    def log_authorization_failure(
        self,
        user_id: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        reason: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        """Log authorization failure.

        Args:
            user_id: User ID attempting access
            resource: Resource being accessed
            action: Action being attempted
            reason: Reason for denial
            client_ip: Client IP address
        """
        self.security_logger.warning(
            f"Authorization denied: {reason}",
            extra={
                "event_type": "authorization_failure",
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "reason": reason,
                "client_ip": client_ip,
            },
        )

    def log_suspicious_activity(
        self,
        activity_type: str,
        description: str,
        user_id: str | None = None,
        client_ip: str | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Log suspicious activity.

        Args:
            activity_type: Type of suspicious activity
            description: Description of the activity
            user_id: User ID (if known)
            client_ip: Client IP address
            additional_data: Additional context data
        """
        extra_data = {
            "event_type": "suspicious_activity",
            "activity_type": activity_type,
            "user_id": user_id,
            "client_ip": client_ip,
        }

        if additional_data:
            extra_data.update(additional_data)

        self.security_logger.warning(
            f"Suspicious activity detected: {description}", extra=extra_data
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name (should start with 'api_server.')

    Returns:
        Logger instance
    """
    if not name.startswith("api_server."):
        name = f"api_server.{name}"

    return logging.getLogger(name)


# Convenience functions for common logging patterns


def log_database_operation(
    operation: str,
    table: str,
    success: bool = True,
    duration: float | None = None,
    error: str | None = None,
    **kwargs,
) -> None:
    """Log database operation.

    Args:
        operation: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        table: Database table name
        success: Whether operation was successful
        duration: Operation duration in seconds
        error: Error message (if applicable)
        **kwargs: Additional context data
    """
    logger = get_logger("database")
    level = logging.INFO if success else logging.ERROR
    message = f"Database {operation} on {table}"

    if not success and error:
        message += f" failed: {error}"

    extra_data = {
        "event_type": "database_operation",
        "operation": operation,
        "table": table,
        "success": success,
        "duration": duration,
    }

    if error:
        extra_data["error"] = error

    extra_data.update(kwargs)

    logger.log(level, message, extra=extra_data)


def log_external_api_call(
    service: str,
    endpoint: str,
    method: str = "GET",
    status_code: int | None = None,
    duration: float | None = None,
    success: bool = True,
    error: str | None = None,
    **kwargs,
) -> None:
    """Log external API call.

    Args:
        service: External service name
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        duration: Request duration in seconds
        success: Whether request was successful
        error: Error message (if applicable)
        **kwargs: Additional context data
    """
    logger = get_logger("external_api")
    level = logging.INFO if success else logging.ERROR
    message = f"External API call to {service}: {method} {endpoint}"

    if status_code:
        message += f" - {status_code}"

    if not success and error:
        message += f" failed: {error}"

    extra_data = {
        "event_type": "external_api_call",
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "duration": duration,
        "success": success,
    }

    if error:
        extra_data["error"] = error

    extra_data.update(kwargs)

    logger.log(level, message, extra=extra_data)
