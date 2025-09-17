"""Post schemas for CRUD operations and API responses.

This module defines Pydantic schemas for post-related API operations,
including creation, updates, responses, and user relationship handling.
All schemas include comprehensive validation rules and proper type hints.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator


class PostCreate(BaseModel):
    """Schema for creating a new post.

    This schema validates post creation requests with comprehensive
    validation rules for all fields.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Post title (required, 1-100 characters)",
        example="My First Blog Post",
    )
    content: str | None = Field(
        default=None,
        max_length=5000,
        description="Post content (optional, max 5000 characters)",
        example="This is the content of my first blog post...",
    )
    published: bool = Field(
        default=False,
        description="Whether the post should be published",
        example=False,
    )
    location: str | None = Field(
        default=None,
        max_length=12,
        description="Location as GEOHASH (optional, max 12 characters)",
        example="u4pruydqqvj",
    )

    @validator("title")
    def validate_title(cls, v: str) -> str:
        """Validate post title."""
        if not v or v.isspace():
            raise ValueError("Post title cannot be empty or whitespace only")

        # Remove extra whitespace
        v = " ".join(v.split())

        # Check for minimum meaningful content
        if len(v.strip()) < 1:
            raise ValueError(
                "Post title must contain at least 1 non-whitespace character"
            )

        return v

    @validator("content")
    def validate_content(cls, v: str | None) -> str | None:
        """Validate post content."""
        if v is not None:
            # Remove extra whitespace
            v = " ".join(v.split())

            # Return None if content is empty after cleaning
            if not v:
                return None

        return v

    @validator("location")
    def validate_location(cls, v: str | None) -> str | None:
        """Validate GEOHASH location."""
        if v is not None:
            # Remove whitespace
            v = v.strip()
            
            # Return None if location is empty after cleaning
            if not v:
                return None
            
            # Basic GEOHASH validation (alphanumeric, specific characters)
            import re
            if not re.match(r'^[0-9a-z]+$', v.lower()):
                raise ValueError("Location must be a valid GEOHASH (alphanumeric characters only)")
            
            # GEOHASH length validation (typically 1-12 characters)
            if len(v) < 1 or len(v) > 12:
                raise ValueError("GEOHASH must be between 1 and 12 characters")

        return v


