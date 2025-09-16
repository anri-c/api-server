"""Integration tests for items endpoints.

This module contains comprehensive integration tests for the items API endpoints,
including CRUD operations, authentication, authorization, and error handling.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api_server.models.item import Item
from src.api_server.models.user import User


class TestItemsEndpoints:
    """Integration tests for items endpoints."""
    
    def test_get_items_success(
        self,
        client: TestClient,
        test_user: User,
        multiple_test_items: list[Item],
        auth_headers: dict[str, str]
    ):
        """Test successful retrieval of items."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.get("/api/items/", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert "total_pages" in data
            
            assert len(data["items"]) == len(multiple_test_items)
            assert data["total"] == len(multiple_test_items)
            assert data["page"] == 1
            assert data["page_size"] == 20
    
    def test_get_items_with_pagination(
        self,
        client: TestClient,
        test_user: User,
        multiple_test_items: list[Item],
        auth_headers: dict[str, str]
    ):
        """Test retrieval of items with pagination."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.get(
                "/api/items/?page=1&page_size=2",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data["items"]) == 2
            assert data["page"] == 1
            assert data["page_size"] == 2
            assert data["total_pages"] == 2  # 3 items / 2 per page = 2 pages
    
    def test_get_items_with_search(
        self,
        client: TestClient,
        test_user: User,
        multiple_test_items: list[Item],
        auth_headers: dict[str, str]
    ):
        """Test retrieval of items with search."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.get(
                "/api/items/?search=Test Item",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data["items"]) > 0
            # All returned items should contain "Test Item" in name or description
            for item in data["items"]:
                assert "Test Item" in item["name"] or "Test Item" in (item["description"] or "")
    
    def test_get_items_with_price_range(
        self,
        client: TestClient,
        test_user: User,
        multiple_test_items: list[Item],
        auth_headers: dict[str, str]
    ):
        """Test retrieval of items with price range."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.get(
                "/api/items/?min_price=5.00&max_price=15.00",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # All returned items should be within price range
            for item in data["items"]:
                price = float(item["price"])
                assert 5.00 <= price <= 15.00
    
    def test_get_items_with_sorting(
        self,
        client: TestClient,
        test_user: User,
        multiple_test_items: list[Item],
        auth_headers: dict[str, str]
    ):
        """Test retrieval of items with sorting."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.get(
                "/api/items/?sort_by=name&sort_order=asc",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify items are sorted by name ascending
            names = [item["name"] for item in data["items"]]
            assert names == sorted(names)
    
    def test_get_items_unauthorized(self, client: TestClient):
        """Test retrieval of items without authentication."""
        response = client.get("/api/items/")
        
        assert response.status_code == 401
    
    def test_get_items_invalid_token(
        self,
        client: TestClient,
        invalid_auth_headers: dict[str, str]
    ):
        """Test retrieval of items with invalid token."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.side_effect = Exception("Invalid token")
            
            response = client.get("/api/items/", headers=invalid_auth_headers)
            
            assert response.status_code == 401
    
    def test_create_item_success(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test successful item creation."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            item_data = {
                "name": "New Test Item",
                "description": "A new test item",
                "price": "29.99"
            }
            
            response = client.post("/api/items/", json=item_data, headers=auth_headers)
            
            assert response.status_code == 201
            data = response.json()
            
            assert data["name"] == item_data["name"]
            assert data["description"] == item_data["description"]
            assert data["price"] == item_data["price"]
            assert data["user_id"] == test_user.id
            assert "id" in data
            assert "created_at" in data
    
    def test_create_item_invalid_data(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test item creation with invalid data."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with empty name
            invalid_data = {
                "name": "",
                "description": "Test description",
                "price": "10.00"
            }
            
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    def test_create_item_missing_required_fields(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test item creation with missing required fields."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with missing name
            invalid_data = {
                "description": "Test description",
                "price": "10.00"
            }
            
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            
            assert response.status_code == 422  # Validation error
    
    def test_create_item_unauthorized(self, client: TestClient):
        """Test item creation without authentication."""
        item_data = {
            "name": "Test Item",
            "description": "Test description",
            "price": "10.00"
        }
        
        response = client.post("/api/items/", json=item_data)
        
        assert response.status_code == 401
    
    def test_get_item_by_id_success(
        self,
        client: TestClient,
        test_user: User,
        test_item: Item,
        auth_headers: dict[str, str]
    ):
        """Test successful retrieval of item by ID."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.get(f"/api/items/{test_item.id}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == test_item.id
            assert data["name"] == test_item.name
            assert data["description"] == test_item.description
            assert str(data["price"]) == str(test_item.price)
            assert data["user_id"] == test_item.user_id
    
    def test_get_item_by_id_not_found(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test retrieval of item by ID when item not found."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.get("/api/items/999", headers=auth_headers)
            
            assert response.status_code == 404
            data = response.json()
            assert "error" in data
    
    def test_get_item_by_id_access_denied(
        self,
        client: TestClient,
        test_item: Item,
        multiple_test_users: list[User],
        auth_headers: dict[str, str]
    ):
        """Test retrieval of item by ID when access denied."""
        other_user = multiple_test_users[1]  # Different user
        
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = other_user.id
            
            response = client.get(f"/api/items/{test_item.id}", headers=auth_headers)
            
            assert response.status_code == 403
            data = response.json()
            assert "error" in data
    
    def test_get_item_by_id_unauthorized(self, client: TestClient, test_item: Item):
        """Test retrieval of item by ID without authentication."""
        response = client.get(f"/api/items/{test_item.id}")
        
        assert response.status_code == 401
    
    def test_update_item_success(
        self,
        client: TestClient,
        test_user: User,
        test_item: Item,
        auth_headers: dict[str, str]
    ):
        """Test successful item update."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            update_data = {
                "name": "Updated Item Name",
                "price": "199.99"
            }
            
            response = client.put(
                f"/api/items/{test_item.id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == update_data["name"]
            assert data["price"] == update_data["price"]
            assert data["description"] == test_item.description  # Unchanged
            assert data["user_id"] == test_item.user_id
    
    def test_update_item_partial(
        self,
        client: TestClient,
        test_user: User,
        test_item: Item,
        auth_headers: dict[str, str]
    ):
        """Test partial item update."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            update_data = {
                "name": "Partially Updated Name"
            }
            
            response = client.put(
                f"/api/items/{test_item.id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == update_data["name"]
            assert str(data["price"]) == str(test_item.price)  # Unchanged
            assert data["description"] == test_item.description  # Unchanged
    
    def test_update_item_not_found(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test item update when item not found."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            update_data = {
                "name": "Updated Name"
            }
            
            response = client.put(
                "/api/items/999",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 404
            data = response.json()
            assert "error" in data
    
    def test_update_item_access_denied(
        self,
        client: TestClient,
        test_item: Item,
        multiple_test_users: list[User],
        auth_headers: dict[str, str]
    ):
        """Test item update when access denied."""
        other_user = multiple_test_users[1]  # Different user
        
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = other_user.id
            
            update_data = {
                "name": "Updated Name"
            }
            
            response = client.put(
                f"/api/items/{test_item.id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            data = response.json()
            assert "error" in data
    
    def test_update_item_invalid_data(
        self,
        client: TestClient,
        test_user: User,
        test_item: Item,
        auth_headers: dict[str, str]
    ):
        """Test item update with invalid data."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with invalid price
            invalid_data = {
                "price": "-10.00"  # Negative price
            }
            
            response = client.put(
                f"/api/items/{test_item.id}",
                json=invalid_data,
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    def test_update_item_unauthorized(self, client: TestClient, test_item: Item):
        """Test item update without authentication."""
        update_data = {
            "name": "Updated Name"
        }
        
        response = client.put(f"/api/items/{test_item.id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_delete_item_success(
        self,
        client: TestClient,
        test_user: User,
        test_item: Item,
        auth_headers: dict[str, str]
    ):
        """Test successful item deletion."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.delete(f"/api/items/{test_item.id}", headers=auth_headers)
            
            assert response.status_code == 204
            
            # Verify item is deleted by trying to get it
            get_response = client.get(f"/api/items/{test_item.id}", headers=auth_headers)
            assert get_response.status_code == 404
    
    def test_delete_item_not_found(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test item deletion when item not found."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            response = client.delete("/api/items/999", headers=auth_headers)
            
            assert response.status_code == 404
            data = response.json()
            assert "error" in data
    
    def test_delete_item_access_denied(
        self,
        client: TestClient,
        test_item: Item,
        multiple_test_users: list[User],
        auth_headers: dict[str, str]
    ):
        """Test item deletion when access denied."""
        other_user = multiple_test_users[1]  # Different user
        
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = other_user.id
            
            response = client.delete(f"/api/items/{test_item.id}", headers=auth_headers)
            
            assert response.status_code == 403
            data = response.json()
            assert "error" in data
    
    def test_delete_item_unauthorized(self, client: TestClient, test_item: Item):
        """Test item deletion without authentication."""
        response = client.delete(f"/api/items/{test_item.id}")
        
        assert response.status_code == 401


class TestItemsEndpointsValidation:
    """Validation tests for items endpoints."""
    
    def test_create_item_price_validation(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test item creation with various price validations."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with zero price
            invalid_data = {
                "name": "Test Item",
                "price": "0.00"
            }
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            assert response.status_code == 400
            
            # Test with negative price
            invalid_data = {
                "name": "Test Item",
                "price": "-10.00"
            }
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            assert response.status_code == 400
            
            # Test with very high price
            invalid_data = {
                "name": "Test Item",
                "price": "1000001.00"
            }
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            assert response.status_code == 400
    
    def test_create_item_name_validation(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test item creation with name validation."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with empty name
            invalid_data = {
                "name": "",
                "price": "10.00"
            }
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            assert response.status_code == 400
            
            # Test with whitespace-only name
            invalid_data = {
                "name": "   ",
                "price": "10.00"
            }
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            assert response.status_code == 400
            
            # Test with very long name
            invalid_data = {
                "name": "x" * 101,  # Exceeds max length
                "price": "10.00"
            }
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            assert response.status_code == 422  # Pydantic validation error
    
    def test_create_item_description_validation(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test item creation with description validation."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with very long description
            invalid_data = {
                "name": "Test Item",
                "description": "x" * 1001,  # Exceeds max length
                "price": "10.00"
            }
            response = client.post("/api/items/", json=invalid_data, headers=auth_headers)
            assert response.status_code == 400
    
    def test_get_items_pagination_validation(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test items retrieval with pagination validation."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with invalid page number
            response = client.get("/api/items/?page=0", headers=auth_headers)
            assert response.status_code == 400
            
            # Test with invalid page size
            response = client.get("/api/items/?page_size=0", headers=auth_headers)
            assert response.status_code == 400
            
            response = client.get("/api/items/?page_size=101", headers=auth_headers)
            assert response.status_code == 400
    
    def test_get_items_price_range_validation(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test items retrieval with price range validation."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Test with invalid price range (min > max)
            response = client.get(
                "/api/items/?min_price=100.00&max_price=50.00",
                headers=auth_headers
            )
            assert response.status_code == 400
            
            # Test with negative min price
            response = client.get("/api/items/?min_price=-10.00", headers=auth_headers)
            assert response.status_code == 400
            
            # Test with zero max price
            response = client.get("/api/items/?max_price=0.00", headers=auth_headers)
            assert response.status_code == 400


class TestItemsEndpointsErrorHandling:
    """Error handling tests for items endpoints."""
    
    def test_database_error_handling(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test handling of database errors."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            with patch("src.api_server.services.item_service.ItemService.get_items_for_user") as mock_service:
                mock_service.side_effect = Exception("Database connection failed")
                
                response = client.get("/api/items/", headers=auth_headers)
                
                assert response.status_code == 500
                data = response.json()
                assert "error" in data
    
    def test_invalid_json_handling(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test handling of invalid JSON in request body."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            # Send invalid JSON
            response = client.post(
                "/api/items/",
                data="invalid json",
                headers={**auth_headers, "Content-Type": "application/json"}
            )
            
            assert response.status_code == 422
    
    def test_missing_content_type(
        self,
        client: TestClient,
        test_user: User,
        auth_headers: dict[str, str]
    ):
        """Test handling of missing content type."""
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = test_user.id
            
            item_data = {
                "name": "Test Item",
                "price": "10.00"
            }
            
            # Remove content-type header
            headers = {k: v for k, v in auth_headers.items() if k.lower() != "content-type"}
            
            response = client.post("/api/items/", json=item_data, headers=headers)
            
            # FastAPI should handle this gracefully
            assert response.status_code in [200, 201, 422]


class TestItemsEndpointsDataIsolation:
    """Data isolation tests for items endpoints."""
    
    def test_user_data_isolation(
        self,
        client: TestClient,
        multiple_test_users: list[User],
        auth_headers: dict[str, str]
    ):
        """Test that users can only see their own items."""
        user1, user2 = multiple_test_users[0], multiple_test_users[1]
        
        # Create items for user1
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = user1.id
            
            item_data = {
                "name": "User1 Item",
                "price": "10.00"
            }
            response = client.post("/api/items/", json=item_data, headers=auth_headers)
            assert response.status_code == 201
            user1_item = response.json()
        
        # Create items for user2
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = user2.id
            
            item_data = {
                "name": "User2 Item",
                "price": "20.00"
            }
            response = client.post("/api/items/", json=item_data, headers=auth_headers)
            assert response.status_code == 201
            user2_item = response.json()
        
        # User1 should only see their own items
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = user1.id
            
            response = client.get("/api/items/", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            
            item_names = [item["name"] for item in data["items"]]
            assert "User1 Item" in item_names
            assert "User2 Item" not in item_names
        
        # User2 should only see their own items
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = user2.id
            
            response = client.get("/api/items/", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            
            item_names = [item["name"] for item in data["items"]]
            assert "User2 Item" in item_names
            assert "User1 Item" not in item_names
    
    def test_cross_user_access_prevention(
        self,
        client: TestClient,
        multiple_test_users: list[User],
        auth_headers: dict[str, str]
    ):
        """Test that users cannot access other users' items."""
        user1, user2 = multiple_test_users[0], multiple_test_users[1]
        
        # Create item for user1
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = user1.id
            
            item_data = {
                "name": "User1 Private Item",
                "price": "10.00"
            }
            response = client.post("/api/items/", json=item_data, headers=auth_headers)
            assert response.status_code == 201
            user1_item = response.json()
        
        # User2 should not be able to access user1's item
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = user2.id
            
            # Try to get user1's item
            response = client.get(f"/api/items/{user1_item['id']}", headers=auth_headers)
            assert response.status_code == 403
            
            # Try to update user1's item
            update_data = {"name": "Hacked Item"}
            response = client.put(
                f"/api/items/{user1_item['id']}",
                json=update_data,
                headers=auth_headers
            )
            assert response.status_code == 403
            
            # Try to delete user1's item
            response = client.delete(f"/api/items/{user1_item['id']}", headers=auth_headers)
            assert response.status_code == 403