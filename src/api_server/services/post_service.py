"""Post service for business logic operations.

This module provides business logic for post management operations,
including post CRUD operations, user authorization checks, validation,
proper error handling with comprehensive type hints, and operation logging.
"""

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from ..logging_config import get_logger, log_database_operation
from ..models.post import Post, PostCreate, PostUpdate
from ..repositories.post_repository import (
    PostAccessDeniedError,
    PostNotFoundError,
    PostRepository,
)
from ..repositories.user_repository import UserRepository
from ..schemas.post_schemas import (
    PostListRequest,
    PostListResponse,
    PostResponse,
    PostWithUser,
    UserSummary,
)

logger = get_logger("post_service")


class PostServiceError(Exception):
    """Base exception for post service errors."""

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


class PostNotFoundServiceError(PostServiceError):
    """Exception raised when post is not found."""

    def __init__(self, post_id: int) -> None:
        super().__init__(f"Post with id {post_id} not found", status_code=404)


class PostAccessDeniedServiceError(PostServiceError):
    """Exception raised when user doesn't have access to post."""

    def __init__(self, post_id: int, user_id: int) -> None:
        super().__init__(
            f"User {user_id} does not have access to post {post_id}", status_code=403
        )


class PostValidationError(PostServiceError):
    """Exception raised for post validation errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class PostService:
    """Service for post business logic operations.

    This service provides business logic for post management,
    including validation, authorization, transformation, and coordination with
    repositories.
    All operations are user-scoped - users can only access their own posts.
    """

    def __init__(self, session: Session) -> None:
        """Initialize post service with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session
        self.post_repository = PostRepository(session)
        self.user_repository = UserRepository(session)

    async def create_post(self, post_data: PostCreate, user_id: int) -> PostResponse:
        """Create a new post for the specified user.

        Args:
            post_data: Post creation data
            user_id: ID of the user who will own the post

        Returns:
            Created post response

        Raises:
            PostServiceError: If post creation fails
            PostValidationError: If validation fails
        """
        try:
            logger.info(
                f"Creating post for user {user_id}",
                extra={
                    "user_id": user_id,
                    "post_title": post_data.title,
                    "published": post_data.published,
                },
            )

            # Validate user exists
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                logger.warning(
                    f"Attempted to create post for non-existent user {user_id}",
                    extra={"user_id": user_id},
                )
                raise PostServiceError(
                    f"User with id {user_id} not found", status_code=404
                )

            # Validate post data
            self._validate_post_create_data(post_data)

            # Create post
            post = self.post_repository.create(post_data, user_id)

            log_database_operation(
                operation="INSERT",
                table="posts",
                success=True,
                user_id=user_id,
                post_id=post.id,
            )

            logger.info(
                f"Post created successfully for user {user_id}",
                extra={"user_id": user_id, "post_id": post.id, "post_title": post.title},
            )

            return self._convert_to_response(post)

        except PostValidationError as e:
            logger.warning(
                f"Post validation failed for user {user_id}: {e.message}",
                extra={"user_id": user_id, "validation_error": e.message},
            )
            raise
        except SQLAlchemyError as e:
            log_database_operation(
                operation="INSERT",
                table="posts",
                success=False,
                error=str(e),
                user_id=user_id,
            )

            if "user_id" in str(e) and "does not exist" in str(e):
                logger.error(
                    f"Foreign key constraint failed for user {user_id}",
                    extra={"user_id": user_id, "error": str(e)},
                )
                raise PostServiceError(
                    f"User with id {user_id} not found",
                    status_code=404,
                    original_error=e,
                ) from e

            logger.error(
                f"Database error creating post for user {user_id}: {str(e)}",
                exc_info=True,
                extra={"user_id": user_id},
            )
            raise PostServiceError(
                f"Failed to create post: {str(e)}", status_code=500, original_error=e
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error creating post for user {user_id}: {str(e)}",
                exc_info=True,
                extra={"user_id": user_id},
            )
            raise PostServiceError(
                f"Unexpected error creating post: {str(e)}",
                status_code=500,
                original_error=e,
            ) from e

    async def get_post_by_id(self, post_id: int, user_id: int) -> PostResponse | None:
        """Get post by ID for the specified user.

        Args:
            post_id: ID of the post to retrieve
            user_id: ID of the user who should own the post

        Returns:
            Post response if found and owned by user, None otherwise

        Raises:
            PostServiceError: If operation fails
        """
        try:
            post = self.post_repository.get_by_id(post_id, user_id)
            if not post:
                return None

            return self._convert_to_response(post)

        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to get post: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_post_by_id_or_raise(self, post_id: int, user_id: int) -> PostResponse:
        """Get post by ID for the specified user or raise an exception.

        Args:
            post_id: ID of the post to retrieve
            user_id: ID of the user who should own the post

        Returns:
            Post response if found and owned by user

        Raises:
            PostNotFoundServiceError: If post is not found
            PostAccessDeniedServiceError: If post exists but is owned by different user
            PostServiceError: If operation fails
        """
        try:
            post = self.post_repository.get_by_id_or_raise(post_id, user_id)
            return self._convert_to_response(post)

        except PostNotFoundError as e:
            raise PostNotFoundServiceError(post_id) from e
        except PostAccessDeniedError as e:
            raise PostAccessDeniedServiceError(post_id, user_id) from e
        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to get post: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_posts_for_user(
        self, user_id: int, request: PostListRequest
    ) -> PostListResponse:
        """Get posts for a specific user with filtering, sorting, and pagination.

        Args:
            user_id: ID of the user whose posts to retrieve
            request: Request parameters for filtering, sorting, and pagination

        Returns:
            Paginated list of posts with metadata

        Raises:
            PostServiceError: If operation fails
            PostValidationError: If request parameters are invalid
        """
        try:
            # Validate request parameters
            self._validate_list_request(request)

            # Calculate skip value from page and page_size
            skip = (request.page - 1) * request.page_size

            # Get posts based on filters
            if request.search:
                posts = self.post_repository.search_for_user(
                    user_id=user_id,
                    query=request.search,
                    skip=skip,
                    limit=request.page_size,
                    published_only=request.published_only,
                )
            else:
                posts = self.post_repository.get_all_for_user(
                    user_id=user_id,
                    skip=skip,
                    limit=request.page_size,
                    sort_by=request.sort_by.value,
                    sort_order=request.sort_order.value,
                    published_only=request.published_only,
                )

            # Get total count for pagination
            total_count = self.post_repository.count_for_user(
                user_id, published_only=request.published_only
            )

            # Calculate total pages
            total_pages = (total_count + request.page_size - 1) // request.page_size

            # Convert posts to responses
            post_responses = [self._convert_to_response(post) for post in posts]

            return PostListResponse(
                posts=post_responses,
                total=total_count,
                page=request.page,
                page_size=request.page_size,
                total_pages=total_pages,
            )

        except PostValidationError:
            raise
        except ValueError as e:
            raise PostValidationError(str(e)) from e
        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to get posts: {str(e)}", status_code=500, original_error=e
            ) from e

    async def update_post(
        self, post_id: int, user_id: int, post_data: PostUpdate
    ) -> PostResponse:
        """Update a post for the specified user.

        Args:
            post_id: ID of the post to update
            user_id: ID of the user who should own the post
            post_data: Updated post data

        Returns:
            Updated post response

        Raises:
            PostNotFoundServiceError: If post is not found
            PostAccessDeniedServiceError: If post exists but is owned by different user
            PostValidationError: If validation fails
            PostServiceError: If operation fails
        """
        try:
            # Validate update data
            self._validate_post_update_data(post_data)

            # Update post (this will handle authorization checks)
            post = self.post_repository.update(post_id, user_id, post_data)

            return self._convert_to_response(post)

        except PostNotFoundError as e:
            raise PostNotFoundServiceError(post_id) from e
        except PostAccessDeniedError as e:
            raise PostAccessDeniedServiceError(post_id, user_id) from e
        except PostValidationError:
            raise
        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to update post: {str(e)}", status_code=500, original_error=e
            ) from e

    async def delete_post(self, post_id: int, user_id: int) -> bool:
        """Delete a post for the specified user.

        Args:
            post_id: ID of the post to delete
            user_id: ID of the user who should own the post

        Returns:
            True if post was deleted, False if not found

        Raises:
            PostAccessDeniedServiceError: If post exists but is owned by different user
            PostServiceError: If operation fails
        """
        try:
            return self.post_repository.delete(post_id, user_id)

        except PostAccessDeniedError as e:
            raise PostAccessDeniedServiceError(post_id, user_id) from e
        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to delete post: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_post_with_user(
        self, post_id: int, user_id: int
    ) -> PostWithUser | None:
        """Get post with user information for the specified user.

        Args:
            post_id: ID of the post to retrieve
            user_id: ID of the user who should own the post

        Returns:
            Post with user information if found and owned by user, None otherwise

        Raises:
            PostServiceError: If operation fails
        """
        try:
            post = self.post_repository.get_by_id(post_id, user_id)
            if not post:
                return None

            # Get user information
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise PostServiceError(
                    f"User with id {user_id} not found", status_code=404
                )

            # Convert to response with user information
            post_response = self._convert_to_response(post)
            user_summary = UserSummary(
                id=user.id if user.id is not None else 0,
                display_name=user.display_name,
                picture_url=user.picture_url,
            )

            return PostWithUser(**post_response.dict(), user=user_summary)

        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to get post with user: {str(e)}",
                status_code=500,
                original_error=e,
            ) from e

    async def search_posts(
        self, user_id: int, query: str, page: int = 1, page_size: int = 20, published_only: bool = False
    ) -> PostListResponse:
        """Search posts by title or content for a specific user.

        Args:
            user_id: ID of the user whose posts to search
            query: Search query string
            page: Page number (starts from 1)
            page_size: Number of posts per page
            published_only: If True, only search published posts

        Returns:
            Paginated search results

        Raises:
            PostValidationError: If search parameters are invalid
            PostServiceError: If operation fails
        """
        try:
            # Validate search parameters
            if not query or not query.strip():
                raise PostValidationError("Search query cannot be empty")

            if page < 1:
                raise PostValidationError("Page number must be at least 1")

            if page_size < 1 or page_size > 100:
                raise PostValidationError("Page size must be between 1 and 100")

            # Calculate skip value
            skip = (page - 1) * page_size

            # Search posts
            posts = self.post_repository.search_for_user(
                user_id=user_id, 
                query=query.strip(), 
                skip=skip, 
                limit=page_size,
                published_only=published_only
            )

            # For search, we don't have an efficient way to get total count
            # So we'll estimate based on returned results
            total_count = len(posts)
            if len(posts) == page_size:
                # There might be more results, but we can't know for sure
                total_count = page * page_size
            else:
                # This is the last page
                total_count = (page - 1) * page_size + len(posts)

            total_pages = (total_count + page_size - 1) // page_size

            # Convert posts to responses
            post_responses = [self._convert_to_response(post) for post in posts]

            return PostListResponse(
                posts=post_responses,
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        except PostValidationError:
            raise
        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to search posts: {str(e)}", status_code=500, original_error=e
            ) from e

    async def get_user_post_count(self, user_id: int, published_only: bool = False) -> int:
        """Get total count of posts for a specific user.

        Args:
            user_id: ID of the user whose posts to count
            published_only: If True, only count published posts

        Returns:
            Total number of posts owned by the user

        Raises:
            PostServiceError: If operation fails
        """
        try:
            return self.post_repository.count_for_user(user_id, published_only=published_only)
        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to count posts: {str(e)}", status_code=500, original_error=e
            ) from e

    def _convert_to_response(self, post: Post) -> PostResponse:
        """Convert Post model to PostResponse schema.

        Args:
            post: Post model instance

        Returns:
            PostResponse schema instance
        """
        return PostResponse(
            id=post.id if post.id is not None else 0,
            title=post.title,
            content=post.content,
            published=post.published,
            location=post.location,
            user_id=post.user_id,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )

    def _validate_post_create_data(self, post_data: PostCreate) -> None:
        """Validate post creation data.

        Args:
            post_data: Post creation data to validate

        Raises:
            PostValidationError: If validation fails
        """
        # Basic validation (Pydantic handles most of this)
        if not post_data.title or not post_data.title.strip():
            raise PostValidationError("Post title cannot be empty")

        # Validate content length if provided
        if post_data.content and len(post_data.content) > 5000:
            raise PostValidationError("Post content cannot exceed 5000 characters")

        # Validate location if provided
        if post_data.location:
            self._validate_geohash(post_data.location)

    def _validate_post_update_data(self, post_data: PostUpdate) -> None:
        """Validate post update data.

        Args:
            post_data: Post update data to validate

        Raises:
            PostValidationError: If validation fails
        """
        # Check if at least one field is provided for update
        update_fields = post_data.dict(exclude_unset=True)
        if not update_fields:
            raise PostValidationError("At least one field must be provided for update")

        # Validate individual fields if provided
        if post_data.title is not None:
            if not post_data.title or not post_data.title.strip():
                raise PostValidationError("Post title cannot be empty")

        if post_data.content is not None and len(post_data.content) > 5000:
            raise PostValidationError("Post content cannot exceed 5000 characters")

        # Validate location if provided
        if post_data.location is not None:
            self._validate_geohash(post_data.location)

    def _validate_list_request(self, request: PostListRequest) -> None:
        """Validate post list request parameters.

        Args:
            request: Post list request to validate

        Raises:
            PostValidationError: If validation fails
        """
        if request.page < 1:
            raise PostValidationError("Page number must be at least 1")

        if request.page_size < 1 or request.page_size > 100:
            raise PostValidationError("Page size must be between 1 and 100")

        if request.search is not None and len(request.search.strip()) == 0:
            raise PostValidationError("Search query cannot be empty")

    def _validate_geohash(self, geohash: str) -> None:
        """Validate GEOHASH format.

        Args:
            geohash: GEOHASH string to validate

        Raises:
            PostValidationError: If GEOHASH format is invalid
        """
        import re
        
        if not geohash or not geohash.strip():
            raise PostValidationError("GEOHASH cannot be empty")
        
        geohash = geohash.strip()
        
        # Basic GEOHASH validation (alphanumeric characters only)
        if not re.match(r'^[0-9a-z]+$', geohash.lower()):
            raise PostValidationError("GEOHASH must contain only alphanumeric characters")
        
        # GEOHASH length validation (typically 1-12 characters)
        if len(geohash) < 1 or len(geohash) > 12:
            raise PostValidationError("GEOHASH must be between 1 and 12 characters")

    async def get_posts_by_location(
        self, 
        user_id: int, 
        location_prefix: str, 
        page: int = 1, 
        page_size: int = 20, 
        published_only: bool = False
    ) -> PostListResponse:
        """Get posts by location prefix for a specific user.

        Args:
            user_id: ID of the user whose posts to retrieve
            location_prefix: GEOHASH prefix to search for
            page: Page number (starts from 1)
            page_size: Number of posts per page
            published_only: If True, only return published posts

        Returns:
            Paginated list of posts with matching location prefix

        Raises:
            PostValidationError: If location prefix is invalid
            PostServiceError: If operation fails
        """
        try:
            # Validate location prefix
            if not location_prefix or not location_prefix.strip():
                raise PostValidationError("Location prefix cannot be empty")
            
            location_prefix = location_prefix.strip()
            self._validate_geohash(location_prefix)

            if page < 1:
                raise PostValidationError("Page number must be at least 1")

            if page_size < 1 or page_size > 100:
                raise PostValidationError("Page size must be between 1 and 100")

            # Calculate skip value
            skip = (page - 1) * page_size

            # Get posts by location prefix
            posts = self.post_repository.get_posts_by_location_prefix(
                user_id=user_id,
                location_prefix=location_prefix,
                skip=skip,
                limit=page_size,
                published_only=published_only,
            )

            # For location search, we estimate total count based on returned results
            total_count = len(posts)
            if len(posts) == page_size:
                total_count = page * page_size
            else:
                total_count = (page - 1) * page_size + len(posts)

            total_pages = (total_count + page_size - 1) // page_size

            # Convert posts to responses
            post_responses = [self._convert_to_response(post) for post in posts]

            return PostListResponse(
                posts=post_responses,
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        except PostValidationError:
            raise
        except SQLAlchemyError as e:
            raise PostServiceError(
                f"Failed to get posts by location: {str(e)}", 
                status_code=500, 
                original_error=e
            ) from e