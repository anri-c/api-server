"""Item model with user relationships.

This module defines the Item SQLModel for storing items with user ownership,
including proper type hints, validation, and database relationships.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, Column, String, DateTime, Numeric, ForeignKey, Relationship, Index
from sqlalchemy import func

if TYPE_CHECKING:
    from .user import User


class ItemBase(SQLModel):
    """Base item model with common fields."""
    
    name: str = Field(
        max_length=100,
        min_length=1,
        description="Item name (required, 1-100 characters)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Item description (optional, max 1000 characters)"
    )
    price: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Item price (must be positive, max 10 digits with 2 decimal places)"
    )


class Item(ItemBase, table=True):
    """Item model for database storage.
    
    This model represents an item owned by a user. Each item belongs to
    exactly one user and includes pricing and descriptive information.
    
    Attributes:
        id: Primary key (auto-generated)
        name: Item name (required)
        description: Optional item description
        price: Item price (positive decimal)
        user_id: Foreign key to the owning user
        user: Relationship to the User model
        created_at: Timestamp when item was created
        updated_at: Timestamp when item was last updated
    """
    
    __tablename__ = "items"
    
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Primary key (auto-generated)"
    )
    
    # Override price to use proper database column type
    price: Decimal = Field(
        gt=0,
        description="Item price (must be positive)",
        sa_column=Column(Numeric(10, 2), nullable=False)
    )
    
    # Foreign key to user
    user_id: int = Field(
        foreign_key="users.id",
        description="ID of the user who owns this item",
        index=True
    )
    
    # Relationship to user
    user: Optional["User"] = Relationship(back_populates="items", sa_relationship_kwargs={"lazy": "select"})
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when item was created",
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when item was last updated",
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    
    __table_args__ = (
        Index("idx_items_user_id", "user_id"),
        Index("idx_items_name", "name"),
        Index("idx_items_price", "price"),
        Index("idx_items_created_at", "created_at"),
        Index("idx_items_user_created", "user_id", "created_at"),  # Composite index for user's items by date
    )


class ItemCreate(ItemBase):
    """Schema for creating a new item.
    
    This schema is used when creating a new item. The user_id is typically
    set from the authenticated user context, not from the request body.
    """
    pass


class ItemUpdate(SQLModel):
    """Schema for updating item information.
    
    This schema allows partial updates to item information.
    All fields are optional to support partial updates.
    """
    
    name: Optional[str] = Field(
        default=None,
        max_length=100,
        min_length=1,
        description="Updated item name"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Updated item description"
    )
    price: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Updated item price"
    )


class ItemResponse(ItemBase):
    """Schema for item API responses.
    
    This schema is used when returning item information through the API.
    It includes the item ID, user ID, and timestamps for client use.
    """
    
    id: int = Field(description="Item ID")
    user_id: int = Field(description="ID of the user who owns this item")
    created_at: datetime = Field(description="Item creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")


class ItemWithUser(ItemResponse):
    """Schema for item responses that include user information.
    
    This schema includes the full user information along with the item data.
    Useful for API responses that need to show item ownership details.
    """
    
    user: Optional["UserResponse"] = Field(description="User who owns this item")


class ItemInDB(ItemBase):
    """Item model with all database fields.
    
    This model includes all fields that exist in the database,
    including auto-generated fields like timestamps.
    """
    
    id: int = Field(description="Item ID")
    user_id: int = Field(description="ID of the user who owns this item")
    created_at: datetime = Field(description="Item creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")


# Import here to avoid circular imports
from .user import UserResponse