class PostUpdate(BaseModel):
    """Schema for updating post information.

    This schema allows partial updates to post information.
    All fields are optional to support partial updates.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated post title",
        example="My Updated Blog Post",
    )
    content: str | None = Field(
        default=None,
        max_length=5000,
        description="Updated post content",
        example="This is the updated content of my blog post...",
    )
    published: bool | None = Field(
        default=None,
        description="Updated publication status",
        example=True,
    )
    location: str | None = Field(
        default=None,
        max_length=12,
        description="Updated location as GEOHASH",
        example="u4pruydqqvj",
    )

    @validator("title")
    def validate_title(cls, v: str | None) -> str | None:
        """Validate post title for updates."""
        if v is not None:
            if not v or v.isspace():
                raise ValueError("Post title cannot be empty or whitespace only")

            # Remove extra whitespace
            v = " ".join(v.split())

            # Check for minimum meaningful content
            if len(v.strip()) < 1:
                raise ValueError(
                    "Post title must contain at least 1 non-whitespace character"
                )

        return v

    @validator("content")
    def validate_content(cls, v: str | None) -> str | None:
        """Validate post content for updates."""
        if v is not None:
            # Remove extra whitespace
            v = " ".join(v.split())

            # Return None if content is empty after cleaning
            if not v:
                return None

        return v

    @validator("location")
    def validate_location(cls, v: str | None) -> str | None:
        """Validate GEOHASH location for updates."""
        if v is not None:
            # Remove whitespace
            v = v.strip()
            
            # Return None if location is empty after cleaning
            if not v:
                return None
            
            # Basic GEOHASH validation (alphanumeric, specific characters)
            import re
            if not re.match(r'^[0-9a-z]+$', v.lower()):
                raise ValueError("Location must be a valid GEOHASH (alphanumeric characters only)")
            
            # GEOHASH length validation (typically 1-12 characters)
            if len(v) < 1 or len(v) > 12:
                raise ValueError("GEOHASH must be between 1 and 12 characters")

        return v


class PostResponse(BaseModel):
    """Schema for post API responses.

    This schema is used when returning post information through the API.
    It includes the post ID, user relationship, and timestamps.
    """

    id: int = Field(..., gt=0, description="Post ID", example=123)
    title: str = Field(..., description="Post title", example="My First Blog Post")
    content: str | None = Field(
        default=None,
        description="Post content",
        example="This is the content of my first blog post...",
    )
    published: bool = Field(..., description="Publication status", example=False)
    location: str | None = Field(
        default=None, description="Location as GEOHASH", example="u4pruydqqvj"
    )
    user_id: int = Field(
        ..., gt=0, description="ID of the user who owns this post", example=456
    )
    created_at: datetime = Field(
        ..., description="Post creation timestamp", example="2024-01-01T00:00:00Z"
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
        example="2024-01-02T12:00:00Z",
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class UserSummary(BaseModel):
    """Schema for user summary in post responses.

    This schema provides essential user information when included
    in post responses without exposing sensitive data.
    """

    id: int = Field(..., gt=0, description="User ID", example=456)
    display_name: str = Field(
        ..., description="User's display name", example="John Doe"
    )
    picture_url: str | None = Field(
        default=None,
        description="URL to user's profile picture",
        example="https://profile.line-scdn.net/...",
    )


class PostWithUser(PostResponse):
    """Schema for post responses that include user information.

    This schema includes user information along with the post data.
    Useful for API responses that need to show post ownership details.
    """

    user: UserSummary = Field(..., description="User who owns this post")


class PostListResponse(BaseModel):
    """Schema for paginated post list responses.

    This schema provides a structured response for post listings
    with pagination metadata.
    """

    posts: list[PostResponse] = Field(..., description="List of posts", example=[])
    total: int = Field(..., ge=0, description="Total number of posts", example=100)
    page: int = Field(..., ge=1, description="Current page number", example=1)
    page_size: int = Field(
        ..., ge=1, le=100, description="Number of posts per page", example=20
    )
    total_pages: int = Field(..., ge=0, description="Total number of pages", example=5)

    @validator("total_pages")
    def validate_total_pages(cls, v: int, values: dict) -> int:
        """Validate total pages calculation."""
        if "total" in values and "page_size" in values:
            expected_pages = (values["total"] + values["page_size"] - 1) // values[
                "page_size"
            ]
            if v != expected_pages:
                raise ValueError("Total pages calculation is incorrect")
        return v


class PostSortField(str, Enum):
    """Enumeration for post sorting fields."""

    TITLE = "title"
    PUBLISHED = "published"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(str, Enum):
    """Enumeration for sort order."""

    ASC = "asc"
    DESC = "desc"


class PostListRequest(BaseModel):
    """Schema for post list request parameters.

    This schema validates query parameters for post listing endpoints.
    """

    page: int = Field(
        default=1, ge=1, description="Page number (starts from 1)", example=1
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of posts per page (max 100)",
        example=20,
    )
    sort_by: PostSortField = Field(
        default=PostSortField.CREATED_AT,
        description="Field to sort by",
        example=PostSortField.CREATED_AT,
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort order (ascending or descending)",
        example=SortOrder.DESC,
    )
    search: str | None = Field(
        default=None,
        max_length=100,
        description="Search term for post title or content",
        example="blog",
    )
    published_only: bool = Field(
        default=False,
        description="Filter to show only published posts",
        example=False,
    )

    @validator("search")
    def validate_search(cls, v: str | None) -> str | None:
        """Validate search term."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # Remove extra whitespace
            v = " ".join(v.split())
        return v


class PostError(BaseModel):
    """Schema for post-related error responses.

    This schema provides structured error information for post operations.
    """

    error: str = Field(..., description="Error code", example="post_not_found")
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="The requested post was not found",
    )
    field: str | None = Field(
        default=None, description="Field name for validation errors", example="title"
    )

    @validator("error")
    def validate_error(cls, v: str) -> str:
        """Validate error code."""
        if not v or v.isspace():
            raise ValueError("Error code cannot be empty")
        return v.strip()

    @validator("message")
    def validate_message(cls, v: str) -> str:
        """Validate error message."""
        if not v or v.isspace():
            raise ValueError("Error message cannot be empty")
        return v.strip()


class PostOperationResponse(BaseModel):
    """Schema for post operation responses.

    This schema provides the result of post operations like create, update, delete.
    """

    success: bool = Field(
        ..., description="Whether the operation was successful", example=True
    )
    message: str = Field(
        ..., description="Operation result message", example="Post created successfully"
    )
    post: PostResponse | None = Field(
        default=None,
        description="Post data (present for successful create/update operations)",
    )

    @validator("message")
    def validate_message(cls, v: str) -> str:
        """Validate operation message."""
        if not v or v.isspace():
            raise ValueError("Operation message cannot be empty")
        return v.strip()