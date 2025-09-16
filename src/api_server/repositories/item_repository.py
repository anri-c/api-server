"""Item repository for database operations.

This module provides the ItemRepository class that handles all database operations
for items, including CRUD operations, user-scoped queries, and transaction management.
"""


from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, and_, asc, desc, select

from ..models.item import Item, ItemCreate, ItemUpdate


class ItemNotFoundError(Exception):
    """Raised when an item is not found."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__(f"Item with id {item_id} not found")


class ItemAccessDeniedError(Exception):
    """Raised when user tries to access item they don't own."""

    def __init__(self, item_id: int, user_id: int) -> None:
        self.item_id = item_id
        self.user_id = user_id
        super().__init__(f"User {user_id} does not have access to item {item_id}")


class ItemRepository:
    """Repository for item database operations.

    This repository provides methods for creating, reading, updating, and deleting
    items with proper user scoping and transaction management.

    All operations are scoped to the user - users can only access their own items.
    """

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLModel database session
        """
        self.session = session

    def create(self, item_data: ItemCreate, user_id: int) -> Item:
        """Create a new item for the specified user.

        Args:
            item_data: Item creation data
            user_id: ID of the user who owns the item

        Returns:
            Item: The created item

        Raises:
            SQLAlchemyError: If database operation fails
            IntegrityError: If user_id doesn't exist

        Example:
            item_data = ItemCreate(name="Test Item", price=10.99)
            item = repository.create(item_data, user_id=1)
        """
        try:
            # Create item with user_id
            db_item = Item(
                name=item_data.name,
                description=item_data.description,
                price=item_data.price,
                user_id=user_id,
            )

            self.session.add(db_item)
            self.session.commit()
            self.session.refresh(db_item)

            return db_item

        except IntegrityError as e:
            self.session.rollback()
            raise IntegrityError(
                f"Failed to create item: user_id {user_id} does not exist",
                params=None,
                orig=e.orig if e.orig is not None else e,
            ) from e
        except SQLAlchemyError as e:
            self.session.rollback()
            raise SQLAlchemyError(
                f"Database error while creating item: {str(e)}"
            ) from e

    def get_by_id(self, item_id: int, user_id: int) -> Item | None:
        """Get an item by ID for the specified user.

        Args:
            item_id: ID of the item to retrieve
            user_id: ID of the user who should own the item

        Returns:
            Item: The item if found and owned by user, None otherwise

        Example:
            item = repository.get_by_id(item_id=1, user_id=1)
            if item:
                print(f"Found item: {item.name}")
        """
        try:
            statement = select(Item).where(
                and_(Item.id == item_id, Item.user_id == user_id)
            )

            result = self.session.exec(statement)
            return result.first()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while retrieving item {item_id}: {str(e)}"
            ) from e

    def get_by_id_or_raise(self, item_id: int, user_id: int) -> Item:
        """Get an item by ID for the specified user or raise an exception.

        Args:
            item_id: ID of the item to retrieve
            user_id: ID of the user who should own the item

        Returns:
            Item: The item if found and owned by user

        Raises:
            ItemNotFoundError: If item is not found
            ItemAccessDeniedError: If item exists but is owned by different user

        Example:
            try:
                item = repository.get_by_id_or_raise(item_id=1, user_id=1)
                print(f"Found item: {item.name}")
            except ItemNotFoundError:
                print("Item not found")
        """
        try:
            # First check if item exists at all
            item_exists_statement = select(Item).where(Item.id == item_id)
            existing_item = self.session.exec(item_exists_statement).first()

            if not existing_item:
                raise ItemNotFoundError(item_id)

            # Check if user owns the item
            if existing_item.user_id != user_id:
                raise ItemAccessDeniedError(item_id, user_id)

            # Load with user relationship
            statement = select(Item).where(
                and_(Item.id == item_id, Item.user_id == user_id)
            )

            result = self.session.exec(statement)
            item = result.first()

            if not item:
                raise ItemNotFoundError(item_id)

            return item

        except (ItemNotFoundError, ItemAccessDeniedError):
            raise
        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while retrieving item {item_id}: {str(e)}"
            ) from e

    def get_all_for_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[Item]:
        """Get all items for a specific user with pagination and sorting.

        Args:
            user_id: ID of the user whose items to retrieve
            skip: Number of items to skip (for pagination)
            limit: Maximum number of items to return
            sort_by: Field to sort by (created_at, name, price, updated_at)
            sort_order: Sort order (asc or desc)

        Returns:
            List[Item]: List of items owned by the user

        Raises:
            ValueError: If sort_by or sort_order is invalid
            SQLAlchemyError: If database operation fails

        Example:
            items = repository.get_all_for_user(
                user_id=1, skip=0, limit=10, sort_by="name", sort_order="asc"
            )
        """
        try:
            # Validate sort parameters
            valid_sort_fields = {"created_at", "name", "price", "updated_at"}
            valid_sort_orders = {"asc", "desc"}

            if sort_by not in valid_sort_fields:
                raise ValueError(
                    f"Invalid sort_by field: {sort_by}. "
                    f"Must be one of {valid_sort_fields}"
                )

            if sort_order not in valid_sort_orders:
                raise ValueError(
                    f"Invalid sort_order: {sort_order}. "
                    f"Must be one of {valid_sort_orders}"
                )

            # Build query
            statement = select(Item).where(Item.user_id == user_id)

            # Add sorting
            sort_column = getattr(Item, sort_by)
            if sort_order == "desc":
                statement = statement.order_by(desc(sort_column))
            else:
                statement = statement.order_by(asc(sort_column))

            # Add pagination
            statement = statement.offset(skip).limit(limit)

            result = self.session.exec(statement)
            return list(result.all())

        except ValueError:
            raise
        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while retrieving items for user {user_id}: "
                f"{str(e)}"
            ) from e

    def count_for_user(self, user_id: int) -> int:
        """Count total number of items for a specific user.

        Args:
            user_id: ID of the user whose items to count

        Returns:
            int: Total number of items owned by the user

        Raises:
            SQLAlchemyError: If database operation fails

        Example:
            total_items = repository.count_for_user(user_id=1)
            print(f"User has {total_items} items")
        """
        try:
            statement = select(Item).where(Item.user_id == user_id)
            result = self.session.exec(statement)
            return len(list(result.all()))

        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while counting items for user {user_id}: "
                f"{str(e)}"
            ) from e

    def update(self, item_id: int, user_id: int, item_data: ItemUpdate) -> Item:
        """Update an item for the specified user.

        Args:
            item_id: ID of the item to update
            user_id: ID of the user who should own the item
            item_data: Updated item data

        Returns:
            Item: The updated item

        Raises:
            ItemNotFoundError: If item is not found
            ItemAccessDeniedError: If item exists but is owned by different user
            SQLAlchemyError: If database operation fails

        Example:
            update_data = ItemUpdate(name="Updated Item", price=15.99)
            item = repository.update(item_id=1, user_id=1, item_data=update_data)
        """
        try:
            # Get the item (this will raise appropriate exceptions if not found)
            db_item = self.get_by_id_or_raise(item_id, user_id)

            # Update only provided fields
            update_data = item_data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                setattr(db_item, field, value)

            self.session.add(db_item)
            self.session.commit()
            self.session.refresh(db_item)

            return db_item

        except (ItemNotFoundError, ItemAccessDeniedError):
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise SQLAlchemyError(
                f"Database error while updating item {item_id}: {str(e)}"
            ) from e

    def delete(self, item_id: int, user_id: int) -> bool:
        """Delete an item for the specified user.

        Args:
            item_id: ID of the item to delete
            user_id: ID of the user who should own the item

        Returns:
            bool: True if item was deleted, False if not found

        Raises:
            ItemAccessDeniedError: If item exists but is owned by different user
            SQLAlchemyError: If database operation fails

        Example:
            deleted = repository.delete(item_id=1, user_id=1)
            if deleted:
                print("Item deleted successfully")
        """
        try:
            # Check if item exists and get it
            item = self.get_by_id(item_id, user_id)

            if not item:
                # Check if item exists but belongs to different user
                item_exists_statement = select(Item).where(Item.id == item_id)
                existing_item = self.session.exec(item_exists_statement).first()

                if existing_item:
                    raise ItemAccessDeniedError(item_id, user_id)

                return False  # Item doesn't exist at all

            # Delete the item
            self.session.delete(item)
            self.session.commit()

            return True

        except ItemAccessDeniedError:
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise SQLAlchemyError(
                f"Database error while deleting item {item_id}: {str(e)}"
            ) from e

    def search_for_user(
        self,
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Item]:
        """Search items by name or description for a specific user.

        Args:
            user_id: ID of the user whose items to search
            query: Search query string
            skip: Number of items to skip (for pagination)
            limit: Maximum number of items to return

        Returns:
            List[Item]: List of matching items owned by the user

        Raises:
            SQLAlchemyError: If database operation fails

        Example:
            items = repository.search_for_user(
                user_id=1, query="laptop", skip=0, limit=10
            )
        """
        try:
            # Build search query (case-insensitive)
            search_pattern = f"%{query.lower()}%"

            statement = (
                select(Item)
                .where(
                    and_(
                        Item.user_id == user_id,
                        or_(
                            func.lower(Item.name).like(search_pattern),
                            func.lower(Item.description).like(search_pattern),
                        ),
                    )
                )
                .order_by(desc(Item.created_at))
                .offset(skip)
                .limit(limit)
            )

            result = self.session.exec(statement)
            return list(result.all())

        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while searching items for user {user_id}: "
                f"{str(e)}"
            ) from e

    def get_user_items_by_price_range(
        self,
        user_id: int,
        min_price: float | None = None,
        max_price: float | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Item]:
        """Get items within a price range for a specific user.

        Args:
            user_id: ID of the user whose items to retrieve
            min_price: Minimum price (inclusive)
            max_price: Maximum price (inclusive)
            skip: Number of items to skip (for pagination)
            limit: Maximum number of items to return

        Returns:
            List[Item]: List of items within the price range owned by the user

        Raises:
            ValueError: If price range is invalid
            SQLAlchemyError: If database operation fails

        Example:
            items = repository.get_user_items_by_price_range(
                user_id=1, min_price=10.0, max_price=100.0
            )
        """
        try:
            if (
                min_price is not None
                and max_price is not None
                and min_price > max_price
            ):
                raise ValueError("min_price cannot be greater than max_price")

            # Build query with price filters
            conditions = [Item.user_id == user_id]

            if min_price is not None:
                conditions.append(Item.price >= min_price)

            if max_price is not None:
                conditions.append(Item.price <= max_price)

            statement = (
                select(Item)
                .where(and_(*conditions))
                .order_by(asc(Item.price))
                .offset(skip)
                .limit(limit)
            )

            result = self.session.exec(statement)
            return list(result.all())

        except ValueError:
            raise
        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while retrieving items by price range "
                f"for user {user_id}: {str(e)}"
            ) from e
