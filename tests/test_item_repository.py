"""Unit tests for ItemRepository.

This module contains comprehensive unit tests for the ItemRepository class,
including database operations and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.api_server.repositories.item_repository import (
    ItemRepository,
    ItemNotFoundError,
    ItemAccessDeniedError
)
from src.api_server.models.item import Item, ItemCreate, ItemUpdate
from src.api_server.models.user import User


class TestItemRepository:
    """Test cases for ItemRepository."""
    
    @pytest.fixture
    def item_repository(self, test_session: Session) -> ItemRepository:
        """Create ItemRepository instance for testing."""
        return ItemRepository(test_session)
    
    @pytest.mark.asyncio
    async def test_create_success(
        self,
        item_repository: ItemRepository,
        test_user: User,
        sample_item_data: ItemCreate
    ):
        """Test successful item creation."""
        result = item_repository.create(sample_item_data, test_user.id)
        
        assert result is not None
        assert result.id is not None
        assert result.name == sample_item_data.name
        assert result.description == sample_item_data.description
        assert result.price == sample_item_data.price
        assert result.user_id == test_user.id
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_create_invalid_user_id(
        self,
        item_repository: ItemRepository,
        sample_item_data: ItemCreate
    ):
        """Test item creation with invalid user ID."""
        with pytest.raises(IntegrityError) as exc_info:
            item_repository.create(sample_item_data, 999)
        
        assert "user_id 999 does not exist" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_database_error(
        self,
        item_repository: ItemRepository,
        test_user: User,
        sample_item_data: ItemCreate
    ):
        """Test item creation with database error."""
        with patch.object(item_repository.session, 'add') as mock_add:
            mock_add.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(SQLAlchemyError) as exc_info:
                item_repository.create(sample_item_data, test_user.id)
            
            assert "Database error while creating item" in str(exc_info.value)
    
    def test_get_by_id_success(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test successful item retrieval by ID."""
        result = item_repository.get_by_id(test_item.id, test_item.user_id)
        
        assert result is not None
        assert result.id == test_item.id
        assert result.name == test_item.name
        assert result.user_id == test_item.user_id
    
    def test_get_by_id_not_found(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test item retrieval by ID when item not found."""
        result = item_repository.get_by_id(999, test_user.id)
        
        assert result is None
    
    def test_get_by_id_wrong_user(
        self,
        item_repository: ItemRepository,
        test_item: Item,
        multiple_test_users: list[User]
    ):
        """Test item retrieval by ID with wrong user."""
        other_user = multiple_test_users[1]  # Different user
        result = item_repository.get_by_id(test_item.id, other_user.id)
        
        assert result is None
    
    def test_get_by_id_database_error(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test item retrieval by ID with database error."""
        with patch.object(item_repository.session, 'exec') as mock_exec:
            mock_exec.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(SQLAlchemyError) as exc_info:
                item_repository.get_by_id(test_item.id, test_item.user_id)
            
            assert "Database error while retrieving item" in str(exc_info.value)
    
    def test_get_by_id_or_raise_success(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test successful item retrieval by ID or raise."""
        result = item_repository.get_by_id_or_raise(test_item.id, test_item.user_id)
        
        assert result is not None
        assert result.id == test_item.id
        assert result.name == test_item.name
        assert result.user_id == test_item.user_id
    
    def test_get_by_id_or_raise_not_found(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test item retrieval by ID or raise when item not found."""
        with pytest.raises(ItemNotFoundError) as exc_info:
            item_repository.get_by_id_or_raise(999, test_user.id)
        
        assert exc_info.value.item_id == 999
        assert "Item with id 999 not found" in str(exc_info.value)
    
    def test_get_by_id_or_raise_access_denied(
        self,
        item_repository: ItemRepository,
        test_item: Item,
        multiple_test_users: list[User]
    ):
        """Test item retrieval by ID or raise when access denied."""
        other_user = multiple_test_users[1]  # Different user
        
        with pytest.raises(ItemAccessDeniedError) as exc_info:
            item_repository.get_by_id_or_raise(test_item.id, other_user.id)
        
        assert exc_info.value.item_id == test_item.id
        assert exc_info.value.user_id == other_user.id
        assert f"User {other_user.id} does not have access to item {test_item.id}" in str(exc_info.value)
    
    def test_get_all_for_user_success(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test successful retrieval of all items for user."""
        user_id = multiple_test_items[0].user_id
        result = item_repository.get_all_for_user(user_id)
        
        assert len(result) == len(multiple_test_items)
        assert all(item.user_id == user_id for item in result)
        
        # Verify items are sorted by created_at desc (default)
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at
    
    def test_get_all_for_user_with_pagination(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test retrieval of all items for user with pagination."""
        user_id = multiple_test_items[0].user_id
        
        # Get first page
        result_page1 = item_repository.get_all_for_user(user_id, skip=0, limit=2)
        assert len(result_page1) == 2
        
        # Get second page
        result_page2 = item_repository.get_all_for_user(user_id, skip=2, limit=2)
        assert len(result_page2) == 1  # Only 3 items total
        
        # Verify no overlap
        page1_ids = [item.id for item in result_page1]
        page2_ids = [item.id for item in result_page2]
        assert not set(page1_ids).intersection(set(page2_ids))
    
    def test_get_all_for_user_with_sorting(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test retrieval of all items for user with sorting."""
        user_id = multiple_test_items[0].user_id
        
        # Sort by name ascending
        result = item_repository.get_all_for_user(
            user_id, sort_by="name", sort_order="asc"
        )
        
        assert len(result) == len(multiple_test_items)
        
        # Verify sorting
        for i in range(len(result) - 1):
            assert result[i].name <= result[i + 1].name
    
    def test_get_all_for_user_invalid_sort_field(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test retrieval of all items for user with invalid sort field."""
        with pytest.raises(ValueError) as exc_info:
            item_repository.get_all_for_user(
                test_user.id, sort_by="invalid_field"
            )
        
        assert "Invalid sort_by field: invalid_field" in str(exc_info.value)
    
    def test_get_all_for_user_invalid_sort_order(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test retrieval of all items for user with invalid sort order."""
        with pytest.raises(ValueError) as exc_info:
            item_repository.get_all_for_user(
                test_user.id, sort_order="invalid_order"
            )
        
        assert "Invalid sort_order: invalid_order" in str(exc_info.value)
    
    def test_count_for_user_success(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test successful count of items for user."""
        user_id = multiple_test_items[0].user_id
        result = item_repository.count_for_user(user_id)
        
        assert result == len(multiple_test_items)
    
    def test_count_for_user_empty(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test count of items for user with no items."""
        # Create a user with no items
        result = item_repository.count_for_user(999)  # Non-existent user
        
        assert result == 0
    
    def test_count_for_user_database_error(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test count of items for user with database error."""
        with patch.object(item_repository.session, 'exec') as mock_exec:
            mock_exec.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(SQLAlchemyError) as exc_info:
                item_repository.count_for_user(test_user.id)
            
            assert "Database error while counting items" in str(exc_info.value)
    
    def test_update_success(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test successful item update."""
        update_data = ItemUpdate(
            name="Updated Item",
            price=Decimal("199.99")
        )
        
        result = item_repository.update(test_item.id, test_item.user_id, update_data)
        
        assert result is not None
        assert result.id == test_item.id
        assert result.name == "Updated Item"
        assert result.price == Decimal("199.99")
        assert result.description == test_item.description  # Unchanged
        assert result.user_id == test_item.user_id
    
    def test_update_partial(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test partial item update."""
        original_price = test_item.price
        update_data = ItemUpdate(name="Partially Updated Item")
        
        result = item_repository.update(test_item.id, test_item.user_id, update_data)
        
        assert result is not None
        assert result.name == "Partially Updated Item"
        assert result.price == original_price  # Unchanged
    
    def test_update_not_found(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test item update when item not found."""
        update_data = ItemUpdate(name="Updated Item")
        
        with pytest.raises(ItemNotFoundError) as exc_info:
            item_repository.update(999, test_user.id, update_data)
        
        assert exc_info.value.item_id == 999
    
    def test_update_access_denied(
        self,
        item_repository: ItemRepository,
        test_item: Item,
        multiple_test_users: list[User]
    ):
        """Test item update when access denied."""
        other_user = multiple_test_users[1]  # Different user
        update_data = ItemUpdate(name="Updated Item")
        
        with pytest.raises(ItemAccessDeniedError) as exc_info:
            item_repository.update(test_item.id, other_user.id, update_data)
        
        assert exc_info.value.item_id == test_item.id
        assert exc_info.value.user_id == other_user.id
    
    def test_update_database_error(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test item update with database error."""
        update_data = ItemUpdate(name="Updated Item")
        
        with patch.object(item_repository.session, 'commit') as mock_commit:
            mock_commit.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(SQLAlchemyError) as exc_info:
                item_repository.update(test_item.id, test_item.user_id, update_data)
            
            assert "Database error while updating item" in str(exc_info.value)
    
    def test_delete_success(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test successful item deletion."""
        result = item_repository.delete(test_item.id, test_item.user_id)
        
        assert result is True
        
        # Verify item is deleted
        deleted_item = item_repository.get_by_id(test_item.id, test_item.user_id)
        assert deleted_item is None
    
    def test_delete_not_found(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test item deletion when item not found."""
        result = item_repository.delete(999, test_user.id)
        
        assert result is False
    
    def test_delete_access_denied(
        self,
        item_repository: ItemRepository,
        test_item: Item,
        multiple_test_users: list[User]
    ):
        """Test item deletion when access denied."""
        other_user = multiple_test_users[1]  # Different user
        
        with pytest.raises(ItemAccessDeniedError) as exc_info:
            item_repository.delete(test_item.id, other_user.id)
        
        assert exc_info.value.item_id == test_item.id
        assert exc_info.value.user_id == other_user.id
    
    def test_delete_database_error(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test item deletion with database error."""
        with patch.object(item_repository.session, 'commit') as mock_commit:
            mock_commit.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(SQLAlchemyError) as exc_info:
                item_repository.delete(test_item.id, test_item.user_id)
            
            assert "Database error while deleting item" in str(exc_info.value)
    
    def test_search_for_user_success(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test successful item search for user."""
        user_id = multiple_test_items[0].user_id
        
        # Search by name (should find items with "Test Item" in name)
        result = item_repository.search_for_user(user_id, "Test Item")
        
        assert len(result) > 0
        assert all(item.user_id == user_id for item in result)
        assert all("Test Item" in item.name for item in result)
    
    def test_search_for_user_by_description(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test item search for user by description."""
        # Search by description
        result = item_repository.search_for_user(
            test_item.user_id, "test item"
        )
        
        assert len(result) > 0
        assert any(item.id == test_item.id for item in result)
    
    def test_search_for_user_case_insensitive(
        self,
        item_repository: ItemRepository,
        test_item: Item
    ):
        """Test case-insensitive item search for user."""
        # Search with different case
        result = item_repository.search_for_user(
            test_item.user_id, "TEST ITEM"
        )
        
        assert len(result) > 0
        assert any(item.id == test_item.id for item in result)
    
    def test_search_for_user_no_results(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test item search for user with no results."""
        result = item_repository.search_for_user(
            test_user.id, "nonexistent item"
        )
        
        assert len(result) == 0
    
    def test_search_for_user_with_pagination(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test item search for user with pagination."""
        user_id = multiple_test_items[0].user_id
        
        # Search with pagination
        result = item_repository.search_for_user(
            user_id, "Test", skip=0, limit=2
        )
        
        assert len(result) <= 2
    
    def test_search_for_user_database_error(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test item search for user with database error."""
        with patch.object(item_repository.session, 'exec') as mock_exec:
            mock_exec.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(SQLAlchemyError) as exc_info:
                item_repository.search_for_user(test_user.id, "test")
            
            assert "Database error while searching items" in str(exc_info.value)
    
    def test_get_user_items_by_price_range_success(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test successful retrieval of items by price range."""
        user_id = multiple_test_items[0].user_id
        
        # Get items in price range
        result = item_repository.get_user_items_by_price_range(
            user_id, min_price=5.0, max_price=15.0
        )
        
        assert all(item.user_id == user_id for item in result)
        assert all(5.0 <= float(item.price) <= 15.0 for item in result)
    
    def test_get_user_items_by_price_range_min_only(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test retrieval of items by price range with min price only."""
        user_id = multiple_test_items[0].user_id
        
        result = item_repository.get_user_items_by_price_range(
            user_id, min_price=10.0
        )
        
        assert all(item.user_id == user_id for item in result)
        assert all(float(item.price) >= 10.0 for item in result)
    
    def test_get_user_items_by_price_range_max_only(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test retrieval of items by price range with max price only."""
        user_id = multiple_test_items[0].user_id
        
        result = item_repository.get_user_items_by_price_range(
            user_id, max_price=15.0
        )
        
        assert all(item.user_id == user_id for item in result)
        assert all(float(item.price) <= 15.0 for item in result)
    
    def test_get_user_items_by_price_range_invalid_range(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test retrieval of items by price range with invalid range."""
        with pytest.raises(ValueError) as exc_info:
            item_repository.get_user_items_by_price_range(
                test_user.id, min_price=100.0, max_price=50.0
            )
        
        assert "min_price cannot be greater than max_price" in str(exc_info.value)
    
    def test_get_user_items_by_price_range_with_pagination(
        self,
        item_repository: ItemRepository,
        multiple_test_items: list[Item]
    ):
        """Test retrieval of items by price range with pagination."""
        user_id = multiple_test_items[0].user_id
        
        result = item_repository.get_user_items_by_price_range(
            user_id, min_price=0.0, max_price=1000.0, skip=0, limit=2
        )
        
        assert len(result) <= 2
    
    def test_get_user_items_by_price_range_database_error(
        self,
        item_repository: ItemRepository,
        test_user: User
    ):
        """Test retrieval of items by price range with database error."""
        with patch.object(item_repository.session, 'exec') as mock_exec:
            mock_exec.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(SQLAlchemyError) as exc_info:
                item_repository.get_user_items_by_price_range(
                    test_user.id, min_price=10.0, max_price=100.0
                )
            
            assert "Database error while retrieving items by price range" in str(exc_info.value)


class TestItemRepositoryExceptions:
    """Test cases for ItemRepository exception classes."""
    
    def test_item_not_found_error(self):
        """Test ItemNotFoundError exception."""
        error = ItemNotFoundError(123)
        
        assert error.item_id == 123
        assert "Item with id 123 not found" in str(error)
    
    def test_item_access_denied_error(self):
        """Test ItemAccessDeniedError exception."""
        error = ItemAccessDeniedError(123, 456)
        
        assert error.item_id == 123
        assert error.user_id == 456
        assert "User 456 does not have access to item 123" in str(error)


class TestItemRepositoryIntegration:
    """Integration tests for ItemRepository with real database operations."""
    
    @pytest.mark.asyncio
    async def test_create_and_retrieve_item(
        self,
        item_repository: ItemRepository,
        test_user: User,
        test_data_factory
    ):
        """Test creating and retrieving an item."""
        # Create item data
        item_data = test_data_factory.create_item_data(
            name="Integration Test Item",
            description="Integration test description",
            price=Decimal("25.99")
        )
        
        # Create item
        created_item = item_repository.create(item_data, test_user.id)
        assert created_item is not None
        assert created_item.id is not None
        
        # Retrieve by ID
        retrieved_item = item_repository.get_by_id(created_item.id, test_user.id)
        assert retrieved_item is not None
        assert retrieved_item.name == item_data.name
        assert retrieved_item.price == item_data.price
        
        # Retrieve by ID or raise
        retrieved_by_id_or_raise = item_repository.get_by_id_or_raise(
            created_item.id, test_user.id
        )
        assert retrieved_by_id_or_raise is not None
        assert retrieved_by_id_or_raise.id == created_item.id
    
    @pytest.mark.asyncio
    async def test_update_and_verify_item(
        self,
        item_repository: ItemRepository,
        test_user: User,
        test_data_factory
    ):
        """Test updating and verifying item changes."""
        # Create item
        item_data = test_data_factory.create_item_data(
            name="Original Item",
            price=Decimal("10.00")
        )
        created_item = item_repository.create(item_data, test_user.id)
        
        # Update item
        update_data = ItemUpdate(
            name="Updated Item",
            price=Decimal("20.00")
        )
        updated_item = item_repository.update(
            created_item.id, test_user.id, update_data
        )
        
        assert updated_item is not None
        assert updated_item.name == "Updated Item"
        assert updated_item.price == Decimal("20.00")
        assert updated_item.description == item_data.description  # Unchanged
        
        # Verify changes persist
        retrieved_item = item_repository.get_by_id(created_item.id, test_user.id)
        assert retrieved_item.name == "Updated Item"
        assert retrieved_item.price == Decimal("20.00")
    
    @pytest.mark.asyncio
    async def test_delete_and_verify_item(
        self,
        item_repository: ItemRepository,
        test_user: User,
        test_data_factory
    ):
        """Test deleting and verifying item removal."""
        # Create item
        item_data = test_data_factory.create_item_data(
            name="To Be Deleted",
            price=Decimal("5.00")
        )
        created_item = item_repository.create(item_data, test_user.id)
        
        # Verify item exists
        assert item_repository.get_by_id(created_item.id, test_user.id) is not None
        
        # Delete item
        delete_result = item_repository.delete(created_item.id, test_user.id)
        assert delete_result is True
        
        # Verify item is deleted
        assert item_repository.get_by_id(created_item.id, test_user.id) is None
    
    @pytest.mark.asyncio
    async def test_search_and_filter_items(
        self,
        item_repository: ItemRepository,
        test_user: User,
        test_data_factory
    ):
        """Test searching and filtering items."""
        # Create multiple items
        items_data = [
            test_data_factory.create_item_data(
                name="Laptop Computer",
                description="High-performance laptop",
                price=Decimal("999.99")
            ),
            test_data_factory.create_item_data(
                name="Desktop Computer",
                description="Gaming desktop",
                price=Decimal("1299.99")
            ),
            test_data_factory.create_item_data(
                name="Mobile Phone",
                description="Smartphone device",
                price=Decimal("599.99")
            )
        ]
        
        created_items = []
        for item_data in items_data:
            created_item = item_repository.create(item_data, test_user.id)
            created_items.append(created_item)
        
        # Test search by name
        search_results = item_repository.search_for_user(test_user.id, "Computer")
        assert len(search_results) == 2
        assert all("Computer" in item.name for item in search_results)
        
        # Test search by description
        search_results = item_repository.search_for_user(test_user.id, "laptop")
        assert len(search_results) == 1
        assert search_results[0].name == "Laptop Computer"
        
        # Test price range filter
        price_results = item_repository.get_user_items_by_price_range(
            test_user.id, min_price=600.0, max_price=1000.0
        )
        assert len(price_results) == 2  # Laptop and Mobile Phone
        
        # Test count
        total_count = item_repository.count_for_user(test_user.id)
        assert total_count >= 3  # At least the 3 we created