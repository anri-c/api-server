"""Unit tests for UserRepository.

This module contains comprehensive unit tests for the UserRepository class,
including database operations and error handling.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from src.api_server.models.user import User, UserCreate, UserUpdate
from src.api_server.repositories.user_repository import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserRepository,
    UserRepositoryError,
)


class TestUserRepository:
    """Test cases for UserRepository."""

    @pytest.fixture
    def user_repository(self, test_session: Session) -> UserRepository:
        """Create UserRepository instance for testing."""
        return UserRepository(test_session)

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test successful user retrieval by ID."""
        result = await user_repository.get_by_id(test_user.id)

        assert result is not None
        assert result.id == test_user.id
        assert result.line_user_id == test_user.line_user_id
        assert result.display_name == test_user.display_name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repository: UserRepository):
        """Test user retrieval by ID when user not found."""
        result = await user_repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(self, user_repository: UserRepository):
        """Test user retrieval by ID with database error."""
        with patch.object(user_repository.session, "exec") as mock_exec:
            mock_exec.side_effect = SQLAlchemyError("Database error")

            with pytest.raises(UserRepositoryError) as exc_info:
                await user_repository.get_by_id(1)

            assert "Failed to get user by ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_line_user_id_success(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test successful user retrieval by LINE user ID."""
        result = await user_repository.get_by_line_user_id(test_user.line_user_id)

        assert result is not None
        assert result.line_user_id == test_user.line_user_id
        assert result.display_name == test_user.display_name

    @pytest.mark.asyncio
    async def test_get_by_line_user_id_not_found(self, user_repository: UserRepository):
        """Test user retrieval by LINE user ID when user not found."""
        result = await user_repository.get_by_line_user_id("nonexistent_line_user")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_success(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test successful user retrieval by email."""
        if test_user.email:
            result = await user_repository.get_by_email(test_user.email)

            assert result is not None
            assert result.email == test_user.email
            assert result.line_user_id == test_user.line_user_id

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, user_repository: UserRepository):
        """Test user retrieval by email when user not found."""
        result = await user_repository.get_by_email("nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_success(
        self, user_repository: UserRepository, multiple_test_users: list[User]
    ):
        """Test successful retrieval of all users."""
        result = await user_repository.get_all(limit=10, offset=0)

        assert len(result) == len(multiple_test_users)
        assert all(isinstance(user, User) for user in result)

        # Verify users are returned
        line_user_ids = [user.line_user_id for user in result]
        for test_user in multiple_test_users:
            assert test_user.line_user_id in line_user_ids

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(
        self, user_repository: UserRepository, multiple_test_users: list[User]
    ):
        """Test retrieval of all users with pagination."""
        # Get first page
        result_page1 = await user_repository.get_all(limit=2, offset=0)
        assert len(result_page1) == 2

        # Get second page
        result_page2 = await user_repository.get_all(limit=2, offset=2)
        assert len(result_page2) == 1  # Only 3 users total

        # Verify no overlap
        page1_ids = [user.id for user in result_page1]
        page2_ids = [user.id for user in result_page2]
        assert not set(page1_ids).intersection(set(page2_ids))

    @pytest.mark.asyncio
    async def test_create_success(
        self, user_repository: UserRepository, sample_user_data: UserCreate
    ):
        """Test successful user creation."""
        # Modify sample data to avoid conflicts
        sample_user_data.line_user_id = "new_test_user_123"
        sample_user_data.email = "new_test@example.com"

        result = await user_repository.create(sample_user_data)

        assert result is not None
        assert result.id is not None
        assert result.line_user_id == sample_user_data.line_user_id
        assert result.display_name == sample_user_data.display_name
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_create_duplicate_line_user_id(
        self,
        user_repository: UserRepository,
        test_user: User,
        sample_user_data: UserCreate,
    ):
        """Test user creation with duplicate LINE user ID."""
        # Use same LINE user ID as existing user
        sample_user_data.line_user_id = test_user.line_user_id

        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await user_repository.create(sample_user_data)

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_database_error(
        self, user_repository: UserRepository, sample_user_data: UserCreate
    ):
        """Test user creation with database error."""
        with patch.object(user_repository.session, "add") as mock_add:
            mock_add.side_effect = SQLAlchemyError("Database error")

            with pytest.raises(UserRepositoryError) as exc_info:
                await user_repository.create(sample_user_data)

            assert "Failed to create user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_success(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test successful user update."""
        update_data = UserUpdate(
            display_name="Updated Name", email="updated@example.com"
        )

        result = await user_repository.update(test_user.id, update_data)

        assert result is not None
        assert result.id == test_user.id
        assert result.display_name == "Updated Name"
        assert result.email == "updated@example.com"
        assert result.line_user_id == test_user.line_user_id  # Unchanged

    @pytest.mark.asyncio
    async def test_update_partial(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test partial user update."""
        original_email = test_user.email
        update_data = UserUpdate(display_name="Partially Updated Name")

        result = await user_repository.update(test_user.id, update_data)

        assert result is not None
        assert result.display_name == "Partially Updated Name"
        assert result.email == original_email  # Unchanged

    @pytest.mark.asyncio
    async def test_update_not_found(self, user_repository: UserRepository):
        """Test user update when user not found."""
        update_data = UserUpdate(display_name="Updated Name")

        result = await user_repository.update(999, update_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_database_error(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test user update with database error."""
        update_data = UserUpdate(display_name="Updated Name")

        with patch.object(user_repository.session, "commit") as mock_commit:
            mock_commit.side_effect = SQLAlchemyError("Database error")

            with pytest.raises(UserRepositoryError) as exc_info:
                await user_repository.update(test_user.id, update_data)

            assert "Failed to update user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_success(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test successful user deletion."""
        result = await user_repository.delete(test_user.id)

        assert result is True

        # Verify user is deleted
        deleted_user = await user_repository.get_by_id(test_user.id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, user_repository: UserRepository):
        """Test user deletion when user not found."""
        result = await user_repository.delete(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_database_error(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test user deletion with database error."""
        with patch.object(user_repository.session, "commit") as mock_commit:
            mock_commit.side_effect = SQLAlchemyError("Database error")

            with pytest.raises(UserRepositoryError) as exc_info:
                await user_repository.delete(test_user.id)

            assert "Failed to delete user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exists_by_line_user_id_true(
        self, user_repository: UserRepository, test_user: User
    ):
        """Test user existence check when user exists."""
        result = await user_repository.exists_by_line_user_id(test_user.line_user_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_line_user_id_false(self, user_repository: UserRepository):
        """Test user existence check when user doesn't exist."""
        result = await user_repository.exists_by_line_user_id("nonexistent_line_user")

        assert result is False

    @pytest.mark.asyncio
    async def test_count_success(
        self, user_repository: UserRepository, multiple_test_users: list[User]
    ):
        """Test successful user count."""
        result = await user_repository.count()

        assert result == len(multiple_test_users)

    @pytest.mark.asyncio
    async def test_count_empty_database(self, user_repository: UserRepository):
        """Test user count with empty database."""
        result = await user_repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_database_error(self, user_repository: UserRepository):
        """Test user count with database error."""
        with patch.object(user_repository.session, "exec") as mock_exec:
            mock_exec.side_effect = SQLAlchemyError("Database error")

            with pytest.raises(UserRepositoryError) as exc_info:
                await user_repository.count()

            assert "Failed to count users" in str(exc_info.value)


class TestUserRepositoryExceptions:
    """Test cases for UserRepository exception classes."""

    def test_user_repository_error(self):
        """Test UserRepositoryError exception."""
        original_error = Exception("Original error")
        error = UserRepositoryError("Repository error", original_error)

        assert error.message == "Repository error"
        assert error.original_error == original_error
        assert str(error) == "Repository error"

    def test_user_not_found_error(self):
        """Test UserNotFoundError exception."""
        error = UserNotFoundError("User not found")

        assert error.message == "User not found"
        assert isinstance(error, UserRepositoryError)

    def test_user_already_exists_error(self):
        """Test UserAlreadyExistsError exception."""
        error = UserAlreadyExistsError("User already exists")

        assert error.message == "User already exists"
        assert isinstance(error, UserRepositoryError)


class TestUserRepositoryIntegration:
    """Integration tests for UserRepository with real database operations."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_user(
        self, user_repository: UserRepository, test_data_factory
    ):
        """Test creating and retrieving a user."""
        # Create user data
        user_data = test_data_factory.create_user_data(
            line_user_id="integration_test_user",
            display_name="Integration Test User",
            email="integration@example.com",
        )

        # Create user
        created_user = await user_repository.create(user_data)
        assert created_user is not None
        assert created_user.id is not None

        # Retrieve by ID
        retrieved_user = await user_repository.get_by_id(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.line_user_id == user_data.line_user_id

        # Retrieve by LINE user ID
        retrieved_by_line_id = await user_repository.get_by_line_user_id(
            user_data.line_user_id
        )
        assert retrieved_by_line_id is not None
        assert retrieved_by_line_id.id == created_user.id

    @pytest.mark.asyncio
    async def test_update_and_verify_user(
        self, user_repository: UserRepository, test_data_factory
    ):
        """Test updating and verifying user changes."""
        # Create user
        user_data = test_data_factory.create_user_data(
            line_user_id="update_test_user", display_name="Original Name"
        )
        created_user = await user_repository.create(user_data)

        # Update user
        update_data = UserUpdate(
            display_name="Updated Name", email="updated@example.com"
        )
        updated_user = await user_repository.update(created_user.id, update_data)

        assert updated_user is not None
        assert updated_user.display_name == "Updated Name"
        assert updated_user.email == "updated@example.com"
        assert updated_user.line_user_id == user_data.line_user_id  # Unchanged

        # Verify changes persist
        retrieved_user = await user_repository.get_by_id(created_user.id)
        assert retrieved_user.display_name == "Updated Name"
        assert retrieved_user.email == "updated@example.com"

    @pytest.mark.asyncio
    async def test_delete_and_verify_user(
        self, user_repository: UserRepository, test_data_factory
    ):
        """Test deleting and verifying user removal."""
        # Create user
        user_data = test_data_factory.create_user_data(
            line_user_id="delete_test_user", display_name="To Be Deleted"
        )
        created_user = await user_repository.create(user_data)

        # Verify user exists
        assert (
            await user_repository.exists_by_line_user_id(user_data.line_user_id) is True
        )

        # Delete user
        delete_result = await user_repository.delete(created_user.id)
        assert delete_result is True

        # Verify user is deleted
        assert await user_repository.get_by_id(created_user.id) is None
        assert (
            await user_repository.exists_by_line_user_id(user_data.line_user_id)
            is False
        )
