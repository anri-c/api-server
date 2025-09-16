"""Items router for CRUD operations on items.

This module provides item management endpoints with full CRUD operations,
authentication requirements, user-scoped operations, proper request/response
schemas, error handling, and comprehensive type hints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse

from ..schemas.item_schemas import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemWithUser,
    ItemListResponse,
    ItemListRequest,
    ItemOperationResponse,
    ItemError,
    ItemSortField,
    SortOrder
)
from ..services.item_service import (
    ItemService,
    ItemServiceError,
    ItemNotFoundServiceError,
    ItemAccessDeniedServiceError,
    ItemValidationError
)
from ..dependencies import get_current_user, get_current_user_id, get_session
from ..models.user import UserResponse
from sqlmodel import Session

router = APIRouter(
    prefix="/api/items",
    tags=["items"],
    dependencies=[Depends(get_current_user_id)],  # All endpoints require authentication
    responses={
        400: {"description": "Bad request", "model": ItemError},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden", "model": ItemError},
        404: {"description": "Not found", "model": ItemError},
        500: {"description": "Internal server error", "model": ItemError}
    }
)


def get_item_service(session: Session = Depends(get_session)) -> ItemService:
    """Get item service instance.
    
    Args:
        session: Database session
        
    Returns:
        ItemService: Item service instance
    """
    return ItemService(session)


@router.get(
    "/",
    response_model=ItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's items",
    description="Get paginated list of items owned by the authenticated user with filtering and sorting options"
)
async def get_items(
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page (max 100)"),
    sort_by: ItemSortField = Query(default=ItemSortField.CREATED_AT, description="Field to sort by"),
    sort_order: SortOrder = Query(default=SortOrder.DESC, description="Sort order"),
    search: Optional[str] = Query(default=None, max_length=100, description="Search term for item name or description"),
    min_price: Optional[float] = Query(default=None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(default=None, gt=0, description="Maximum price filter"),
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> ItemListResponse:
    """Get paginated list of items for the authenticated user.
    
    This endpoint returns a paginated list of items owned by the authenticated user
    with support for filtering by price range and search terms, plus sorting options.
    
    Args:
        page: Page number (starts from 1)
        page_size: Number of items per page (max 100)
        sort_by: Field to sort by (name, price, created_at, updated_at)
        sort_order: Sort order (asc or desc)
        search: Search term for item name or description
        min_price: Minimum price filter
        max_price: Maximum price filter
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        ItemListResponse: Paginated list of items with metadata
        
    Raises:
        HTTPException: If validation fails or service error occurs
        
    Example:
        GET /api/items/?page=1&page_size=10&sort_by=price&sort_order=asc&search=coffee
        
        Response:
        {
            "items": [...],
            "total": 25,
            "page": 1,
            "page_size": 10,
            "total_pages": 3
        }
    """
    try:
        # Create request object from query parameters
        request = ItemListRequest(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            min_price=min_price,
            max_price=max_price
        )
        
        # Get items for user
        return await item_service.get_items_for_user(current_user_id, request)
        
    except ItemValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        ) from e
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.post(
    "/",
    response_model=ItemOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new item",
    description="Create a new item for the authenticated user"
)
async def create_item(
    item_data: ItemCreate,
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> ItemOperationResponse:
    """Create a new item for the authenticated user.
    
    This endpoint creates a new item owned by the authenticated user
    with the provided item data.
    
    Args:
        item_data: Item creation data
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        ItemOperationResponse: Creation result with item data
        
    Raises:
        HTTPException: If validation fails or service error occurs
        
    Example:
        POST /api/items/
        {
            "name": "Premium Coffee Beans",
            "description": "High-quality arabica coffee beans",
            "price": 29.99
        }
        
        Response:
        {
            "success": true,
            "message": "Item created successfully",
            "item": {
                "id": 123,
                "name": "Premium Coffee Beans",
                "description": "High-quality arabica coffee beans",
                "price": 29.99,
                "user_id": 456,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": null
            }
        }
    """
    try:
        # Create item
        item = await item_service.create_item(item_data, current_user_id)
        
        return ItemOperationResponse(
            success=True,
            message="Item created successfully",
            item=item
        )
        
    except ItemValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        ) from e
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get item by ID",
    description="Get a specific item by ID (user can only access their own items)"
)
async def get_item(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> ItemResponse:
    """Get a specific item by ID for the authenticated user.
    
    This endpoint returns a specific item owned by the authenticated user.
    Users can only access their own items.
    
    Args:
        item_id: ID of the item to retrieve
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        ItemResponse: Item data
        
    Raises:
        HTTPException: If item not found, access denied, or service error occurs
        
    Example:
        GET /api/items/123
        
        Response:
        {
            "id": 123,
            "name": "Premium Coffee Beans",
            "description": "High-quality arabica coffee beans",
            "price": 29.99,
            "user_id": 456,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": null
        }
    """
    try:
        # Get item by ID (will raise exception if not found or access denied)
        return await item_service.get_item_by_id_or_raise(item_id, current_user_id)
        
    except ItemNotFoundServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        ) from e
    except ItemAccessDeniedServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        ) from e
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.put(
    "/{item_id}",
    response_model=ItemOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update item",
    description="Update a specific item by ID (user can only update their own items)"
)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> ItemOperationResponse:
    """Update a specific item by ID for the authenticated user.
    
    This endpoint updates a specific item owned by the authenticated user.
    Users can only update their own items. Supports partial updates.
    
    Args:
        item_id: ID of the item to update
        item_data: Item update data (partial updates supported)
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        ItemOperationResponse: Update result with updated item data
        
    Raises:
        HTTPException: If item not found, access denied, validation fails, or service error occurs
        
    Example:
        PUT /api/items/123
        {
            "name": "Premium Coffee Beans - Updated",
            "price": 34.99
        }
        
        Response:
        {
            "success": true,
            "message": "Item updated successfully",
            "item": {
                "id": 123,
                "name": "Premium Coffee Beans - Updated",
                "description": "High-quality arabica coffee beans",
                "price": 34.99,
                "user_id": 456,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z"
            }
        }
    """
    try:
        # Update item
        item = await item_service.update_item(item_id, current_user_id, item_data)
        
        return ItemOperationResponse(
            success=True,
            message="Item updated successfully",
            item=item
        )
        
    except ItemNotFoundServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        ) from e
    except ItemAccessDeniedServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        ) from e
    except ItemValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        ) from e
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Delete a specific item by ID (user can only delete their own items)"
)
async def delete_item(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> None:
    """Delete a specific item by ID for the authenticated user.
    
    This endpoint deletes a specific item owned by the authenticated user.
    Users can only delete their own items.
    
    Args:
        item_id: ID of the item to delete
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        None: No content (204 status)
        
    Raises:
        HTTPException: If item not found, access denied, or service error occurs
        
    Example:
        DELETE /api/items/123
        
        Response: 204 No Content (no body)
    """
    try:
        # Delete item
        deleted = await item_service.delete_item(item_id, current_user_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        # Return nothing for 204 No Content
        return
        
    except ItemAccessDeniedServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        ) from e
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.get(
    "/{item_id}/with-user",
    response_model=ItemWithUser,
    status_code=status.HTTP_200_OK,
    summary="Get item with user information",
    description="Get a specific item by ID with user information (user can only access their own items)"
)
async def get_item_with_user(
    item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> ItemWithUser:
    """Get a specific item by ID with user information for the authenticated user.
    
    This endpoint returns a specific item owned by the authenticated user
    along with user information. Users can only access their own items.
    
    Args:
        item_id: ID of the item to retrieve
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        ItemWithUser: Item data with user information
        
    Raises:
        HTTPException: If item not found, access denied, or service error occurs
        
    Example:
        GET /api/items/123/with-user
        
        Response:
        {
            "id": 123,
            "name": "Premium Coffee Beans",
            "description": "High-quality arabica coffee beans",
            "price": 29.99,
            "user_id": 456,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": null,
            "user": {
                "id": 456,
                "display_name": "John Doe",
                "picture_url": "https://profile.line-scdn.net/..."
            }
        }
    """
    try:
        # Get item with user information
        item_with_user = await item_service.get_item_with_user(item_id, current_user_id)
        
        if not item_with_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        return item_with_user
        
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.get(
    "/search/{query}",
    response_model=ItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search items",
    description="Search items by name or description for the authenticated user"
)
async def search_items(
    query: str,
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page (max 100)"),
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> ItemListResponse:
    """Search items by name or description for the authenticated user.
    
    This endpoint searches through items owned by the authenticated user
    based on the provided query string, matching against item names and descriptions.
    
    Args:
        query: Search query string
        page: Page number (starts from 1)
        page_size: Number of items per page (max 100)
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        ItemListResponse: Paginated search results
        
    Raises:
        HTTPException: If validation fails or service error occurs
        
    Example:
        GET /api/items/search/coffee?page=1&page_size=10
        
        Response:
        {
            "items": [...],
            "total": 5,
            "page": 1,
            "page_size": 10,
            "total_pages": 1
        }
    """
    try:
        # Search items
        return await item_service.search_items(current_user_id, query, page, page_size)
        
    except ItemValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        ) from e
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@router.get(
    "/stats/count",
    response_model=Dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Get item count",
    description="Get total count of items owned by the authenticated user"
)
async def get_item_count(
    current_user_id: int = Depends(get_current_user_id),
    item_service: ItemService = Depends(get_item_service)
) -> Dict[str, int]:
    """Get total count of items owned by the authenticated user.
    
    This endpoint returns the total number of items owned by the authenticated user.
    
    Args:
        current_user_id: ID of the authenticated user
        item_service: Item service instance
        
    Returns:
        Dict[str, int]: Total item count
        
    Raises:
        HTTPException: If service error occurs
        
    Example:
        GET /api/items/stats/count
        
        Response:
        {
            "count": 25
        }
    """
    try:
        # Get item count
        count = await item_service.get_user_item_count(current_user_id)
        
        return {"count": count}
        
    except ItemServiceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


# Note: Exception handlers are registered globally in main.py
# Router-level exception handlers are not supported in FastAPI
