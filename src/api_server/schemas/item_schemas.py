"""Item schemas for CRUD operations and API responses.

This module defines Pydantic schemas for item-related API operations,
including creation, updates, responses, and user relationship handling.
All schemas include comprehensive validation rules and proper type hints.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator


class ItemCreate(BaseModel):
    """Schema for creating a new item.

    This schema validates item creation requests with comprehensive
    validation rules for all fields.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item name (required, 1-100 characters)",
        example="Premium Coffee Beans",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Item description (optional, max 1000 characters)",
        example="High-quality arabica coffee beans from Colombia",
    )
    price: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Item price (must be positive, max 10 digits with 2 decimal places)",
        example=29.99,
    )

    @validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate item name."""
        if not v or v.isspace():
            raise ValueError("Item name cannot be empty or whitespace only")

        # Remove extra whitespace
        v = " ".join(v.split())

        # Check for minimum meaningful content
        if len(v.strip()) < 1:
            raise ValueError(
                "Item name must contain at least 1 non-whitespace character"
            )

        return v

    @validator("description")
    def validate_description(cls, v: str | None) -> str | None:
        """Validate item description."""
        if v is not None:
            # Remove extra whitespace
            v = " ".join(v.split())

            # Return None if description is empty after cleaning
            if not v:
                return None

        return v

    @validator("price")
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate item price."""
        if v <= 0:
            raise ValueError("Price must be greater than 0")

        # Check for reasonable maximum price (1 million)
        if v > Decimal("1000000.00"):
            raise ValueError("Price cannot exceed 1,000,000.00")

        # Ensure proper decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError("Price cannot have more than 2 decimal places")

        return v


class ItemUpdate(BaseModel):
    """Schema for updating item information.

    This schema allows partial updates to item information.
    All fields are optional to support partial updates.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated item name",
        example="Premium Coffee Beans - Updated",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Updated item description",
        example="Updated description for high-quality arabica coffee beans",
    )
    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Updated item price",
        example=34.99,
    )

    @validator("name")
    def validate_name(cls, v: str | None) -> str | None:
        """Validate item name for updates."""
        if v is not None:
            if not v or v.isspace():
                raise ValueError("Item name cannot be empty or whitespace only")

            # Remove extra whitespace
            v = " ".join(v.split())

            # Check for minimum meaningful content
            if len(v.strip()) < 1:
                raise ValueError(
                    "Item name must contain at least 1 non-whitespace character"
                )

        return v

    @validator("description")
    def validate_description(cls, v: str | None) -> str | None:
        """Validate item description for updates."""
        if v is not None:
            # Remove extra whitespace
            v = " ".join(v.split())

            # Return None if description is empty after cleaning
            if not v:
                return None

        return v

    @validator("price")
    def validate_price(cls, v: Decimal | None) -> Decimal | None:
        """Validate item price for updates."""
        if v is not None:
            if v <= 0:
                raise ValueError("Price must be greater than 0")

            # Check for reasonable maximum price (1 million)
            if v > Decimal("1000000.00"):
                raise ValueError("Price cannot exceed 1,000,000.00")

            # Ensure proper decimal places
            if v.as_tuple().exponent < -2:
                raise ValueError("Price cannot have more than 2 decimal places")

        return v


class ItemResponse(BaseModel):
    """Schema for item API responses.

    This schema is used when returning item information through the API.
    It includes the item ID, user relationship, and timestamps.
    """

    id: int = Field(..., gt=0, description="Item ID", example=123)
    name: str = Field(..., description="Item name", example="Premium Coffee Beans")
    description: str | None = Field(
        default=None,
        description="Item description",
        example="High-quality arabica coffee beans from Colombia",
    )
    price: Decimal = Field(..., description="Item price", example=29.99)
    user_id: int = Field(
        ..., gt=0, description="ID of the user who owns this item", example=456
    )
    created_at: datetime = Field(
        ..., description="Item creation timestamp", example="2024-01-01T00:00:00Z"
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
        example="2024-01-02T12:00:00Z",
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {Decimal: lambda v: float(v), datetime: lambda v: v.isoformat()}


class UserSummary(BaseModel):
    """Schema for user summary in item responses.

    This schema provides essential user information when included
    in item responses without exposing sensitive data.
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


class ItemWithUser(ItemResponse):
    """Schema for item responses that include user information.

    This schema includes user information along with the item data.
    Useful for API responses that need to show item ownership details.
    """

    user: UserSummary = Field(..., description="User who owns this item")


class ItemListResponse(BaseModel):
    """Schema for paginated item list responses.

    This schema provides a structured response for item listings
    with pagination metadata.
    """

    items: list[ItemResponse] = Field(..., description="List of items", example=[])
    total: int = Field(..., ge=0, description="Total number of items", example=100)
    page: int = Field(..., ge=1, description="Current page number", example=1)
    page_size: int = Field(
        ..., ge=1, le=100, description="Number of items per page", example=20
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


class ItemSortField(str, Enum):
    """Enumeration for item sorting fields."""

    NAME = "name"
    PRICE = "price"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(str, Enum):
    """Enumeration for sort order."""

    ASC = "asc"
    DESC = "desc"


class ItemListRequest(BaseModel):
    """Schema for item list request parameters.

    This schema validates query parameters for item listing endpoints.
    """

    page: int = Field(
        default=1, ge=1, description="Page number (starts from 1)", example=1
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
        example=20,
    )
    sort_by: ItemSortField = Field(
        default=ItemSortField.CREATED_AT,
        description="Field to sort by",
        example=ItemSortField.CREATED_AT,
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort order (ascending or descending)",
        example=SortOrder.DESC,
    )
    search: str | None = Field(
        default=None,
        max_length=100,
        description="Search term for item name or description",
        example="coffee",
    )
    min_price: Decimal | None = Field(
        default=None, ge=0, description="Minimum price filter", example=10.00
    )
    max_price: Decimal | None = Field(
        default=None, gt=0, description="Maximum price filter", example=100.00
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

    @validator("max_price")
    def validate_price_range(cls, v: Decimal | None, values: dict) -> Decimal | None:
        """Validate price range consistency."""
        if v is not None and "min_price" in values and values["min_price"] is not None:
            if v <= values["min_price"]:
                raise ValueError("Maximum price must be greater than minimum price")
        return v


class ItemError(BaseModel):
    """Schema for item-related error responses.

    This schema provides structured error information for item operations.
    """

    error: str = Field(..., description="Error code", example="item_not_found")
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="The requested item was not found",
    )
    field: str | None = Field(
        default=None, description="Field name for validation errors", example="price"
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


class ItemOperationResponse(BaseModel):
    """Schema for item operation responses.

    This schema provides the result of item operations like create, update, delete.
    """

    success: bool = Field(
        ..., description="Whether the operation was successful", example=True
    )
    message: str = Field(
        ..., description="Operation result message", example="Item created successfully"
    )
    item: ItemResponse | None = Field(
        default=None,
        description="Item data (present for successful create/update operations)",
    )

    @validator("message")
    def validate_message(cls, v: str) -> str:
        """Validate operation message."""
        if not v or v.isspace():
            raise ValueError("Operation message cannot be empty")
        return v.strip()
