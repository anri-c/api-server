"""Authentication service for LINE OAuth and JWT token management.

This module provides authentication services including LINE OAuth verification,
JWT token creation and validation, with comprehensive error handling, type hints,
and security logging.
"""

from datetime import datetime, timedelta

import httpx
from jose import jwt
from pydantic import BaseModel, Field

from ..config import Settings
from ..logging_config import SecurityLoggingMixin, get_logger, log_external_api_call

logger = get_logger("auth_service")


class LineUserProfile(BaseModel):
    """LINE user profile data from API response."""

    userId: str = Field(description="LINE user ID")
    displayName: str = Field(description="User display name")
    pictureUrl: str | None = Field(default=None, description="Profile picture URL")
    statusMessage: str | None = Field(default=None, description="User status message")


class LineTokenInfo(BaseModel):
    """LINE access token information."""

    scope: str = Field(description="Token scope")
    client_id: str = Field(description="Client ID")
    expires_in: int = Field(description="Token expiration time in seconds")


class JWTPayload(BaseModel):
    """JWT token payload structure."""

    sub: str = Field(description="Subject (user ID)")
    line_user_id: str = Field(description="LINE user ID")
    exp: int = Field(description="Expiration timestamp")
    iat: int = Field(description="Issued at timestamp")


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class LineAuthError(AuthenticationError):
    """Exception for LINE authentication errors."""

    pass


class JWTError(AuthenticationError):
    """Exception for JWT token errors."""

    pass


