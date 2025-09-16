"""Item service for business logic operations.

This module provides business logic for item management operations,
including item CRUD operations, user authorization checks, validation,
proper error handling with comprehensive type hints, and operation logging.
"""

from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from ..models.item import Item, ItemCreate, ItemUpdate
from ..repositories.item_repository import (
    ItemAccessDeniedError,
    ItemNotFoundError,
    ItemRepository,
)
from ..repositories.user_repository import UserRepository
from ..schemas.item_schemas import (
    ItemListRequest,
    ItemListResponse,
    ItemResponse,
    ItemWithUser,
    UserSummary,
)
from ..logging_config import get_logger, log_database_operation

logger = get_logger("item_service")


class ItemServiceError(Exception):
    """Base exception for item service errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        original_error: Exception | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.original_error = original_error
        super().__init__(self.message)


class ItemNotFoundServiceError(ItemServiceError):
    """Exception raised when item is not found."""

    def __init__(self, item_id: int) -> None:
        super().__init__(f"Item with id {item_id} not found", status_code=404)


class ItemAccessDeniedServiceError(ItemServiceError):
    """Exception raised when user doesn't have access to item."""

    def __init__(self, item_id: int, user_id: int) -> None:
        super().__init__(
            f"User {user_id} does not have access to item {item_id}", status_code=403
        )


