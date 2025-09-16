"""Data access layer.

This module provides data access repositories for database operations
with proper error handling and type safety.
"""

from .user_repository import (
    UserRepository,
    UserRepositoryError,
    UserNotFoundError,
    UserAlreadyExistsError,
)

__all__ = [
    "UserRepository",
    "UserRepositoryError",
    "UserNotFoundError", 
    "UserAlreadyExistsError",
]