class AuthService(SecurityLoggingMixin):
    """Authentication service for LINE OAuth and JWT management.

    This service handles LINE OAuth token verification, user profile retrieval,
    and JWT token creation and validation with comprehensive error handling
    and security logging.
    """

    LINE_PROFILE_API_URL = "https://api.line.me/v2/profile"
    LINE_TOKEN_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"

    def __init__(self, settings: Settings) -> None:
        """Initialize authentication service with configuration.

        Args:
            settings: Application settings containing LINE and JWT configuration
        """
        super().__init__()  # Initialize SecurityLoggingMixin
        self.line_client_id = settings.line_client_id
        self.line_client_secret = settings.line_client_secret
        self.jwt_secret = settings.jwt_secret
        self.jwt_algorithm = settings.jwt_algorithm
        self.jwt_expire_minutes = settings.jwt_expire_minutes

    async def verify_line_access_token(self, access_token: str) -> LineTokenInfo:
        """Verify LINE access token and get token information.

        Args:
            access_token: LINE access token to verify

        Returns:
            LineTokenInfo: Token information from LINE API

        Raises:
            LineAuthError: If token verification fails
        """
        start_time = datetime.utcnow()

        try:
            logger.debug("Starting LINE token verification")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.LINE_TOKEN_VERIFY_URL,
                    params={"access_token": access_token},
                    timeout=10.0,
                )

                duration = (datetime.utcnow() - start_time).total_seconds()

                # Log the API call
                log_external_api_call(
                    service="LINE",
                    endpoint=self.LINE_TOKEN_VERIFY_URL,
                    method="GET",
                    status_code=response.status_code,
                    duration=duration,
                    success=response.status_code == 200,
                )

                if response.status_code != 200:
                    logger.warning(
                        f"LINE token verification failed with status {response.status_code}",
                        extra={"status_code": response.status_code},
                    )
                    raise LineAuthError(
                        f"LINE token verification failed: {response.status_code}",
                        status_code=401,
                    )

                token_data = response.json()

                # Verify the client_id matches our application
                if token_data.get("client_id") != self.line_client_id:
                    logger.warning(
                        "Invalid client ID in LINE token",
                        extra={"received_client_id": token_data.get("client_id")},
                    )
                    raise LineAuthError("Invalid client ID in token", status_code=401)

                logger.info("LINE token verification successful")
                return LineTokenInfo(**token_data)

        except httpx.RequestError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_external_api_call(
                service="LINE",
                endpoint=self.LINE_TOKEN_VERIFY_URL,
                method="GET",
                duration=duration,
                success=False,
                error=str(e),
            )
            raise LineAuthError(
                f"Failed to connect to LINE API: {str(e)}", status_code=503
            ) from e
        except Exception as e:
            if isinstance(e, LineAuthError):
                raise
            logger.error(
                f"Unexpected error during token verification: {str(e)}", exc_info=True
            )
            raise LineAuthError(
                f"Unexpected error during token verification: {str(e)}", status_code=500
            ) from e

    async def get_line_user_profile(self, access_token: str) -> LineUserProfile:
        """Get LINE user profile using access token.

        Args:
            access_token: Valid LINE access token

        Returns:
            LineUserProfile: User profile data from LINE API

        Raises:
            LineAuthError: If profile retrieval fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.LINE_PROFILE_API_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )

                if response.status_code != 200:
                    raise LineAuthError(
                        f"Failed to get LINE user profile: {response.status_code}",
                        status_code=401,
                    )

                profile_data = response.json()
                return LineUserProfile(**profile_data)

        except httpx.RequestError as e:
            raise LineAuthError(
                f"Failed to connect to LINE API: {str(e)}", status_code=503
            ) from e
        except Exception as e:
            if isinstance(e, LineAuthError):
                raise
            raise LineAuthError(
                f"Unexpected error during profile retrieval: {str(e)}", status_code=500
            ) from e

    async def authenticate_line_user(self, access_token: str) -> LineUserProfile:
        """Authenticate LINE user and return profile.

        This method combines token verification and profile retrieval
        for a complete authentication flow.

        Args:
            access_token: LINE access token from client

        Returns:
            LineUserProfile: Authenticated user profile

        Raises:
            LineAuthError: If authentication fails at any step
        """
        # First verify the token
        await self.verify_line_access_token(access_token)

        # Then get user profile
        return await self.get_line_user_profile(access_token)

    def create_jwt_token(self, user_id: int, line_user_id: str) -> str:
        """Create JWT token for authenticated user.

        Args:
            user_id: Internal user ID
            line_user_id: LINE user ID

        Returns:
            str: Encoded JWT token

        Raises:
            JWTError: If token creation fails
        """
        try:
            logger.debug(
                f"Creating JWT token for user {user_id}",
                extra={"user_id": user_id, "line_user_id": line_user_id},
            )

            now = datetime.utcnow()
            expire = now + timedelta(minutes=self.jwt_expire_minutes)

            payload = JWTPayload(
                sub=str(user_id),
                line_user_id=line_user_id,
                exp=int(expire.timestamp()),
                iat=int(now.timestamp()),
            )

            token = jwt.encode(
                payload.dict(), self.jwt_secret, algorithm=self.jwt_algorithm
            )

            logger.info(
                f"JWT token created successfully for user {user_id}",
                extra={
                    "user_id": user_id,
                    "line_user_id": line_user_id,
                    "expires_at": expire.isoformat(),
                },
            )

            return token

        except Exception as e:
            logger.error(
                f"Failed to create JWT token for user {user_id}: {str(e)}",
                exc_info=True,
                extra={"user_id": user_id, "line_user_id": line_user_id},
            )
            raise JWTError(
                f"Failed to create JWT token: {str(e)}", status_code=500
            ) from e

    def verify_jwt_token(self, token: str) -> JWTPayload:
        """Verify and decode JWT token.

        Args:
            token: JWT token to verify

        Returns:
            JWTPayload: Decoded token payload

        Raises:
            JWTError: If token verification fails
        """
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            return JWTPayload(**payload)

        except jwt.ExpiredSignatureError:
            raise JWTError("Token has expired", status_code=401)
        except jwt.JWTError as e:
            raise JWTError(f"Invalid token: {str(e)}", status_code=401)
        except Exception as e:
            raise JWTError(
                f"Token verification failed: {str(e)}", status_code=500
            ) from e

    def extract_token_from_header(self, authorization: str | None) -> str:
        """Extract JWT token from Authorization header.

        Args:
            authorization: Authorization header value

        Returns:
            str: Extracted JWT token

        Raises:
            JWTError: If token extraction fails
        """
        if not authorization:
            raise JWTError("Authorization header is missing", status_code=401)

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise JWTError(
                    "Invalid authorization scheme. Expected 'Bearer'", status_code=401
                )
            return token
        except ValueError:
            raise JWTError("Invalid authorization header format", status_code=401)

    async def get_current_user_id(self, authorization: str | None) -> int:
        """Get current user ID from authorization header.

        Args:
            authorization: Authorization header value

        Returns:
            int: Current user ID

        Raises:
            JWTError: If user ID extraction fails
        """
        token = self.extract_token_from_header(authorization)
        payload = self.verify_jwt_token(token)

        try:
            return int(payload.sub)
        except ValueError:
            raise JWTError("Invalid user ID in token", status_code=401)
