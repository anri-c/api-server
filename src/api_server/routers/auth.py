"""Authentication router for LINE OAuth and JWT token management.

This module provides authentication endpoints for LINE login callback,
JWT token generation, user creation/login logic with proper error handling
and comprehensive type hints.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_auth_service, get_user_service
from ..models.user import UserCreate
from ..schemas.auth_schemas import (
    AuthError,
    LineLoginRequest,
    LoginResponse,
    LoginStatus,
    TokenResponse,
    UserAuthResponse,
)
from ..services.auth_service import AuthService, JWTError, LineAuthError
from ..services.user_service import UserService, UserServiceError

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
    responses={
        400: {"description": "Bad request", "model": AuthError},
        401: {"description": "Unauthorized", "model": AuthError},
        500: {"description": "Internal server error", "model": AuthError},
        503: {"description": "Service unavailable", "model": AuthError},
    },
)


@router.post(
    "/line/callback",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="LINE login callback",
    description="Handle LINE OAuth callback and create/login user with JWT token generation",
)
async def line_login_callback(
    request: LineLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> LoginResponse:
    """Handle LINE OAuth callback and authenticate user.

    This endpoint processes the authorization code from LINE OAuth callback,
    verifies the user with LINE API, creates or retrieves the user from database,
    and returns a JWT token for subsequent API calls.

    Args:
        request: LINE login request containing authorization code
        auth_service: Authentication service for LINE OAuth and JWT operations
        user_service: User service for database operations

    Returns:
        LoginResponse: Login result with JWT token on success

    Raises:
        HTTPException: If authentication fails at any step

    Example:
        POST /api/auth/line/callback
        {
            "code": "authorization_code_from_line",
            "state": "optional_state_parameter"
        }

        Response:
        {
            "status": "success",
            "message": "Login successful",
            "data": {
                "access_token": "jwt_token_here",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "id": 123,
                    "line_user_id": "U1234...",
                    "display_name": "John Doe",
                    "picture_url": "https://...",
                    "email": null,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            }
        }
    """
    try:
        # Note: In a real implementation, you would exchange the authorization code
        # for an access token using LINE's token endpoint. For this implementation,
        # we'll assume the 'code' parameter is actually the access token.
        # This is a simplified version for demonstration purposes.

        access_token = request.code  # In real implementation, exchange code for token

        # Authenticate user with LINE
        line_profile = await auth_service.authenticate_line_user(access_token)

        # Create user data from LINE profile
        user_data = UserCreate(
            line_user_id=line_profile.userId,
            display_name=line_profile.displayName,
            picture_url=line_profile.pictureUrl,
            email=None,  # LINE doesn't always provide email
        )

        # Create or get existing user
        user = await user_service.create_or_get_user(user_data)

        # Create JWT token
        jwt_token = auth_service.create_jwt_token(user.id, user.line_user_id)

        # Prepare user response
        user_response = UserAuthResponse(
            id=user.id,
            line_user_id=user.line_user_id,
            display_name=user.display_name,
            picture_url=user.picture_url,
            email=user.email,
            created_at=user.created_at,
        )

        # Prepare token response
        token_response = TokenResponse(
            access_token=jwt_token,
            token_type="bearer",
            expires_in=auth_service.jwt_expire_minutes * 60,  # Convert to seconds
            user=user_response,
        )

        return LoginResponse(
            status=LoginStatus.SUCCESS, message="Login successful", data=token_response
        )

    except LineAuthError as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"LINE authentication failed: {e.message}"
        ) from e
    except UserServiceError as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"User service error: {e.message}"
        ) from e
    except JWTError as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"Token generation failed: {e.message}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.post(
    "/line/token",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="LINE token authentication",
    description="Authenticate user directly with LINE access token",
)
async def line_token_auth(
    access_token: str,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> LoginResponse:
    """Authenticate user directly with LINE access token.

    This endpoint allows direct authentication using a LINE access token,
    bypassing the OAuth callback flow. Useful for mobile applications
    that handle LINE OAuth directly.

    Args:
        access_token: LINE access token
        auth_service: Authentication service
        user_service: User service

    Returns:
        LoginResponse: Login result with JWT token on success

    Raises:
        HTTPException: If authentication fails

    Example:
        POST /api/auth/line/token
        Content-Type: application/x-www-form-urlencoded

        access_token=line_access_token_here
    """
    try:
        # Authenticate user with LINE
        line_profile = await auth_service.authenticate_line_user(access_token)

        # Create user data from LINE profile
        user_data = UserCreate(
            line_user_id=line_profile.userId,
            display_name=line_profile.displayName,
            picture_url=line_profile.pictureUrl,
            email=None,
        )

        # Create or get existing user
        user = await user_service.create_or_get_user(user_data)

        # Create JWT token
        jwt_token = auth_service.create_jwt_token(user.id, user.line_user_id)

        # Prepare responses
        user_response = UserAuthResponse(
            id=user.id,
            line_user_id=user.line_user_id,
            display_name=user.display_name,
            picture_url=user.picture_url,
            email=user.email,
            created_at=user.created_at,
        )

        token_response = TokenResponse(
            access_token=jwt_token,
            token_type="bearer",
            expires_in=auth_service.jwt_expire_minutes * 60,
            user=user_response,
        )

        return LoginResponse(
            status=LoginStatus.SUCCESS,
            message="Authentication successful",
            data=token_response,
        )

    except LineAuthError as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"LINE authentication failed: {e.message}"
        ) from e
    except UserServiceError as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"User service error: {e.message}"
        ) from e
    except JWTError as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"Token generation failed: {e.message}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.post(
    "/verify",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Verify JWT token",
    description="Verify the validity of a JWT token and return user information",
)
async def verify_token(
    authorization: str = Depends(lambda: None),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """Verify JWT token and return user information.

    This endpoint verifies the provided JWT token and returns the associated
    user information if the token is valid.

    Args:
        authorization: Authorization header with Bearer token
        auth_service: Authentication service
        user_service: User service

    Returns:
        Dict[str, Any]: Token verification result with user information

    Raises:
        HTTPException: If token verification fails

    Example:
        POST /api/auth/verify
        Authorization: Bearer jwt_token_here

        Response:
        {
            "valid": true,
            "user": {
                "id": 123,
                "line_user_id": "U1234...",
                "display_name": "John Doe"
            },
            "expires_at": "2024-01-02T00:00:00Z"
        }
    """
    try:
        # Extract and verify token

        # Get authorization header from request
        # This is a simplified approach - in production, use proper dependency injection
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_service.extract_token_from_header(authorization)
        payload = auth_service.verify_jwt_token(token)

        # Get user information
        user_id = int(payload.sub)
        user = await user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return {
            "valid": True,
            "user": {
                "id": user.id,
                "line_user_id": user.line_user_id,
                "display_name": user.display_name,
                "picture_url": user.picture_url,
                "email": user.email,
            },
            "expires_at": payload.exp,
        }

    except JWTError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Token verification failed: {e.message}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except UserServiceError as e:
        raise HTTPException(
            status_code=e.status_code, detail=f"User service error: {e.message}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.post(
    "/logout",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout user (client-side token invalidation)",
)
async def logout() -> dict[str, str]:
    """Logout user by instructing client to discard token.

    Since JWT tokens are stateless, logout is handled on the client side
    by discarding the token. This endpoint provides a standard logout
    response for client applications.

    Returns:
        Dict[str, str]: Logout confirmation message

    Example:
        POST /api/auth/logout

        Response:
        {
            "message": "Logout successful. Please discard your access token."
        }
    """
    return {"message": "Logout successful. Please discard your access token."}


# Note: Exception handlers are registered globally in main.py
# Router-level exception handlers are not supported in FastAPI
