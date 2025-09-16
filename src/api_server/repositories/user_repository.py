"""User repository for database operations.

This module provides data access layer for user management operations
with comprehensive type hints and error handling.
"""

from typing import Optional, List
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..models.user import User, UserCreate, UserUpdate


class UserRepositoryError(Exception):
    """Base exception for user repository errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class UserNotFoundError(UserRepositoryError):
    """Exception raised when user is not found."""
    pass


class UserAlreadyExistsError(UserRepositoryError):
    """Exception raised when trying to create a user that already exists."""
    pass


class UserRepository:
    """Repository for user database operations.
    
    This repository provides data access methods for user management
    with proper error handling and type safety.
    """
    
    def __init__(self, session: Session) -> None:
        """Initialize user repository with database session.
        
        Args:
            session: SQLModel database session
        """
        self.session = session
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User if found, None otherwise
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            statement = select(User).where(User.id == user_id)
            result = self.session.exec(statement)
            return result.first()
        except SQLAlchemyError as e:
            raise UserRepositoryError(
                f"Failed to get user by ID {user_id}: {str(e)}",
                original_error=e
            ) from e
    
    async def get_by_line_user_id(self, line_user_id: str) -> Optional[User]:
        """Get user by LINE user ID.
        
        Args:
            line_user_id: LINE user ID to search for
            
        Returns:
            User if found, None otherwise
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            statement = select(User).where(User.line_user_id == line_user_id)
            result = self.session.exec(statement)
            return result.first()
        except SQLAlchemyError as e:
            raise UserRepositoryError(
                f"Failed to get user by LINE user ID {line_user_id}: {str(e)}",
                original_error=e
            ) from e
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User if found, None otherwise
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            statement = select(User).where(User.email == email)
            result = self.session.exec(statement)
            return result.first()
        except SQLAlchemyError as e:
            raise UserRepositoryError(
                f"Failed to get user by email {email}: {str(e)}",
                original_error=e
            ) from e
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Get all users with pagination.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of users
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            statement = select(User).offset(offset).limit(limit)
            result = self.session.exec(statement)
            return list(result.all())
        except SQLAlchemyError as e:
            raise UserRepositoryError(
                f"Failed to get users: {str(e)}",
                original_error=e
            ) from e
    
    async def create(self, user_data: UserCreate) -> User:
        """Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user
            
        Raises:
            UserAlreadyExistsError: If user with same LINE user ID already exists
            UserRepositoryError: If database operation fails
        """
        try:
            # Check if user already exists
            existing_user = await self.get_by_line_user_id(user_data.line_user_id)
            if existing_user:
                raise UserAlreadyExistsError(
                    f"User with LINE user ID {user_data.line_user_id} already exists"
                )
            
            # Create new user
            user = User(**user_data.dict())
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            return user
            
        except UserAlreadyExistsError:
            raise
        except IntegrityError as e:
            self.session.rollback()
            raise UserAlreadyExistsError(
                f"User with LINE user ID {user_data.line_user_id} already exists",
                original_error=e
            ) from e
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserRepositoryError(
                f"Failed to create user: {str(e)}",
                original_error=e
            ) from e
    
    async def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user information.
        
        Args:
            user_id: ID of user to update
            user_data: Updated user data
            
        Returns:
            Updated user if found, None otherwise
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return None
            
            # Update only provided fields
            update_data = user_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)
            
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            return user
            
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserRepositoryError(
                f"Failed to update user {user_id}: {str(e)}",
                original_error=e
            ) from e
    
    async def delete(self, user_id: int) -> bool:
        """Delete user by ID.
        
        Args:
            user_id: ID of user to delete
            
        Returns:
            True if user was deleted, False if not found
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False
            
            self.session.delete(user)
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            raise UserRepositoryError(
                f"Failed to delete user {user_id}: {str(e)}",
                original_error=e
            ) from e
    
    async def exists_by_line_user_id(self, line_user_id: str) -> bool:
        """Check if user exists by LINE user ID.
        
        Args:
            line_user_id: LINE user ID to check
            
        Returns:
            True if user exists, False otherwise
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            statement = select(User.id).where(User.line_user_id == line_user_id)
            result = self.session.exec(statement)
            return result.first() is not None
        except SQLAlchemyError as e:
            raise UserRepositoryError(
                f"Failed to check user existence for LINE user ID {line_user_id}: {str(e)}",
                original_error=e
            ) from e
    
    async def count(self) -> int:
        """Get total count of users.
        
        Returns:
            Total number of users
            
        Raises:
            UserRepositoryError: If database operation fails
        """
        try:
            from sqlalchemy import func
            statement = select(func.count(User.id))
            result = self.session.exec(statement)
            return result.first() or 0
        except SQLAlchemyError as e:
            raise UserRepositoryError(
                f"Failed to count users: {str(e)}",
                original_error=e
            ) from e
