"""Posts router for CRUD operations on posts.

This module provides post management endpoints with full CRUD operations,
authentication requirements, user-scoped operations, proper request/response
schemas, error handling, and comprehensive type hints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from ..dependencies import get_current_user_id, get_session
from ..schemas.post_schemas import (
    PostCreate,
    PostError,
    PostListRequest,
    PostListResponse,
    PostOperationResponse,
    PostResponse,
    PostSortField,
    PostUpdate,
    PostWithUser,
    SortOrder,
)
from ..services.post_service import (
    PostAccessDeniedServiceError,
    PostNotFoundServiceError,
    PostService,
    PostServiceError,
    PostValidationError,
)

router = APIRouter(
    prefix="/api/posts",
    tags=["posts"],
    dependencies=[Depends(get_current_user_id)],  # All endpoints require authentication
    responses={
        400: {"description": "Bad request", "model": PostError},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden", "model": PostError},
        404: {"description": "Not found", "model": PostError},
        500: {"description": "Internal server error", "model": PostError},
    },
)


def get_post_service(session: Session = Depends(get_session)) -> PostService:
    """Get post service instance.

    Args:
        session: Database session

    Returns:
        PostService: Post service instance
    """
    return PostService(session)


@router.get(
    "/",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's posts",
    description="Get paginated list of posts owned by the authenticated user with filtering and sorting options",
)
async def get_posts(
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Number of posts per page (max 100)"
    ),
    sort_by: PostSortField = Query(
        default=PostSortField.CREATED_AT, description="Field to sort by"
    ),
    sort_order: SortOrder = Query(default=SortOrder.DESC, description="Sort order"),
    search: str | None = Query(
        default=None,
        max_length=100,
        description="Search term for post title or content",
    ),
    published_only: bool = Query(
        default=False, description="Filter to show only published posts"
    ),
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> PostListResponse:
    """Get paginated list of posts for the authenticated user.

    This endpoint returns a paginated list of posts owned by the authenticated user
    with support for filtering by publication status and search terms, plus sorting options.

    Args:
        page: Page number (starts from 1)
        page_size: Number of posts per page (max 100)
        sort_by: Field to sort by (title, published, created_at, updated_at)
        sort_order: Sort order (asc or desc)
        search: Search term for post title or content
        published_only: Filter to show only published posts
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        PostListResponse: Paginated list of posts with metadata

    Raises:
        HTTPException: If validation fails or service error occurs

    Example:
        GET /api/posts/?page=1&page_size=10&sort_by=title&sort_order=asc&search=python

        Response:
        {
            "posts": [...],
            "total": 25,
            "page": 1,
            "page_size": 10,
            "total_pages": 3
        }
    """
    try:
        # Create request object from query parameters
        request = PostListRequest(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            published_only=published_only,
        )

        # Get posts for user
        return await post_service.get_posts_for_user(current_user_id, request)

    except PostValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.post(
    "/",
    response_model=PostOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new post",
    description="Create a new post for the authenticated user",
)
async def create_post(
    post_data: PostCreate,
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> PostOperationResponse:
    """Create a new post for the authenticated user.

    This endpoint creates a new post owned by the authenticated user
    with the provided post data.

    Args:
        post_data: Post creation data
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        PostOperationResponse: Creation result with post data

    Raises:
        HTTPException: If validation fails or service error occurs

    Example:
        POST /api/posts/
        {
            "title": "My First Blog Post",
            "content": "This is the content of my first blog post...",
            "published": false
        }

        Response:
        {
            "success": true,
            "message": "Post created successfully",
            "post": {
                "id": 123,
                "title": "My First Blog Post",
                "content": "This is the content of my first blog post...",
                "published": false,
                "user_id": 456,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": null
            }
        }
    """
    try:
        # Create post
        post = await post_service.create_post(post_data, current_user_id)

        return PostOperationResponse(
            success=True, message="Post created successfully", post=post
        )

    except PostValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
    summary="Get post by ID",
    description="Get a specific post by ID (user can only access their own posts)",
)
async def get_post(
    post_id: int,
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> PostResponse:
    """Get a specific post by ID for the authenticated user.

    This endpoint returns a specific post owned by the authenticated user.
    Users can only access their own posts.

    Args:
        post_id: ID of the post to retrieve
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        PostResponse: Post data

    Raises:
        HTTPException: If post not found, access denied, or service error occurs

    Example:
        GET /api/posts/123

        Response:
        {
            "id": 123,
            "title": "My First Blog Post",
            "content": "This is the content of my first blog post...",
            "published": false,
            "user_id": 456,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": null
        }
    """
    try:
        # Get post by ID (will raise exception if not found or access denied)
        return await post_service.get_post_by_id_or_raise(post_id, current_user_id)

    except PostNotFoundServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except PostAccessDeniedServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=e.message
        ) from e
    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.put(
    "/{post_id}",
    response_model=PostOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update post",
    description="Update a specific post by ID (user can only update their own posts)",
)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> PostOperationResponse:
    """Update a specific post by ID for the authenticated user.

    This endpoint updates a specific post owned by the authenticated user.
    Users can only update their own posts. Supports partial updates.

    Args:
        post_id: ID of the post to update
        post_data: Post update data (partial updates supported)
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        PostOperationResponse: Update result with updated post data

    Raises:
        HTTPException: If post not found, access denied, validation fails, or service error occurs

    Example:
        PUT /api/posts/123
        {
            "title": "My Updated Blog Post",
            "published": true
        }

        Response:
        {
            "success": true,
            "message": "Post updated successfully",
            "post": {
                "id": 123,
                "title": "My Updated Blog Post",
                "content": "This is the content of my first blog post...",
                "published": true,
                "user_id": 456,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z"
            }
        }
    """
    try:
        # Update post
        post = await post_service.update_post(post_id, current_user_id, post_data)

        return PostOperationResponse(
            success=True, message="Post updated successfully", post=post
        )

    except PostNotFoundServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except PostAccessDeniedServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=e.message
        ) from e
    except PostValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete post",
    description="Delete a specific post by ID (user can only delete their own posts)",
)
async def delete_post(
    post_id: int,
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> None:
    """Delete a specific post by ID for the authenticated user.

    This endpoint deletes a specific post owned by the authenticated user.
    Users can only delete their own posts.

    Args:
        post_id: ID of the post to delete
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        None: No content (204 status)

    Raises:
        HTTPException: If post not found, access denied, or service error occurs

    Example:
        DELETE /api/posts/123

        Response: 204 No Content (no body)
    """
    try:
        # Delete post
        deleted = await post_service.delete_post(post_id, current_user_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found",
            )

        # Return nothing for 204 No Content
        return

    except PostAccessDeniedServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=e.message
        ) from e
    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.get(
    "/{post_id}/with-user",
    response_model=PostWithUser,
    status_code=status.HTTP_200_OK,
    summary="Get post with user information",
    description="Get a specific post by ID with user information (user can only access their own posts)",
)
async def get_post_with_user(
    post_id: int,
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> PostWithUser:
    """Get a specific post by ID with user information for the authenticated user.

    This endpoint returns a specific post owned by the authenticated user
    along with user information. Users can only access their own posts.

    Args:
        post_id: ID of the post to retrieve
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        PostWithUser: Post data with user information

    Raises:
        HTTPException: If post not found, access denied, or service error occurs

    Example:
        GET /api/posts/123/with-user

        Response:
        {
            "id": 123,
            "title": "My First Blog Post",
            "content": "This is the content of my first blog post...",
            "published": false,
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
        # Get post with user information
        post_with_user = await post_service.get_post_with_user(post_id, current_user_id)

        if not post_with_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found",
            )

        return post_with_user

    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.get(
    "/search/{query}",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search posts",
    description="Search posts by title or content for the authenticated user",
)
async def search_posts(
    query: str,
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Number of posts per page (max 100)"
    ),
    published_only: bool = Query(
        default=False, description="Filter to show only published posts"
    ),
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> PostListResponse:
    """Search posts by title or content for the authenticated user.

    This endpoint searches through posts owned by the authenticated user
    based on the provided query string, matching against post titles and content.

    Args:
        query: Search query string
        page: Page number (starts from 1)
        page_size: Number of posts per page (max 100)
        published_only: Filter to show only published posts
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        PostListResponse: Paginated search results

    Raises:
        HTTPException: If validation fails or service error occurs

    Example:
        GET /api/posts/search/python?page=1&page_size=10&published_only=true

        Response:
        {
            "posts": [...],
            "total": 5,
            "page": 1,
            "page_size": 10,
            "total_pages": 1
        }
    """
    try:
        # Search posts
        return await post_service.search_posts(current_user_id, query, page, page_size, published_only)

    except PostValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.get(
    "/stats/count",
    response_model=dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Get post count",
    description="Get total count of posts owned by the authenticated user",
)
async def get_post_count(
    published_only: bool = Query(
        default=False, description="Count only published posts"
    ),
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> dict[str, int]:
    """Get total count of posts owned by the authenticated user.

    This endpoint returns the total number of posts owned by the authenticated user.

    Args:
        published_only: Count only published posts
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        Dict[str, int]: Total post count

    Raises:
        HTTPException: If service error occurs

    Example:
        GET /api/posts/stats/count?published_only=true

        Response:
        {
            "count": 15
        }
    """
    try:
        # Get post count
        count = await post_service.get_user_post_count(current_user_id, published_only=published_only)

        return {"count": count}

    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.get(
    "/location/{location_prefix}",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get posts by location",
    description="Get posts by GEOHASH location prefix for the authenticated user",
)
async def get_posts_by_location(
    location_prefix: str,
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Number of posts per page (max 100)"
    ),
    published_only: bool = Query(
        default=False, description="Filter to show only published posts"
    ),
    current_user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
) -> PostListResponse:
    """Get posts by GEOHASH location prefix for the authenticated user.

    This endpoint searches through posts owned by the authenticated user
    based on the provided GEOHASH location prefix, matching posts within
    the specified geographic area.

    Args:
        location_prefix: GEOHASH prefix to search for (e.g., "u4pr" for Tokyo area)
        page: Page number (starts from 1)
        page_size: Number of posts per page (max 100)
        published_only: Filter to show only published posts
        current_user_id: ID of the authenticated user
        post_service: Post service instance

    Returns:
        PostListResponse: Paginated location-based search results

    Raises:
        HTTPException: If validation fails or service error occurs

    Example:
        GET /api/posts/location/u4pr?page=1&page_size=10&published_only=true

        Response:
        {
            "posts": [...],
            "total": 8,
            "page": 1,
            "page_size": 10,
            "total_pages": 1
        }
    """
    try:
        # Get posts by location
        return await post_service.get_posts_by_location(
            current_user_id, location_prefix, page, page_size, published_only
        )

    except PostValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except PostServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


# Note: Exception handlers are registered globally in main.py
# Router-level exception handlers are not supported in FastAPI