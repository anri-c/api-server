"""SQLModel data models.

This module exports all database models and schemas for the API server.
Import models from here to ensure proper initialization and relationships.
"""

from .user import (
    User,
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB
)
from .item import (
    Item,
    ItemBase,
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemWithUser,
    ItemInDB
)

__all__ = [
    # User models
    "User",
    "UserBase", 
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Item models
    "Item",
    "ItemBase",
    "ItemCreate", 
    "ItemUpdate",
    "ItemResponse",
    "ItemWithUser",
    "ItemInDB",
]
