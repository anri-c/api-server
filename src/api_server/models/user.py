"""User model with LINE integration.

This module defines the User SQLModel for storing LINE authenticated users
with proper type hints, validation, and database constraints.
"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, String, DateTime, Index, Relationship
from sqlalchemy import func

if TYPE_CHECKING:
    from .item import Item


class UserBase(SQLModel):
    """Base user model with common fields."""
    
    line_user_id: str = Field(
        max_length=100,
        description="LINE user ID (unique identifier from LINE)",
        index=True
    )
    display_name: str = Field(
        max_length=200,
        description="User's display name from LINE profile"
    )
    picture_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL to user's profile picture from LINE"
    )
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's email address from LINE profile"
    )


class User(UserBase, table=True):
    """User model for database storage.
    
    This model represents a user authenticated through LINE Login.
    It stores essential user information and maintains relationships
    with other entities in the system.
    
    Attributes:
        id: Primary key (auto-generated)
        line_user_id: Unique LINE user identifier
        display_name: User's display name from LINE
        picture_url: Optional profile picture URL
        email: Optional email address
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
    """
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Primary key (auto-generated)"
    )
    
    # Override line_user_id to add unique constraint
    line_user_id: str = Field(
        max_length=100,
        description="LINE user ID (unique identifier from LINE)",
        sa_column=Column(String(100), unique=True, nullable=False, index=True)
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when user was created",
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when user was last updated",
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    
    # Relationship to items
    items: List["Item"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "select"})
    
    __table_args__ = (
        Index("idx_users_line_user_id", "line_user_id"),
        Index("idx_users_email", "email"),
        Index("idx_users_created_at", "created_at"),
    )


class UserCreate(UserBase):
    """Schema for creating a new user.
    
    This schema is used when creating a new user from LINE authentication data.
    It includes all required fields for user creation.
    """
    pass


class UserUpdate(SQLModel):
    """Schema for updating user information.
    
    This schema allows partial updates to user information.
    All fields are optional to support partial updates.
    """
    
    display_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Updated display name"
    )
    picture_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Updated profile picture URL"
    )
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated email address"
    )


class UserResponse(UserBase):
    """Schema for user API responses.
    
    This schema is used when returning user information through the API.
    It includes the user ID and timestamps for client use.
    """
    
    id: int = Field(description="User ID")
    created_at: datetime = Field(description="User creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")


class UserInDB(UserBase):
    """User model with all database fields.
    
    This model includes all fields that exist in the database,
    including auto-generated fields like timestamps.
    """
    
    id: int = Field(description="User ID")
    created_at: datetime = Field(description="User creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")
