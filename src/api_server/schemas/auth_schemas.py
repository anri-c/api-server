"""Authentication schemas for LINE login and JWT token handling.

This module defines Pydantic schemas for authentication-related API operations,
including LINE login requests/responses, JWT token handling, and user authentication data.
All schemas include comprehensive validation rules and proper type hints.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator, EmailStr
from enum import Enum


class LineLoginRequest(BaseModel):
    """Schema for LINE login callback request.
    
    This schema validates the authorization code received from LINE's OAuth callback.
    """
    
    code: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Authorization code from LINE OAuth callback",
        example="abc123def456"
    )
    state: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional state parameter for CSRF protection",
        example="random_state_string"
    )
    
    @validator('code')
    def validate_code(cls, v: str) -> str:
        """Validate authorization code format."""
        if not v or v.isspace():
            raise ValueError('Authorization code cannot be empty or whitespace')
        return v.strip()


class LineUserProfile(BaseModel):
    """Schema for LINE user profile data.
    
    This schema represents user profile information received from LINE API.
    """
    
    userId: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="LINE user ID",
        example="U1234567890abcdef1234567890abcdef"
    )
    displayName: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="User's display name",
        example="John Doe"
    )
    pictureUrl: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL to user's profile picture",
        example="https://profile.line-scdn.net/..."
    )
    statusMessage: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User's status message"
    )
    
    @validator('userId')
    def validate_user_id(cls, v: str) -> str:
        """Validate LINE user ID format."""
        if not v or v.isspace():
            raise ValueError('LINE user ID cannot be empty')
        return v.strip()
    
    @validator('displayName')
    def validate_display_name(cls, v: str) -> str:
        """Validate display name."""
        if not v or v.isspace():
            raise ValueError('Display name cannot be empty')
        return v.strip()
    
    @validator('pictureUrl')
    def validate_picture_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate picture URL format."""
        if v is not None:
            v = v.strip()
            if not v.startswith(('http://', 'https://')):
                raise ValueError('Picture URL must be a valid HTTP/HTTPS URL')
        return v


class TokenType(str, Enum):
    """Enumeration for token types."""
    BEARER = "bearer"


class TokenResponse(BaseModel):
    """Schema for JWT token response.
    
    This schema is returned after successful authentication,
    containing the JWT access token and related information.
    """
    
    access_token: str = Field(
        ...,
        min_length=1,
        description="JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: TokenType = Field(
        default=TokenType.BEARER,
        description="Token type (always 'bearer')",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        gt=0,
        description="Token expiration time in seconds",
        example=86400
    )
    user: "UserAuthResponse" = Field(
        ...,
        description="Authenticated user information"
    )
    
    @validator('access_token')
    def validate_access_token(cls, v: str) -> str:
        """Validate access token format."""
        if not v or v.isspace():
            raise ValueError('Access token cannot be empty')
        return v.strip()


class UserAuthResponse(BaseModel):
    """Schema for user information in authentication responses.
    
    This schema provides essential user information after successful authentication.
    """
    
    id: int = Field(
        ...,
        gt=0,
        description="User database ID",
        example=123
    )
    line_user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="LINE user ID",
        example="U1234567890abcdef1234567890abcdef"
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="User's display name",
        example="John Doe"
    )
    picture_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL to user's profile picture",
        example="https://profile.line-scdn.net/..."
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="User's email address",
        example="john.doe@example.com"
    )
    created_at: datetime = Field(
        ...,
        description="User creation timestamp",
        example="2024-01-01T00:00:00Z"
    )
    
    @validator('display_name')
    def validate_display_name(cls, v: str) -> str:
        """Validate display name."""
        if not v or v.isspace():
            raise ValueError('Display name cannot be empty')
        return v.strip()


class JWTPayload(BaseModel):
    """Schema for JWT token payload.
    
    This schema defines the structure of data stored in JWT tokens.
    """
    
    sub: str = Field(
        ...,
        description="Subject (user ID)",
        example="123"
    )
    line_user_id: str = Field(
        ...,
        description="LINE user ID",
        example="U1234567890abcdef1234567890abcdef"
    )
    exp: int = Field(
        ...,
        description="Expiration timestamp",
        example=1704067200
    )
    iat: int = Field(
        ...,
        description="Issued at timestamp",
        example=1703980800
    )
    
    @validator('sub')
    def validate_subject(cls, v: str) -> str:
        """Validate JWT subject."""
        if not v or v.isspace():
            raise ValueError('JWT subject cannot be empty')
        return v.strip()


class AuthError(BaseModel):
    """Schema for authentication error responses.
    
    This schema provides structured error information for authentication failures.
    """
    
    error: str = Field(
        ...,
        description="Error code",
        example="invalid_token"
    )
    error_description: str = Field(
        ...,
        description="Human-readable error description",
        example="The provided token is invalid or expired"
    )
    
    @validator('error')
    def validate_error(cls, v: str) -> str:
        """Validate error code."""
        if not v or v.isspace():
            raise ValueError('Error code cannot be empty')
        return v.strip()
    
    @validator('error_description')
    def validate_error_description(cls, v: str) -> str:
        """Validate error description."""
        if not v or v.isspace():
            raise ValueError('Error description cannot be empty')
        return v.strip()


class LoginStatus(str, Enum):
    """Enumeration for login status."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class LoginResponse(BaseModel):
    """Schema for login operation response.
    
    This schema provides the result of a login attempt with status and optional data.
    """
    
    status: LoginStatus = Field(
        ...,
        description="Login operation status",
        example=LoginStatus.SUCCESS
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Status message",
        example="Login successful"
    )
    data: Optional[TokenResponse] = Field(
        default=None,
        description="Token data (only present on successful login)"
    )
    
    @validator('message')
    def validate_message(cls, v: str) -> str:
        """Validate status message."""
        if not v or v.isspace():
            raise ValueError('Status message cannot be empty')
        return v.strip()


# Update forward references
TokenResponse.model_rebuild()
UserAuthResponse.model_rebuild()
