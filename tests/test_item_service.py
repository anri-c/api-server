"""Unit tests for ItemService.

This module contains comprehensive unit tests for the ItemService class,
including item management operations and error handling.
"""

from decimal import Decimal
from enum import Enum
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from src.api_server.models.item import Item, ItemCreate, ItemUpdate
from src.api_server.models.user import User
from src.api_server.repositories.item_repository import (
    ItemAccessDeniedError,
    ItemNotFoundError,
    ItemRepository,
)
from src.api_server.repositories.user_repository import UserRepository
from src.api_server.schemas.item_schemas import (
    ItemListRequest,
    ItemListResponse,
    ItemResponse,
    ItemWithUser,
    UserSummary,
)
from src.api_server.services.item_service import (
    ItemAccessDeniedServiceError,
    ItemNotFoundServiceError,
    ItemService,
    ItemServiceError,
    ItemValidationError,
)


# Mock enums for testing
class SortBy(Enum):
    CREATED_AT = "created_at"
    NAME = "name"
    PRICE = "price"


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


class TestItemService:
    """Test cases for ItemService."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_item_repository(self) -> Mock:
        """Create mock item repository."""
        return Mock(spec=ItemRepository)

    @pytest.fixture
    def mock_user_repository(self) -> Mock:
        """Create mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def item_service(self, mock_session: Mock) -> ItemService:
        """Create ItemService instance for testing."""
        return ItemService(mock_session)

    @pytest.fixture
    def sample_item(self) -> Item:
        """Create sample item for testing."""
        return Item(
            id=1,
            name="Test Item",
            description="Test description",
            price=Decimal("99.99"),
            user_id=1,
        )

    @pytest.fixture
    def sample_user(self) -> User:
        """Create sample user for testing."""
        return User(
            id=1,
            line_user_id="test_line_user_123",
            display_name="Test User",
            picture_url="https://example.com/profile.jpg",
            email="test@example.com",
        )

    @pytest.fixture
    def sample_item_create(self) -> ItemCreate:
        """Create sample item creation data."""
        return ItemCreate(
            name="New Item", description="New item description", price=Decimal("49.99")
        )

    @pytest.fixture
    def sample_list_request(self) -> ItemListRequest:
        """Create sample item list request."""
        return ItemListRequest(
            page=1, page_size=20, sort_by=SortBy.CREATED_AT, sort_order=SortOrder.DESC
        )

    @pytest.mark.asyncio
    async def test_create_item_success(
        self,
        item_service: ItemService,
        mock_item_repository: Mock,
        mock_user_repository: Mock,
        sample_item_create: ItemCreate,
        sample_item: Item,
        sample_user: User,
    ):
        """Test successful item creation."""
        # Setup mocks
        item_service.item_repository = mock_item_repository
        item_service.user_repository = mock_user_repository
        mock_user_repository.get_by_id = AsyncMock(return_value=sample_user)
        mock_item_repository.create = Mock(return_value=sample_item)

        # Test item creation
        result = await item_service.create_item(sample_item_create, 1)

        # Assertions
        assert isinstance(result, ItemResponse)
        assert result.name == sample_item.name
        assert result.price == sample_item.price
        assert result.user_id == sample_item.user_id

        # Verify repository calls
        mock_user_repository.get_by_id.assert_called_once_with(1)
        mock_item_repository.create.assert_called_once_with(sample_item_create, 1)

    @pytest.mark.asyncio
    async def test_create_item_user_not_found(
        self,
        item_service: ItemService,
        mock_user_repository: Mock,
        sample_item_create: ItemCreate,
    ):
        """Test item creation when user not found."""
        # Setup mocks
        item_service.user_repository = mock_user_repository
        mock_user_repository.get_by_id = AsyncMock(return_value=None)

        # Test item creation with non-existent user
        with pytest.raises(ItemServiceError) as exc_info:
            await item_service.create_item(sample_item_create, 999)

        assert exc_info.value.status_code == 404
        assert "User with id 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_item_validation_error(
        self, item_service: ItemService, mock_user_repository: Mock, sample_user: User
    ):
        """Test item creation with validation error."""
        # Setup mocks
        item_service.user_repository = mock_user_repository
        mock_user_repository.get_by_id = AsyncMock(return_value=sample_user)

        # Test with invalid item data
        invalid_item = ItemCreate(
            name="",  # Empty name should fail validation
            description="Test",
            price=Decimal("10.00"),
        )

        with pytest.raises(ItemValidationError) as exc_info:
            await item_service.create_item(invalid_item, 1)

        assert "Item name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_item_database_error(
        self,
        item_service: ItemService,
        mock_item_repository: Mock,
        mock_user_repository: Mock,
        sample_item_create: ItemCreate,
        sample_user: User,
    ):
        """Test item creation with database error."""
        # Setup mocks
        item_service.item_repository = mock_item_repository
        item_service.user_repository = mock_user_repository
        mock_user_repository.get_by_id = AsyncMock(return_value=sample_user)
        mock_item_repository.create = Mock(
            side_effect=SQLAlchemyError("Database error")
        )

        # Test item creation with database error
        with pytest.raises(ItemServiceError) as exc_info:
            await item_service.create_item(sample_item_create, 1)

        assert exc_info.value.status_code == 500
        assert "Failed to create item" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_item_by_id_success(
        self, item_service: ItemService, mock_item_repository: Mock, sample_item: Item
    ):
        """Test successful item retrieval by ID."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_by_id = Mock(return_value=sample_item)

        # Test item retrieval
        result = await item_service.get_item_by_id(1, 1)

        # Assertions
        assert result is not None
        assert isinstance(result, ItemResponse)
        assert result.id == sample_item.id
        assert result.name == sample_item.name

        # Verify repository call
        mock_item_repository.get_by_id.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_get_item_by_id_not_found(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test item retrieval by ID when item not found."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_by_id = Mock(return_value=None)

        # Test item retrieval
        result = await item_service.get_item_by_id(999, 1)

        # Assertions
        assert result is None
        mock_item_repository.get_by_id.assert_called_once_with(999, 1)

    @pytest.mark.asyncio
    async def test_get_item_by_id_or_raise_success(
        self, item_service: ItemService, mock_item_repository: Mock, sample_item: Item
    ):
        """Test successful item retrieval by ID or raise."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_by_id_or_raise = Mock(return_value=sample_item)

        # Test item retrieval
        result = await item_service.get_item_by_id_or_raise(1, 1)

        # Assertions
        assert isinstance(result, ItemResponse)
        assert result.id == sample_item.id

        # Verify repository call
        mock_item_repository.get_by_id_or_raise.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_get_item_by_id_or_raise_not_found(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test item retrieval by ID or raise when item not found."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_by_id_or_raise = Mock(
            side_effect=ItemNotFoundError("Item not found")
        )

        # Test item retrieval
        with pytest.raises(ItemNotFoundServiceError) as exc_info:
            await item_service.get_item_by_id_or_raise(999, 1)

        assert "Item with id 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_item_by_id_or_raise_access_denied(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test item retrieval by ID or raise when access denied."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_by_id_or_raise = Mock(
            side_effect=ItemAccessDeniedError("Access denied")
        )

        # Test item retrieval
        with pytest.raises(ItemAccessDeniedServiceError) as exc_info:
            await item_service.get_item_by_id_or_raise(1, 2)

        assert "User 2 does not have access to item 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_items_for_user_success(
        self,
        item_service: ItemService,
        mock_item_repository: Mock,
        sample_list_request: ItemListRequest,
        sample_item: Item,
    ):
        """Test successful retrieval of items for user."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_all_for_user = Mock(return_value=[sample_item])
        mock_item_repository.count_for_user = Mock(return_value=1)

        # Test items retrieval
        result = await item_service.get_items_for_user(1, sample_list_request)

        # Assertions
        assert isinstance(result, ItemListResponse)
        assert len(result.items) == 1
        assert result.total == 1
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 1

        # Verify repository calls
        mock_item_repository.get_all_for_user.assert_called_once_with(
            user_id=1, skip=0, limit=20, sort_by="created_at", sort_order="desc"
        )
        mock_item_repository.count_for_user.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_items_for_user_with_search(
        self, item_service: ItemService, mock_item_repository: Mock, sample_item: Item
    ):
        """Test retrieval of items for user with search."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.search_for_user = Mock(return_value=[sample_item])
        mock_item_repository.count_for_user = Mock(return_value=1)

        # Create request with search
        request = ItemListRequest(
            page=1,
            page_size=20,
            search="test",
            sort_by=SortBy.CREATED_AT,
            sort_order=SortOrder.DESC,
        )

        # Test items retrieval with search
        result = await item_service.get_items_for_user(1, request)

        # Assertions
        assert isinstance(result, ItemListResponse)
        assert len(result.items) == 1

        # Verify search was called
        mock_item_repository.search_for_user.assert_called_once_with(
            user_id=1, query="test", skip=0, limit=20
        )

    @pytest.mark.asyncio
    async def test_get_items_for_user_with_price_range(
        self, item_service: ItemService, mock_item_repository: Mock, sample_item: Item
    ):
        """Test retrieval of items for user with price range."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_user_items_by_price_range = Mock(
            return_value=[sample_item]
        )
        mock_item_repository.count_for_user = Mock(return_value=1)

        # Create request with price range
        request = ItemListRequest(
            page=1,
            page_size=20,
            min_price=Decimal("10.00"),
            max_price=Decimal("100.00"),
            sort_by=SortBy.CREATED_AT,
            sort_order=SortOrder.DESC,
        )

        # Test items retrieval with price range
        result = await item_service.get_items_for_user(1, request)

        # Assertions
        assert isinstance(result, ItemListResponse)
        assert len(result.items) == 1

        # Verify price range search was called
        mock_item_repository.get_user_items_by_price_range.assert_called_once_with(
            user_id=1, min_price=10.0, max_price=100.0, skip=0, limit=20
        )

    @pytest.mark.asyncio
    async def test_get_items_for_user_invalid_request(self, item_service: ItemService):
        """Test retrieval of items for user with invalid request."""
        # Create invalid request
        invalid_request = ItemListRequest(
            page=0,  # Invalid page number
            page_size=20,
            sort_by=SortBy.CREATED_AT,
            sort_order=SortOrder.DESC,
        )

        # Test items retrieval with invalid request
        with pytest.raises(ItemValidationError) as exc_info:
            await item_service.get_items_for_user(1, invalid_request)

        assert "Page number must be at least 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_item_success(
        self, item_service: ItemService, mock_item_repository: Mock, sample_item: Item
    ):
        """Test successful item update."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        updated_item = Item(**sample_item.dict())
        updated_item.name = "Updated Item"
        mock_item_repository.update = Mock(return_value=updated_item)

        # Test item update
        update_data = ItemUpdate(name="Updated Item")
        result = await item_service.update_item(1, 1, update_data)

        # Assertions
        assert isinstance(result, ItemResponse)
        assert result.name == "Updated Item"

        # Verify repository call
        mock_item_repository.update.assert_called_once_with(1, 1, update_data)

    @pytest.mark.asyncio
    async def test_update_item_not_found(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test item update when item not found."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.update = Mock(
            side_effect=ItemNotFoundError("Item not found")
        )

        # Test item update
        update_data = ItemUpdate(name="Updated Item")
        with pytest.raises(ItemNotFoundServiceError) as exc_info:
            await item_service.update_item(999, 1, update_data)

        assert "Item with id 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_item_validation_error(self, item_service: ItemService):
        """Test item update with validation error."""
        # Test with empty update data
        update_data = ItemUpdate()
        with pytest.raises(ItemValidationError) as exc_info:
            await item_service.update_item(1, 1, update_data)

        assert "At least one field must be provided for update" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_item_success(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test successful item deletion."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.delete = Mock(return_value=True)

        # Test item deletion
        result = await item_service.delete_item(1, 1)

        # Assertions
        assert result is True
        mock_item_repository.delete.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_delete_item_not_found(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test item deletion when item not found."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.delete = Mock(return_value=False)

        # Test item deletion
        result = await item_service.delete_item(999, 1)

        # Assertions
        assert result is False
        mock_item_repository.delete.assert_called_once_with(999, 1)

    @pytest.mark.asyncio
    async def test_delete_item_access_denied(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test item deletion when access denied."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.delete = Mock(
            side_effect=ItemAccessDeniedError("Access denied")
        )

        # Test item deletion
        with pytest.raises(ItemAccessDeniedServiceError) as exc_info:
            await item_service.delete_item(1, 2)

        assert "User 2 does not have access to item 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_item_with_user_success(
        self,
        item_service: ItemService,
        mock_item_repository: Mock,
        mock_user_repository: Mock,
        sample_item: Item,
        sample_user: User,
    ):
        """Test successful retrieval of item with user information."""
        # Setup mocks
        item_service.item_repository = mock_item_repository
        item_service.user_repository = mock_user_repository
        mock_item_repository.get_by_id = Mock(return_value=sample_item)
        mock_user_repository.get_by_id = AsyncMock(return_value=sample_user)

        # Test item with user retrieval
        result = await item_service.get_item_with_user(1, 1)

        # Assertions
        assert result is not None
        assert isinstance(result, ItemWithUser)
        assert result.id == sample_item.id
        assert result.user is not None
        assert isinstance(result.user, UserSummary)
        assert result.user.id == sample_user.id
        assert result.user.display_name == sample_user.display_name

        # Verify repository calls
        mock_item_repository.get_by_id.assert_called_once_with(1, 1)
        mock_user_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_item_with_user_item_not_found(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test retrieval of item with user when item not found."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.get_by_id = Mock(return_value=None)

        # Test item with user retrieval
        result = await item_service.get_item_with_user(999, 1)

        # Assertions
        assert result is None

    @pytest.mark.asyncio
    async def test_search_items_success(
        self, item_service: ItemService, mock_item_repository: Mock, sample_item: Item
    ):
        """Test successful item search."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.search_for_user = Mock(return_value=[sample_item])

        # Test item search
        result = await item_service.search_items(1, "test query", 1, 20)

        # Assertions
        assert isinstance(result, ItemListResponse)
        assert len(result.items) == 1
        assert result.page == 1
        assert result.page_size == 20

        # Verify repository call
        mock_item_repository.search_for_user.assert_called_once_with(
            user_id=1, query="test query", skip=0, limit=20
        )

    @pytest.mark.asyncio
    async def test_search_items_empty_query(self, item_service: ItemService):
        """Test item search with empty query."""
        # Test with empty query
        with pytest.raises(ItemValidationError) as exc_info:
            await item_service.search_items(1, "", 1, 20)

        assert "Search query cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_items_invalid_pagination(self, item_service: ItemService):
        """Test item search with invalid pagination."""
        # Test with invalid page
        with pytest.raises(ItemValidationError) as exc_info:
            await item_service.search_items(1, "test", 0, 20)

        assert "Page number must be at least 1" in str(exc_info.value)

        # Test with invalid page size
        with pytest.raises(ItemValidationError) as exc_info:
            await item_service.search_items(1, "test", 1, 101)

        assert "Page size must be between 1 and 100" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_item_count_success(
        self, item_service: ItemService, mock_item_repository: Mock
    ):
        """Test successful user item count retrieval."""
        # Setup mock
        item_service.item_repository = mock_item_repository
        mock_item_repository.count_for_user = Mock(return_value=5)

        # Test item count
        result = await item_service.get_user_item_count(1)

        # Assertions
        assert result == 5
        mock_item_repository.count_for_user.assert_called_once_with(1)


class TestItemServiceValidation:
    """Test cases for ItemService validation methods."""

    @pytest.fixture
    def item_service(self, mock_session: Mock) -> ItemService:
        """Create ItemService instance for testing."""
        return ItemService(mock_session)

    def test_validate_item_create_data_success(self, item_service: ItemService):
        """Test successful item create data validation."""
        valid_data = ItemCreate(
            name="Valid Item", description="Valid description", price=Decimal("99.99")
        )

        # Should not raise any exception
        item_service._validate_item_create_data(valid_data)

    def test_validate_item_create_data_empty_name(self, item_service: ItemService):
        """Test item create data validation with empty name."""
        invalid_data = ItemCreate(
            name="", description="Valid description", price=Decimal("99.99")
        )

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_item_create_data(invalid_data)

        assert "Item name cannot be empty" in str(exc_info.value)

    def test_validate_item_create_data_invalid_price(self, item_service: ItemService):
        """Test item create data validation with invalid price."""
        invalid_data = ItemCreate(
            name="Valid Item", description="Valid description", price=Decimal("0")
        )

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_item_create_data(invalid_data)

        assert "Item price must be greater than 0" in str(exc_info.value)

    def test_validate_item_create_data_price_too_high(self, item_service: ItemService):
        """Test item create data validation with price too high."""
        invalid_data = ItemCreate(
            name="Valid Item",
            description="Valid description",
            price=Decimal("1000001.00"),
        )

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_item_create_data(invalid_data)

        assert "Item price cannot exceed 1,000,000.00" in str(exc_info.value)

    def test_validate_item_create_data_description_too_long(
        self, item_service: ItemService
    ):
        """Test item create data validation with description too long."""
        invalid_data = ItemCreate(
            name="Valid Item",
            description="x" * 1001,  # Too long
            price=Decimal("99.99"),
        )

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_item_create_data(invalid_data)

        assert "Item description cannot exceed 1000 characters" in str(exc_info.value)

    def test_validate_item_update_data_success(self, item_service: ItemService):
        """Test successful item update data validation."""
        valid_data = ItemUpdate(name="Updated Item")

        # Should not raise any exception
        item_service._validate_item_update_data(valid_data)

    def test_validate_item_update_data_empty(self, item_service: ItemService):
        """Test item update data validation with empty data."""
        empty_data = ItemUpdate()

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_item_update_data(empty_data)

        assert "At least one field must be provided for update" in str(exc_info.value)

    def test_validate_list_request_success(self, item_service: ItemService):
        """Test successful list request validation."""
        valid_request = ItemListRequest(
            page=1, page_size=20, sort_by=SortBy.CREATED_AT, sort_order=SortOrder.DESC
        )

        # Should not raise any exception
        item_service._validate_list_request(valid_request)

    def test_validate_list_request_invalid_page(self, item_service: ItemService):
        """Test list request validation with invalid page."""
        invalid_request = ItemListRequest(
            page=0, page_size=20, sort_by=SortBy.CREATED_AT, sort_order=SortOrder.DESC
        )

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_list_request(invalid_request)

        assert "Page number must be at least 1" in str(exc_info.value)

    def test_validate_list_request_invalid_page_size(self, item_service: ItemService):
        """Test list request validation with invalid page size."""
        invalid_request = ItemListRequest(
            page=1, page_size=101, sort_by=SortBy.CREATED_AT, sort_order=SortOrder.DESC
        )

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_list_request(invalid_request)

        assert "Page size must be between 1 and 100" in str(exc_info.value)

    def test_validate_list_request_invalid_price_range(self, item_service: ItemService):
        """Test list request validation with invalid price range."""
        invalid_request = ItemListRequest(
            page=1,
            page_size=20,
            min_price=Decimal("100.00"),
            max_price=Decimal("50.00"),  # Max less than min
            sort_by=SortBy.CREATED_AT,
            sort_order=SortOrder.DESC,
        )

        with pytest.raises(ItemValidationError) as exc_info:
            item_service._validate_list_request(invalid_request)

        assert "Minimum price must be less than maximum price" in str(exc_info.value)


class TestItemServiceExceptions:
    """Test cases for ItemService exception classes."""

    def test_item_service_error(self):
        """Test ItemServiceError exception."""
        original_error = Exception("Original error")
        error = ItemServiceError("Service error", 400, original_error)

        assert error.message == "Service error"
        assert error.status_code == 400
        assert error.original_error == original_error
        assert str(error) == "Service error"

    def test_item_not_found_service_error(self):
        """Test ItemNotFoundServiceError exception."""
        error = ItemNotFoundServiceError(123)

        assert error.status_code == 404
        assert "Item with id 123 not found" in str(error)
        assert isinstance(error, ItemServiceError)

    def test_item_access_denied_service_error(self):
        """Test ItemAccessDeniedServiceError exception."""
        error = ItemAccessDeniedServiceError(123, 456)

        assert error.status_code == 403
        assert "User 456 does not have access to item 123" in str(error)
        assert isinstance(error, ItemServiceError)

    def test_item_validation_error(self):
        """Test ItemValidationError exception."""
        error = ItemValidationError("Validation failed")

        assert error.status_code == 400
        assert "Validation failed" in str(error)
        assert isinstance(error, ItemServiceError)
