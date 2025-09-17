"""Unit tests for UserService.

This module contains comprehensive unit tests for the UserService class,
including user management operations and error handling.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlmodel import Session

from src.api_server.models.user import User, UserResponse, UserUpdate
from src.api_server.repositories.user_repository import (
    UserRepository,
    UserRepositoryError,
)
from src.api_server.services.auth_service import LineUserProfile
from src.api_server.services.user_service import UserService, UserServiceError


class TestUserService:
    """Test cases for UserService."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def user_service(self, mock_session: Mock) -> UserService:
        """Create UserService instance for testing."""
        service = UserService(mock_session)
        return service

    @pytest.fixture
    def sample_user(self) -> User:
        """Create sample user for testing."""
        return User(
            id=1,
            line_user_id="test_line_user_123",
            display_name="Test User",
            picture_url="https://example.com/profile.jpg",
            email="test@example.com",
        )

    @pytest.fixture
    def sample_line_profile(self) -> LineUserProfile:
        """Create sample LINE profile for testing."""
        return LineUserProfile(
            userId="test_line_user_123",
            displayName="Test User",
            pictureUrl="https://example.com/profile.jpg",
            statusMessage="Hello!",
        )

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(
        self, user_service: UserService, mock_repository: Mock, sample_user: User
    ):
        """Test successful user retrieval by ID."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.get_by_id = AsyncMock(return_value=sample_user)

        # Test user retrieval
        result = await user_service.get_user_by_id(1)

        # Assertions
        assert result is not None
        assert isinstance(result, UserResponse)
        assert result.id == sample_user.id
        assert result.line_user_id == sample_user.line_user_id
        assert result.display_name == sample_user.display_name

        # Verify repository call
        mock_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test user retrieval by ID when user not found."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.get_by_id = AsyncMock(return_value=None)

        # Test user retrieval
        result = await user_service.get_user_by_id(999)

        # Assertions
        assert result is None
        mock_repository.get_by_id.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_get_user_by_id_repository_error(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test user retrieval by ID with repository error."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.get_by_id = AsyncMock(
            side_effect=UserRepositoryError("Database error")
        )

        # Test user retrieval with error
        with pytest.raises(UserServiceError) as exc_info:
            await user_service.get_user_by_id(1)

        assert exc_info.value.status_code == 500
        assert "Failed to get user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_by_line_id_success(
        self, user_service: UserService, mock_repository: Mock, sample_user: User
    ):
        """Test successful user retrieval by LINE ID."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.get_by_line_user_id = AsyncMock(return_value=sample_user)

        # Test user retrieval
        result = await user_service.get_user_by_line_id("test_line_user_123")

        # Assertions
        assert result is not None
        assert isinstance(result, UserResponse)
        assert result.line_user_id == sample_user.line_user_id

        # Verify repository call
        mock_repository.get_by_line_user_id.assert_called_once_with(
            "test_line_user_123"
        )

    @pytest.mark.asyncio
    async def test_create_user_from_line_profile_new_user(
        self,
        user_service: UserService,
        mock_repository: Mock,
        sample_line_profile: LineUserProfile,
        sample_user: User,
    ):
        """Test creating new user from LINE profile."""
        # Setup mocks
        user_service.repository = mock_repository
        mock_repository.get_by_line_user_id = AsyncMock(return_value=None)
        mock_repository.create = AsyncMock(return_value=sample_user)

        # Test user creation
        result = await user_service.create_user_from_line_profile(sample_line_profile)

        # Assertions
        assert result is not None
        assert isinstance(result, UserResponse)
        assert result.line_user_id == sample_line_profile.userId
        assert result.display_name == sample_line_profile.displayName

        # Verify repository calls
        mock_repository.get_by_line_user_id.assert_called_once_with(
            sample_line_profile.userId
        )
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_from_line_profile_existing_user(
        self,
        user_service: UserService,
        mock_repository: Mock,
        sample_line_profile: LineUserProfile,
        sample_user: User,
    ):
        """Test creating user from LINE profile when user already exists."""
        # Setup mock to return existing user
        user_service.repository = mock_repository
        mock_repository.get_by_line_user_id = AsyncMock(return_value=sample_user)

        # Test user creation with existing user
        result = await user_service.create_user_from_line_profile(sample_line_profile)

        # Assertions
        assert result is not None
        assert isinstance(result, UserResponse)
        assert result.line_user_id == sample_user.line_user_id

        # Verify only get was called, not create
        mock_repository.get_by_line_user_id.assert_called_once_with(
            sample_line_profile.userId
        )
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_from_line_profile_repository_error(
        self,
        user_service: UserService,
        mock_repository: Mock,
        sample_line_profile: LineUserProfile,
    ):
        """Test creating user from LINE profile with repository error."""
        # Setup mocks
        user_service.repository = mock_repository
        mock_repository.get_by_line_user_id = AsyncMock(return_value=None)
        mock_repository.create = AsyncMock(
            side_effect=UserRepositoryError("Database error")
        )

        # Test user creation with error
        with pytest.raises(UserServiceError) as exc_info:
            await user_service.create_user_from_line_profile(sample_line_profile)

        assert exc_info.value.status_code == 500
        assert "Failed to create user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_success(
        self, user_service: UserService, mock_repository: Mock, sample_user: User
    ):
        """Test successful user update."""
        # Setup mock
        user_service.repository = mock_repository
        updated_user = User(**sample_user.dict())
        updated_user.display_name = "Updated Name"
        mock_repository.update = AsyncMock(return_value=updated_user)

        # Test user update
        update_data = UserUpdate(display_name="Updated Name")
        result = await user_service.update_user(1, update_data)

        # Assertions
        assert result is not None
        assert isinstance(result, UserResponse)
        assert result.display_name == "Updated Name"

        # Verify repository call
        mock_repository.update.assert_called_once_with(1, update_data)

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test user update when user not found."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.update = AsyncMock(return_value=None)

        # Test user update
        update_data = UserUpdate(display_name="Updated Name")
        result = await user_service.update_user(999, update_data)

        # Assertions
        assert result is None
        mock_repository.update.assert_called_once_with(999, update_data)

    @pytest.mark.asyncio
    async def test_update_user_empty_data(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test user update with empty update data."""
        # Setup mock
        user_service.repository = mock_repository

        # Test user update with empty data
        update_data = UserUpdate()
        with pytest.raises(UserServiceError) as exc_info:
            await user_service.update_user(1, update_data)

        assert exc_info.value.status_code == 400
        assert "No valid fields provided for update" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test successful user deletion."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.delete = AsyncMock(return_value=True)

        # Test user deletion
        result = await user_service.delete_user(1)

        # Assertions
        assert result is True
        mock_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test user deletion when user not found."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.delete = AsyncMock(return_value=False)

        # Test user deletion
        result = await user_service.delete_user(999)

        # Assertions
        assert result is False
        mock_repository.delete.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_get_all_users_success(
        self, user_service: UserService, mock_repository: Mock, sample_user: User
    ):
        """Test successful retrieval of all users."""
        # Setup mock
        user_service.repository = mock_repository
        users = [sample_user]
        mock_repository.get_all = AsyncMock(return_value=users)

        # Test get all users
        result = await user_service.get_all_users(limit=10, offset=0)

        # Assertions
        assert len(result) == 1
        assert all(isinstance(user, UserResponse) for user in result)
        assert result[0].id == sample_user.id

        # Verify repository call
        mock_repository.get_all.assert_called_once_with(limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_get_all_users_invalid_limit(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test get all users with invalid limit."""
        # Setup mock
        user_service.repository = mock_repository

        # Test with invalid limit
        with pytest.raises(UserServiceError) as exc_info:
            await user_service.get_all_users(limit=0)

        assert exc_info.value.status_code == 400
        assert "Limit must be between 1 and 1000" in str(exc_info.value)

        # Test with limit too high
        with pytest.raises(UserServiceError) as exc_info:
            await user_service.get_all_users(limit=1001)

        assert exc_info.value.status_code == 400
        assert "Limit must be between 1 and 1000" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_all_users_invalid_offset(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test get all users with invalid offset."""
        # Setup mock
        user_service.repository = mock_repository

        # Test with negative offset
        with pytest.raises(UserServiceError) as exc_info:
            await user_service.get_all_users(offset=-1)

        assert exc_info.value.status_code == 400
        assert "Offset must be non-negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_user_exists_true(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test user existence check when user exists."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.exists_by_line_user_id = AsyncMock(return_value=True)

        # Test user existence
        result = await user_service.user_exists("test_line_user_123")

        # Assertions
        assert result is True
        mock_repository.exists_by_line_user_id.assert_called_once_with(
            "test_line_user_123"
        )

    @pytest.mark.asyncio
    async def test_user_exists_false(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test user existence check when user doesn't exist."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.exists_by_line_user_id = AsyncMock(return_value=False)

        # Test user existence
        result = await user_service.user_exists("nonexistent_user")

        # Assertions
        assert result is False
        mock_repository.exists_by_line_user_id.assert_called_once_with(
            "nonexistent_user"
        )

    @pytest.mark.asyncio
    async def test_get_user_count_success(
        self, user_service: UserService, mock_repository: Mock
    ):
        """Test successful user count retrieval."""
        # Setup mock
        user_service.repository = mock_repository
        mock_repository.count = AsyncMock(return_value=5)

        # Test user count
        result = await user_service.get_user_count()

        # Assertions
        assert result == 5
        mock_repository.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(
        self,
        user_service: UserService,
        mock_repository: Mock,
        sample_line_profile: LineUserProfile,
        sample_user: User,
    ):
        """Test get or create user when user already exists."""
        # Setup mock to return existing user
        user_service.repository = mock_repository
        mock_repository.get_by_line_user_id = AsyncMock(return_value=sample_user)

        # Test get or create user
        result = await user_service.get_or_create_user_from_line_profile(
            sample_line_profile
        )

        # Assertions
        assert result is not None
        assert isinstance(result, UserResponse)
        assert result.line_user_id == sample_user.line_user_id

        # Verify only get was called, not create
        mock_repository.get_by_line_user_id.assert_called_once_with(
            sample_line_profile.userId
        )
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(
        self,
        user_service: UserService,
        mock_repository: Mock,
        sample_line_profile: LineUserProfile,
        sample_user: User,
    ):
        """Test get or create user when creating new user."""
        # Setup mocks
        user_service.repository = mock_repository
        mock_repository.get_by_line_user_id = AsyncMock(return_value=None)
        mock_repository.create = AsyncMock(return_value=sample_user)

        # Test get or create user
        result = await user_service.get_or_create_user_from_line_profile(
            sample_line_profile
        )

        # Assertions
        assert result is not None
        assert isinstance(result, UserResponse)
        assert result.line_user_id == sample_line_profile.userId

        # Verify both get and create were called
        mock_repository.get_by_line_user_id.assert_called_once_with(
            sample_line_profile.userId
        )
        mock_repository.create.assert_called_once()


class TestUserServiceError:
    """Test cases for UserServiceError exception."""

    def test_user_service_error_creation(self):
        """Test UserServiceError creation."""
        original_error = Exception("Original error")
        error = UserServiceError("Service error", 400, original_error)

        assert error.message == "Service error"
        assert error.status_code == 400
        assert error.original_error == original_error
        assert str(error) == "Service error"

    def test_user_service_error_defaults(self):
        """Test UserServiceError with default values."""
        error = UserServiceError("Service error")

        assert error.message == "Service error"
        assert error.status_code == 400
        assert error.original_error is None
