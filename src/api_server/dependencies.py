"""FastAPI dependencies for authentication and database access.

This module provides dependency injection functions for FastAPI endpoints,
including authentication, database sessions, and service instances.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from .config import Settings, get_settings
from .database import get_session
from .models.user import UserResponse
from .services.auth_service import AuthenticationError, AuthService, JWTError
from .services.user_service import UserService, UserServiceError


# Dependency for getting application settings
def get_app_settings() -> Settings:
    """Get application settings.

    Returns:
        Settings: Application configuration
    """
    return get_settings()


# Dependency for getting authentication service
def get_auth_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthService:
    """Get authentication service instance.

    Args:
        settings: Application settings

    Returns:
        AuthService: Authentication service instance
    """
    return AuthService(settings)


# Dependency for getting user service
def get_user_service(session: Annotated[Session, Depends(get_session)]) -> UserService:
    """Get user service instance.

    Args:
        session: Database session

    Returns:
        UserService: User service instance
    """
    return UserService(session)


# Dependency for JWT token validation
async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> int:
    """Get current user ID from JWT token.

    Args:
        authorization: Authorization header with Bearer token
        auth_service: Authentication service instance

    Returns:
        int: Current user ID

    Raises:
        HTTPException: If authentication fails
    """
    try:
        return await auth_service.get_current_user_id(authorization)
    except JWTError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Dependency for getting current user
async def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Get current authenticated user.

    Args:
        user_id: Current user ID from JWT token
        user_service: User service instance

    Returns:
        UserResponse: Current user information

    Raises:
        HTTPException: If user not found or service error
    """
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except UserServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# Optional authentication dependency (for endpoints that work with or without auth)
async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
    user_service: Annotated[UserService, Depends(get_user_service)] = None,
) -> UserResponse | None:
    """Get current user if authenticated, None otherwise.

    This dependency is useful for endpoints that provide different behavior
    for authenticated vs anonymous users.

    Args:
        authorization: Authorization header with Bearer token
        auth_service: Authentication service instance
        user_service: User service instance

    Returns:
        UserResponse if authenticated, None otherwise
    """
    if not authorization:
        return None

    try:
        user_id = await auth_service.get_current_user_id(authorization)
        user = await user_service.get_user_by_id(user_id)
        return user
    except (JWTError, AuthenticationError, UserServiceError):
        # Return None for any authentication or service errors
        # This allows the endpoint to handle anonymous users
        return None


# Dependency for validating JWT token without getting user
async def validate_token(
    authorization: Annotated[str | None, Header()] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> str:
    """Validate JWT token and return LINE user ID.

    Args:
        authorization: Authorization header with Bearer token
        auth_service: Authentication service instance

    Returns:
        str: LINE user ID from token

    Raises:
        HTTPException: If token validation fails
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_service.extract_token_from_header(authorization)
        payload = auth_service.verify_jwt_token(token)
        return payload.line_user_id

    except JWTError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Dependency for admin-only endpoints (placeholder for future use)
async def require_admin_user(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    """Require admin user for endpoint access.

    This is a placeholder for future admin functionality.
    Currently, all authenticated users are treated as regular users.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Current user if admin

    Raises:
        HTTPException: If user is not admin
    """
    # TODO: Implement admin role checking when user roles are added
    # For now, this just returns the current user
    # In the future, check user.role == "admin" or similar
    return current_user


# Type aliases for common dependency patterns
CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
CurrentUserOptional = Annotated[UserResponse | None, Depends(get_current_user_optional)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
AuthService = Annotated[AuthService, Depends(get_auth_service)]
UserService = Annotated[UserService, Depends(get_user_service)]
DatabaseSession = Annotated[Session, Depends(get_session)]
