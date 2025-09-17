"""Post model with user relationships.

This module defines the Post SQLModel for storing posts with user ownership,
including proper type hints, validation, and database relationships.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import func
from sqlmodel import (
    Column,
    DateTime,
    Field,
    Index,
    Relationship,
    SQLModel,
)

if TYPE_CHECKING:
    from .user import User


class PostBase(SQLModel):
    """Base post model with common fields."""

    title: str = Field(
        max_length=100,
        min_length=1,
        description="Post title (required, 1-100 characters)",
    )
    content: str | None = Field(
        default=None,
        max_length=5000,
        description="Post content (optional, max 5000 characters)",
    )
    published: bool = Field(
        default=False,
        description="Whether the post is published",
    )
    location: str | None = Field(
        default=None,
        max_length=12,
        description="Location as GEOHASH (optional, max 12 characters)",
    )


class Post(PostBase, table=True):
    """Post model for database storage.

    This model represents a post owned by a user. Each post belongs to
    exactly one user and includes title, content, and publication status.

    Attributes:
        id: Primary key (auto-generated)
        title: Post title (required)
        content: Optional post content
        published: Publication status (default: false)
        location: Optional location as GEOHASH
        user_id: Foreign key to the owning user
        user: Relationship to the User model
        created_at: Timestamp when post was created
        updated_at: Timestamp when post was last updated
    """

    __tablename__ = "posts"

    id: int | None = Field(
        default=None, primary_key=True, description="Primary key (auto-generated)"
    )

    # Foreign key to user
    user_id: int = Field(
        foreign_key="users.id",
        description="ID of the user who owns this post",
        index=True,
    )

    # Relationship to user
    user: Optional["User"] = Relationship(
        back_populates="posts", sa_relationship_kwargs={"lazy": "select"}
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when post was created",
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when post was last updated",
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )

    __table_args__ = (
        Index("idx_posts_user_id", "user_id"),
        Index("idx_posts_title", "title"),
        Index("idx_posts_published", "published"),
        Index("idx_posts_created_at", "created_at"),
        Index(
            "idx_posts_user_created", "user_id", "created_at"
        ),  # Composite index for user's posts by date
    )


class PostCreate(PostBase):
    """Schema for creating a new post.

    This schema is used when creating a new post. The user_id is typically
    set from the authenticated user context, not from the request body.
    """

    pass


class PostUpdate(SQLModel):
    """Schema for updating post information.

    This schema allows partial updates to post information.
    All fields are optional to support partial updates.
    """

    title: str | None = Field(
        default=None, max_length=100, min_length=1, description="Updated post title"
    )
    content: str | None = Field(
        default=None, max_length=5000, description="Updated post content"
    )
    published: bool | None = Field(
        default=None, description="Updated publication status"
    )
    location: str | None = Field(
        default=None, max_length=12, description="Updated location as GEOHASH"
    )


class PostResponse(PostBase):
    """Schema for post API responses.

    This schema is used when returning post information through the API.
    It includes the post ID, user ID, and timestamps for client use.
    """

    id: int = Field(description="Post ID")
    user_id: int = Field(description="ID of the user who owns this post")
    created_at: datetime = Field(description="Post creation timestamp")
    updated_at: datetime | None = Field(description="Last update timestamp")


class PostWithUser(PostResponse):
    """Schema for post responses that include user information.

    This schema includes the full user information along with the post data.
    Useful for API responses that need to show post ownership details.
    """

    user: Optional["UserResponse"] = Field(description="User who owns this post")


class PostInDB(PostBase):
    """Post model with all database fields.

    This model includes all fields that exist in the database,
    including auto-generated fields like timestamps.
    """

    id: int = Field(description="Post ID")
    user_id: int = Field(description="ID of the user who owns this post")
    created_at: datetime = Field(description="Post creation timestamp")
    updated_at: datetime | None = Field(description="Last update timestamp")


# Import here to avoid circular imports
from .user import UserResponse