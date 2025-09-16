"""Middleware for request processing and authentication.

This module provides FastAPI middleware for request/response processing,
logging, error handling, and authentication context.
"""

import time
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .services.auth_service import AuthService, JWTError, AuthenticationError
from .config import get_settings


# Configure logger
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.
    
    This middleware logs request details, response status, and processing time
    for monitoring and debugging purposes.
    """
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.
        
        Args:
            request: HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response
        """
        start_time = time.time()
        
        # Log request details
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response details
        logger.info(
            f"Response: {response.status_code} "
            f"for {request.method} {request.url.path} "
            f"in {process_time:.4f}s"
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class AuthenticationContextMiddleware(BaseHTTPMiddleware):
    """Middleware for adding authentication context to requests.
    
    This middleware extracts and validates JWT tokens from requests,
    adding user context to the request state for use by endpoints.
    It does not enforce authentication - that's handled by dependencies.
    """
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()
        self.auth_service = AuthService(self.settings)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add authentication context to request.
        
        Args:
            request: HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response
        """
        # Initialize auth context
        request.state.user_id = None
        request.state.line_user_id = None
        request.state.is_authenticated = False
        
        # Extract authorization header
        authorization = request.headers.get("authorization")
        
        if authorization:
            try:
                # Extract and validate token
                token = self.auth_service.extract_token_from_header(authorization)
                payload = self.auth_service.verify_jwt_token(token)
                
                # Add user context to request state
                request.state.user_id = int(payload.sub)
                request.state.line_user_id = payload.line_user_id
                request.state.is_authenticated = True
                
                logger.debug(f"Authenticated user: {payload.line_user_id}")
                
            except (JWTError, AuthenticationError, ValueError) as e:
                # Log authentication failure but don't block request
                # Let the endpoint dependencies handle authentication enforcement
                logger.debug(f"Authentication failed: {str(e)}")
        
        # Process request with auth context
        response = await call_next(request)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling.
    
    This middleware catches unhandled exceptions and returns
    consistent error responses with proper logging.
    """
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors and return consistent responses.
        
        Args:
            request: HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response or error response
        """
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Log the error with context
            logger.error(
                f"Unhandled error in {request.method} {request.url.path}: {str(e)}",
                exc_info=True
            )
            
            # Return generic error response
            error_detail = "Internal server error"
            status_code = 500
            
            # In development, include more error details
            if self.settings.is_development:
                error_detail = f"Internal server error: {str(e)}"
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": error_detail,
                    "type": "internal_server_error"
                }
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """Simple CORS middleware for development.
    
    This middleware adds CORS headers for cross-origin requests.
    In production, consider using FastAPI's built-in CORSMiddleware
    with more specific configuration.
    """
    
    def __init__(self, app: ASGIApp, allow_origins: Optional[list] = None) -> None:
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add CORS headers to response.
        
        Args:
            request: HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response with CORS headers
        """
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Add CORS headers
        origin = request.headers.get("origin")
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers.
    
    This middleware adds common security headers to all responses
    to improve application security posture.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response.
        
        Args:
            request: HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add CSP header for API responses
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        
        return response


# Utility function to get user context from request
def get_request_user_context(request: Request) -> dict:
    """Get user context from request state.
    
    Args:
        request: HTTP request with auth context
        
    Returns:
        dict: User context information
    """
    return {
        "user_id": getattr(request.state, "user_id", None),
        "line_user_id": getattr(request.state, "line_user_id", None),
        "is_authenticated": getattr(request.state, "is_authenticated", False),
    }


# Utility function to check if request is authenticated
def is_request_authenticated(request: Request) -> bool:
    """Check if request is authenticated.
    
    Args:
        request: HTTP request with auth context
        
    Returns:
        bool: True if request is authenticated
    """
    return getattr(request.state, "is_authenticated", False)