class ItemValidationError(ItemServiceError):
    """Exception raised for item validation errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class ItemService:
    """Service for item business logic operations.

    This service provides business logic for item management,
    including validation, authorization, transformation, and coordination with
    repositories.
    All operations are user-scoped - users can only access their own items.
    """

    def __init__(self, session: Session) -> None:
        """Initialize item service with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session
        self.item_repository = ItemRepository(session)
        self.user_repository = UserRepository(session)

    async def create_item(self, item_data: ItemCreate, user_id: int) -> ItemResponse:
        """Create a new item for the specified user.

        Args:
            item_data: Item creation data
            user_id: ID of the user who will own the item

        Returns:
            Created item response

        Raises:
            ItemServiceError: If item creation fails
            ItemValidationError: If validation fails
        """
        try:
            logger.info(
                f"Creating item for user {user_id}",
                extra={
                    "user_id": user_id,
                    "item_name": item_data.name,
                    "item_price": float(item_data.price)
                }
            )
            
            # Validate user exists
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                logger.warning(
                    f"Attempted to create item for non-existent user {user_id}",
                    extra={"user_id": user_id}
                )
                raise ItemServiceError(
                    f"User with id {user_id} not found", status_code=404
                )

            # Validate item data
            self._validate_item_create_data(item_data)

            # Create item
            item = self.item_repository.create(item_data, user_id)
            
            log_database_operation(
                operation="INSERT",
                table="items",
                success=True,
                user_id=user_id,
                item_id=item.id
            )
            
            logger.info(
                f"Item created successfully for user {user_id}",
                extra={
                    "user_id": user_id,
                    "item_id": item.id,
                    "item_name": item.name
                }
            )

            return self._convert_to_response(item)

        except ItemValidationError as e:
            logger.warning(
                f"Item validation failed for user {user_id}: {e.message}",
                extra={"user_id": user_id, "validation_error": e.message}
            )
            raise
        except SQLAlchemyError as e:
            log_database_operation(
                operation="INSERT",
                table="items",
                success=False,
                error=str(e),
                user_id=user_id
            )
            
            if "user_id" in str(e) and "does not exist" in str(e):
                logger.error(
                    f"Foreign key constraint failed for user {user_id}",
                    extra={"user_id": user_id, "error": str(e)}
                )
                raise ItemServiceError(
                    f"User with id {user_id} not found",
                    status_code=404,
                    original_error=e,
                ) from e
            
            logger.error(
                f"Database error creating item for user {user_id}: {str(e)}",
                exc_info=True,
                extra={"user_id": user_id}
            )
            raise ItemServiceError(
                f"Failed to create item: {str(e)}", status_code=500, original_error=e
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error creating item for user {user_id}: {str(e)}",
                exc_info=True,
                extra={"user_id": user_id}
            )
            raise ItemServiceError(
                f"Unexpected error creating item: {str(e)}",
                status_code=500,
                original_error=e,
            ) from e

    async def get_item_by_id(
        self, item_id: int, user_id: int
    ) -> ItemResponse | None:
        """Get item by ID for the specified user.

        Args:
            item_id: ID of the item to retrieve
            user_id: ID of the user who should own the item

        Returns:
            Item response if found and owned by user, None otherwise

        Raises:
            ItemServiceError: If operation fails
        """
        try:
            item = self.item_repository.get_by_id(item_id, user_id)
            if not item:
                return None

            return self._convert_to_response(item)

        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to get item: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_item_by_id_or_raise(self, item_id: int, user_id: int) -> ItemResponse:
        """Get item by ID for the specified user or raise an exception.

        Args:
            item_id: ID of the item to retrieve
            user_id: ID of the user who should own the item

        Returns:
            Item response if found and owned by user

        Raises:
            ItemNotFoundServiceError: If item is not found
            ItemAccessDeniedServiceError: If item exists but is owned by different user
            ItemServiceError: If operation fails
        """
        try:
            item = self.item_repository.get_by_id_or_raise(item_id, user_id)
            return self._convert_to_response(item)

        except ItemNotFoundError as e:
            raise ItemNotFoundServiceError(item_id) from e
        except ItemAccessDeniedError as e:
            raise ItemAccessDeniedServiceError(item_id, user_id) from e
        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to get item: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_items_for_user(
        self, user_id: int, request: ItemListRequest
    ) -> ItemListResponse:
        """Get items for a specific user with filtering, sorting, and pagination.

        Args:
            user_id: ID of the user whose items to retrieve
            request: Request parameters for filtering, sorting, and pagination

        Returns:
            Paginated list of items with metadata

        Raises:
            ItemServiceError: If operation fails
            ItemValidationError: If request parameters are invalid
        """
        try:
            # Validate request parameters
            self._validate_list_request(request)

            # Calculate skip value from page and page_size
            skip = (request.page - 1) * request.page_size

            # Get items based on filters
            if request.search:
                items = self.item_repository.search_for_user(
                    user_id=user_id,
                    query=request.search,
                    skip=skip,
                    limit=request.page_size,
                )
            elif request.min_price is not None or request.max_price is not None:
                items = self.item_repository.get_user_items_by_price_range(
                    user_id=user_id,
                    min_price=float(request.min_price) if request.min_price else None,
                    max_price=float(request.max_price) if request.max_price else None,
                    skip=skip,
                    limit=request.page_size,
                )
            else:
                items = self.item_repository.get_all_for_user(
                    user_id=user_id,
                    skip=skip,
                    limit=request.page_size,
                    sort_by=request.sort_by.value,
                    sort_order=request.sort_order.value,
                )

            # Get total count for pagination
            total_count = self.item_repository.count_for_user(user_id)

            # Calculate total pages
            total_pages = (total_count + request.page_size - 1) // request.page_size

            # Convert items to responses
            item_responses = [self._convert_to_response(item) for item in items]

            return ItemListResponse(
                items=item_responses,
                total=total_count,
                page=request.page,
                page_size=request.page_size,
                total_pages=total_pages,
            )

        except ItemValidationError:
            raise
        except ValueError as e:
            raise ItemValidationError(str(e)) from e
        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to get items: {str(e)}", status_code=500, original_error=e
            ) from e

    async def update_item(
        self, item_id: int, user_id: int, item_data: ItemUpdate
    ) -> ItemResponse:
        """Update an item for the specified user.

        Args:
            item_id: ID of the item to update
            user_id: ID of the user who should own the item
            item_data: Updated item data

        Returns:
            Updated item response

        Raises:
            ItemNotFoundServiceError: If item is not found
            ItemAccessDeniedServiceError: If item exists but is owned by different user
            ItemValidationError: If validation fails
            ItemServiceError: If operation fails
        """
        try:
            # Validate update data
            self._validate_item_update_data(item_data)

            # Update item (this will handle authorization checks)
            item = self.item_repository.update(item_id, user_id, item_data)

            return self._convert_to_response(item)

        except ItemNotFoundError as e:
            raise ItemNotFoundServiceError(item_id) from e
        except ItemAccessDeniedError as e:
            raise ItemAccessDeniedServiceError(item_id, user_id) from e
        except ItemValidationError:
            raise
        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to update item: {str(e)}", status_code=500, original_error=e
            ) from e

    async def delete_item(self, item_id: int, user_id: int) -> bool:
        """Delete an item for the specified user.

        Args:
            item_id: ID of the item to delete
            user_id: ID of the user who should own the item

        Returns:
            True if item was deleted, False if not found

        Raises:
            ItemAccessDeniedServiceError: If item exists but is owned by different user
            ItemServiceError: If operation fails
        """
        try:
            return self.item_repository.delete(item_id, user_id)

        except ItemAccessDeniedError as e:
            raise ItemAccessDeniedServiceError(item_id, user_id) from e
        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to delete item: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_item_with_user(
        self, item_id: int, user_id: int
    ) -> ItemWithUser | None:
        """Get item with user information for the specified user.

        Args:
            item_id: ID of the item to retrieve
            user_id: ID of the user who should own the item

        Returns:
            Item with user information if found and owned by user, None otherwise

        Raises:
            ItemServiceError: If operation fails
        """
        try:
            item = self.item_repository.get_by_id(item_id, user_id)
            if not item:
                return None

            # Get user information
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise ItemServiceError(
                    f"User with id {user_id} not found", status_code=404
                )

            # Convert to response with user information
            item_response = self._convert_to_response(item)
            user_summary = UserSummary(
                id=user.id if user.id is not None else 0,
                display_name=user.display_name,
                picture_url=user.picture_url,
            )

            return ItemWithUser(**item_response.dict(), user=user_summary)

        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to get item with user: {str(e)}",
                status_code=500,
                original_error=e,
            ) from e

    async def search_items(
        self, user_id: int, query: str, page: int = 1, page_size: int = 20
    ) -> ItemListResponse:
        """Search items by name or description for a specific user.

        Args:
            user_id: ID of the user whose items to search
            query: Search query string
            page: Page number (starts from 1)
            page_size: Number of items per page

        Returns:
            Paginated search results

        Raises:
            ItemValidationError: If search parameters are invalid
            ItemServiceError: If operation fails
        """
        try:
            # Validate search parameters
            if not query or not query.strip():
                raise ItemValidationError("Search query cannot be empty")

            if page < 1:
                raise ItemValidationError("Page number must be at least 1")

            if page_size < 1 or page_size > 100:
                raise ItemValidationError("Page size must be between 1 and 100")

            # Calculate skip value
            skip = (page - 1) * page_size

            # Search items
            items = self.item_repository.search_for_user(
                user_id=user_id, query=query.strip(), skip=skip, limit=page_size
            )

            # For search, we don't have an efficient way to get total count
            # So we'll estimate based on returned results
            total_count = len(items)
            if len(items) == page_size:
                # There might be more results, but we can't know for sure
                total_count = page * page_size
            else:
                # This is the last page
                total_count = (page - 1) * page_size + len(items)

            total_pages = (total_count + page_size - 1) // page_size

            # Convert items to responses
            item_responses = [self._convert_to_response(item) for item in items]

            return ItemListResponse(
                items=item_responses,
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        except ItemValidationError:
            raise
        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to search items: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_user_item_count(self, user_id: int) -> int:
        """Get total count of items for a specific user.

        Args:
            user_id: ID of the user whose items to count

        Returns:
            Total number of items owned by the user

        Raises:
            ItemServiceError: If operation fails
        """
        try:
            return self.item_repository.count_for_user(user_id)
        except SQLAlchemyError as e:
            raise ItemServiceError(
                f"Failed to count items: {str(e)}", status_code=500, original_error=e
            ) from e

    def _convert_to_response(self, item: Item) -> ItemResponse:
        """Convert Item model to ItemResponse schema.

        Args:
            item: Item model instance

        Returns:
            ItemResponse schema instance
        """
        return ItemResponse(
            id=item.id if item.id is not None else 0,
            name=item.name,
            description=item.description,
            price=item.price,
            user_id=item.user_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _validate_item_create_data(self, item_data: ItemCreate) -> None:
        """Validate item creation data.

        Args:
            item_data: Item creation data to validate

        Raises:
            ItemValidationError: If validation fails
        """
        # Basic validation (Pydantic handles most of this)
        if not item_data.name or not item_data.name.strip():
            raise ItemValidationError("Item name cannot be empty")

        if item_data.price <= 0:
            raise ItemValidationError("Item price must be greater than 0")

        if item_data.price > Decimal("1000000.00"):
            raise ItemValidationError("Item price cannot exceed 1,000,000.00")

        # Validate description length if provided
        if item_data.description and len(item_data.description) > 1000:
            raise ItemValidationError("Item description cannot exceed 1000 characters")

    def _validate_item_update_data(self, item_data: ItemUpdate) -> None:
        """Validate item update data.

        Args:
            item_data: Item update data to validate

        Raises:
            ItemValidationError: If validation fails
        """
        # Check if at least one field is provided for update
        update_fields = item_data.dict(exclude_unset=True)
        if not update_fields:
            raise ItemValidationError("At least one field must be provided for update")

        # Validate individual fields if provided
        if item_data.name is not None:
            if not item_data.name or not item_data.name.strip():
                raise ItemValidationError("Item name cannot be empty")

        if item_data.price is not None:
            if item_data.price <= 0:
                raise ItemValidationError("Item price must be greater than 0")

            if item_data.price > Decimal("1000000.00"):
                raise ItemValidationError("Item price cannot exceed 1,000,000.00")

        if item_data.description is not None and len(item_data.description) > 1000:
            raise ItemValidationError("Item description cannot exceed 1000 characters")

    def _validate_list_request(self, request: ItemListRequest) -> None:
        """Validate item list request parameters.

        Args:
            request: Item list request to validate

        Raises:
            ItemValidationError: If validation fails
        """
        if request.page < 1:
            raise ItemValidationError("Page number must be at least 1")

        if request.page_size < 1 or request.page_size > 100:
            raise ItemValidationError("Page size must be between 1 and 100")

        if request.min_price is not None and request.min_price < 0:
            raise ItemValidationError("Minimum price cannot be negative")

        if request.max_price is not None and request.max_price <= 0:
            raise ItemValidationError("Maximum price must be greater than 0")

        if (
            request.min_price is not None
            and request.max_price is not None
            and request.min_price >= request.max_price
        ):
            raise ItemValidationError("Minimum price must be less than maximum price")

        if request.search is not None and len(request.search.strip()) == 0:
            raise ItemValidationError("Search query cannot be empty")
