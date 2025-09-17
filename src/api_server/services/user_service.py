"""User service for business logic operations.

This module provides business logic for user management operations,
including user creation, retrieval, and updates with proper validation.
"""

from sqlmodel import Session

from ..models.user import UserCreate, UserResponse, UserUpdate
from ..repositories.user_repository import (
    UserAlreadyExistsError,
    UserRepository,
    UserRepositoryError,
)
from ..services.auth_service import LineUserProfile


class UserServiceError(Exception):
    """Base exception for user service errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        original_error: Exception | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.original_error = original_error
        super().__init__(self.message)


class UserService:
    """Service for user business logic operations.

    This service provides business logic for user management,
    including validation, transformation, and coordination with repositories.
    """

    def __init__(self, session: Session) -> None:
        """Initialize user service with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session
        self.repository = UserRepository(session)

    async def get_user_by_id(self, user_id: int) -> UserResponse | None:
        """Get user by ID.

        Args:
            user_id: User ID to search for

        Returns:
            UserResponse if found, None otherwise

        Raises:
            UserServiceError: If operation fails
        """
        try:
            user = await self.repository.get_by_id(user_id)
            if not user:
                return None

            return UserResponse(
                id=user.id,
                line_user_id=user.line_user_id,
                display_name=user.display_name,
                picture_url=user.picture_url,
                email=user.email,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to get user: {e.message}", status_code=500, original_error=e
            ) from e

    async def get_user_by_line_id(self, line_user_id: str) -> UserResponse | None:
        """Get user by LINE user ID.

        Args:
            line_user_id: LINE user ID to search for

        Returns:
            UserResponse if found, None otherwise

        Raises:
            UserServiceError: If operation fails
        """
        try:
            user = await self.repository.get_by_line_user_id(line_user_id)
            if not user:
                return None

            return UserResponse(
                id=user.id,
                line_user_id=user.line_user_id,
                display_name=user.display_name,
                picture_url=user.picture_url,
                email=user.email,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to get user by LINE ID: {e.message}",
                status_code=500,
                original_error=e,
            ) from e

    async def create_user_from_line_profile(
        self, profile: LineUserProfile
    ) -> UserResponse:
        """Create user from LINE profile data.

        Args:
            profile: LINE user profile data

        Returns:
            Created user response

        Raises:
            UserServiceError: If user creation fails
        """
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_line_id(profile.userId)
            if existing_user:
                return existing_user

            # Create user data from LINE profile
            user_data = UserCreate(
                line_user_id=profile.userId,
                display_name=profile.displayName,
                picture_url=profile.pictureUrl,
                email=None,  # LINE profile doesn't always include email
            )

            # Create user
            user = await self.repository.create(user_data)

            return UserResponse(
                id=user.id,
                line_user_id=user.line_user_id,
                display_name=user.display_name,
                picture_url=user.picture_url,
                email=user.email,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

        except UserAlreadyExistsError as e:
            # This shouldn't happen due to the check above, but handle it gracefully
            existing_user = await self.get_user_by_line_id(profile.userId)
            if existing_user:
                return existing_user
            raise UserServiceError(
                f"User creation failed: {e.message}", status_code=409, original_error=e
            ) from e
        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to create user: {e.message}", status_code=500, original_error=e
            ) from e

    async def update_user(
        self, user_id: int, user_data: UserUpdate
    ) -> UserResponse | None:
        """Update user information.

        Args:
            user_id: ID of user to update
            user_data: Updated user data

        Returns:
            Updated user response if found, None otherwise

        Raises:
            UserServiceError: If update operation fails
        """
        try:
            # Validate update data
            if not any(user_data.dict(exclude_unset=True).values()):
                raise UserServiceError(
                    "No valid fields provided for update", status_code=400
                )

            user = await self.repository.update(user_id, user_data)
            if not user:
                return None

            return UserResponse(
                id=user.id,
                line_user_id=user.line_user_id,
                display_name=user.display_name,
                picture_url=user.picture_url,
                email=user.email,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to update user: {e.message}", status_code=500, original_error=e
            ) from e

    async def delete_user(self, user_id: int) -> bool:
        """Delete user by ID.

        Args:
            user_id: ID of user to delete

        Returns:
            True if user was deleted, False if not found

        Raises:
            UserServiceError: If delete operation fails
        """
        try:
            return await self.repository.delete(user_id)
        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to delete user: {e.message}", status_code=500, original_error=e
            ) from e

    async def get_all_users(
        self, limit: int = 100, offset: int = 0
    ) -> list[UserResponse]:
        """Get all users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of user responses

        Raises:
            UserServiceError: If operation fails
        """
        try:
            # Validate pagination parameters
            if limit <= 0 or limit > 1000:
                raise UserServiceError(
                    "Limit must be between 1 and 1000", status_code=400
                )

            if offset < 0:
                raise UserServiceError("Offset must be non-negative", status_code=400)

            users = await self.repository.get_all(limit=limit, offset=offset)

            return [
                UserResponse(
                    id=user.id,
                    line_user_id=user.line_user_id,
                    display_name=user.display_name,
                    picture_url=user.picture_url,
                    email=user.email,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
                for user in users
            ]

        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to get users: {e.message}", status_code=500, original_error=e
            ) from e

    async def user_exists(self, line_user_id: str) -> bool:
        """Check if user exists by LINE user ID.

        Args:
            line_user_id: LINE user ID to check

        Returns:
            True if user exists, False otherwise

        Raises:
            UserServiceError: If operation fails
        """
        try:
            return await self.repository.exists_by_line_user_id(line_user_id)
        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to check user existence: {e.message}",
                status_code=500,
                original_error=e,
            ) from e

    async def get_user_count(self) -> int:
        """Get total count of users.

        Returns:
            Total number of users

        Raises:
            UserServiceError: If operation fails
        """
        try:
            return await self.repository.count()
        except UserRepositoryError as e:
            raise UserServiceError(
                f"Failed to count users: {e.message}", status_code=500, original_error=e
            ) from e

    async def get_or_create_user_from_line_profile(
        self, profile: LineUserProfile
    ) -> UserResponse:
        """Get existing user or create new user from LINE profile.

        This is a convenience method that combines user lookup and creation
        for the authentication flow.

        Args:
            profile: LINE user profile data

        Returns:
            User response (existing or newly created)

        Raises:
            UserServiceError: If operation fails
        """
        # Try to get existing user first
        existing_user = await self.get_user_by_line_id(profile.userId)
        if existing_user:
            return existing_user

        # Create new user if not found
        return await self.create_user_from_line_profile(profile)
