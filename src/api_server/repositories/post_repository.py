"""Post repository for database operations.

This module provides the PostRepository class that handles all database operations
for posts, including CRUD operations, user-scoped queries, and transaction management.
"""

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, and_, asc, desc, select

from ..models.post import Post, PostCreate, PostUpdate


class PostNotFoundError(Exception):
    """Raised when a post is not found."""

    def __init__(self, post_id: int) -> None:
        self.post_id = post_id
        super().__init__(f"Post with id {post_id} not found")


class PostAccessDeniedError(Exception):
    """Raised when user tries to access post they don't own."""

    def __init__(self, post_id: int, user_id: int) -> None:
        self.post_id = post_id
        self.user_id = user_id
        super().__init__(f"User {user_id} does not have access to post {post_id}")


class PostRepository:
    """Repository for post database operations.

    This repository provides methods for creating, reading, updating, and deleting
    posts with proper user scoping and transaction management.

    All operations are scoped to the user - users can only access their own posts.
    """

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLModel database session
        """
        self.session = session

    def create(self, post_data: PostCreate, user_id: int) -> Post:
        """Create a new post for the specified user.

        Args:
            post_data: Post creation data
            user_id: ID of the user who owns the post

        Returns:
            Post: The created post

        Raises:
            SQLAlchemyError: If database operation fails
            IntegrityError: If user_id doesn't exist

        Example:
            post_data = PostCreate(title="My First Post", content="Hello world!")
            post = repository.create(post_data, user_id=1)
        """
        try:
            # Create post with user_id
            db_post = Post(
                title=post_data.title,
                content=post_data.content,
                published=post_data.published,
                location=post_data.location,
                user_id=user_id,
            )

            self.session.add(db_post)
            self.session.commit()
            self.session.refresh(db_post)

            return db_post

        except IntegrityError as e:
            self.session.rollback()
            raise IntegrityError(
                f"Failed to create post: user_id {user_id} does not exist",
                params=None,
                orig=e.orig if e.orig is not None else e,
            ) from e
        except SQLAlchemyError as e:
            self.session.rollback()
            raise SQLAlchemyError(
                f"Database error while creating post: {str(e)}"
            ) from e

    def get_by_id(self, post_id: int, user_id: int) -> Post | None:
        """Get a post by ID for the specified user.

        Args:
            post_id: ID of the post to retrieve
            user_id: ID of the user who should own the post

        Returns:
            Post: The post if found and owned by user, None otherwise

        Example:
            post = repository.get_by_id(post_id=1, user_id=1)
            if post:
                print(f"Found post: {post.title}")
        """
        try:
            statement = select(Post).where(
                and_(Post.id == post_id, Post.user_id == user_id)
            )

            result = self.session.exec(statement)
            return result.first()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while retrieving post {post_id}: {str(e)}"
            ) from e

    def get_by_id_or_raise(self, post_id: int, user_id: int) -> Post:
        """Get a post by ID for the specified user or raise an exception.

        Args:
            post_id: ID of the post to retrieve
            user_id: ID of the user who should own the post

        Returns:
            Post: The post if found and owned by user

        Raises:
            PostNotFoundError: If post is not found
            PostAccessDeniedError: If post exists but is owned by different user

        Example:
            try:
                post = repository.get_by_id_or_raise(post_id=1, user_id=1)
                print(f"Found post: {post.title}")
            except PostNotFoundError:
                print("Post not found")
        """
        try:
            # First check if post exists at all
            post_exists_statement = select(Post).where(Post.id == post_id)
            existing_post = self.session.exec(post_exists_statement).first()

            if not existing_post:
                raise PostNotFoundError(post_id)

            # Check if user owns the post
            if existing_post.user_id != user_id:
                raise PostAccessDeniedError(post_id, user_id)

            # Load with user relationship
            statement = select(Post).where(
                and_(Post.id == post_id, Post.user_id == user_id)
            )

            result = self.session.exec(statement)
            post = result.first()

            if not post:
                raise PostNotFoundError(post_id)

            return post

        except (PostNotFoundError, PostAccessDeniedError):
            raise
        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while retrieving post {post_id}: {str(e)}"
            ) from e

    def get_all_for_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        published_only: bool = False,
    ) -> list[Post]:
        """Get all posts for a specific user with pagination and sorting.

        Args:
            user_id: ID of the user whose posts to retrieve
            skip: Number of posts to skip (for pagination)
            limit: Maximum number of posts to return
            sort_by: Field to sort by (created_at, title, published, updated_at)
            sort_order: Sort order (asc or desc)
            published_only: If True, only return published posts

        Returns:
            List[Post]: List of posts owned by the user

        Raises:
            ValueError: If sort_by or sort_order is invalid
            SQLAlchemyError: If database operation fails

        Example:
            posts = repository.get_all_for_user(
                user_id=1, skip=0, limit=10, sort_by="title", sort_order="asc"
            )
        """
        try:
            # Validate sort parameters
            valid_sort_fields = {"created_at", "title", "published", "updated_at"}
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

            # Build query conditions
            conditions = [Post.user_id == user_id]
            if published_only:
                conditions.append(Post.published == True)

            statement = select(Post).where(and_(*conditions))

            # Add sorting
            sort_column = getattr(Post, sort_by)
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
                f"Database error while retrieving posts for user {user_id}: {str(e)}"
            ) from e

    def count_for_user(self, user_id: int, published_only: bool = False) -> int:
        """Count total number of posts for a specific user.

        Args:
            user_id: ID of the user whose posts to count
            published_only: If True, only count published posts

        Returns:
            int: Total number of posts owned by the user

        Raises:
            SQLAlchemyError: If database operation fails

        Example:
            total_posts = repository.count_for_user(user_id=1)
            print(f"User has {total_posts} posts")
        """
        try:
            conditions = [Post.user_id == user_id]
            if published_only:
                conditions.append(Post.published == True)

            statement = select(Post).where(and_(*conditions))
            result = self.session.exec(statement)
            return len(list(result.all()))

        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while counting posts for user {user_id}: {str(e)}"
            ) from e

    def update(self, post_id: int, user_id: int, post_data: PostUpdate) -> Post:
        """Update a post for the specified user.

        Args:
            post_id: ID of the post to update
            user_id: ID of the user who should own the post
            post_data: Updated post data

        Returns:
            Post: The updated post

        Raises:
            PostNotFoundError: If post is not found
            PostAccessDeniedError: If post exists but is owned by different user
            SQLAlchemyError: If database operation fails

        Example:
            update_data = PostUpdate(title="Updated Post", published=True)
            post = repository.update(post_id=1, user_id=1, post_data=update_data)
        """
        try:
            # Get the post (this will raise appropriate exceptions if not found)
            db_post = self.get_by_id_or_raise(post_id, user_id)

            # Update only provided fields
            update_data = post_data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                setattr(db_post, field, value)

            self.session.add(db_post)
            self.session.commit()
            self.session.refresh(db_post)

            return db_post

        except (PostNotFoundError, PostAccessDeniedError):
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise SQLAlchemyError(
                f"Database error while updating post {post_id}: {str(e)}"
            ) from e

    def delete(self, post_id: int, user_id: int) -> bool:
        """Delete a post for the specified user.

        Args:
            post_id: ID of the post to delete
            user_id: ID of the user who should own the post

        Returns:
            bool: True if post was deleted, False if not found

        Raises:
            PostAccessDeniedError: If post exists but is owned by different user
            SQLAlchemyError: If database operation fails

        Example:
            deleted = repository.delete(post_id=1, user_id=1)
            if deleted:
                print("Post deleted successfully")
        """
        try:
            # Check if post exists and get it
            post = self.get_by_id(post_id, user_id)

            if not post:
                # Check if post exists but belongs to different user
                post_exists_statement = select(Post).where(Post.id == post_id)
                existing_post = self.session.exec(post_exists_statement).first()

                if existing_post:
                    raise PostAccessDeniedError(post_id, user_id)

                return False  # Post doesn't exist at all

            # Delete the post
            self.session.delete(post)
            self.session.commit()

            return True

        except PostAccessDeniedError:
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise SQLAlchemyError(
                f"Database error while deleting post {post_id}: {str(e)}"
            ) from e

    def search_for_user(
        self,
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 100,
        published_only: bool = False,
    ) -> list[Post]:
        """Search posts by title or content for a specific user.

        Args:
            user_id: ID of the user whose posts to search
            query: Search query string
            skip: Number of posts to skip (for pagination)
            limit: Maximum number of posts to return
            published_only: If True, only search published posts

        Returns:
            List[Post]: List of matching posts owned by the user

        Raises:
            SQLAlchemyError: If database operation fails

        Example:
            posts = repository.search_for_user(
                user_id=1, query="python", skip=0, limit=10
            )
        """
        try:
            # Build search query (case-insensitive)
            search_pattern = f"%{query.lower()}%"

            conditions = [
                Post.user_id == user_id,
                or_(
                    func.lower(Post.title).like(search_pattern),
                    func.lower(Post.content).like(search_pattern),
                ),
            ]

            if published_only:
                conditions.append(Post.published == True)

            statement = (
                select(Post)
                .where(and_(*conditions))
                .order_by(desc(Post.created_at))
                .offset(skip)
                .limit(limit)
            )

            result = self.session.exec(statement)
            return list(result.all())

        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while searching posts for user {user_id}: {str(e)}"
            ) from e

    def get_posts_by_location_prefix(
        self,
        user_id: int,
        location_prefix: str,
        skip: int = 0,
        limit: int = 100,
        published_only: bool = False,
    ) -> list[Post]:
        """Get posts by location prefix (GEOHASH prefix) for a specific user.

        Args:
            user_id: ID of the user whose posts to retrieve
            location_prefix: GEOHASH prefix to search for
            skip: Number of posts to skip (for pagination)
            limit: Maximum number of posts to return
            published_only: If True, only return published posts

        Returns:
            List[Post]: List of posts with matching location prefix owned by the user

        Raises:
            SQLAlchemyError: If database operation fails

        Example:
            posts = repository.get_posts_by_location_prefix(
                user_id=1, location_prefix="u4pr", skip=0, limit=10
            )
        """
        try:
            # Build location prefix query
            location_pattern = f"{location_prefix}%"

            conditions = [
                Post.user_id == user_id,
                Post.location.like(location_pattern),
            ]

            if published_only:
                conditions.append(Post.published == True)

            statement = (
                select(Post)
                .where(and_(*conditions))
                .order_by(desc(Post.created_at))
                .offset(skip)
                .limit(limit)
            )

            result = self.session.exec(statement)
            return list(result.all())

        except SQLAlchemyError as e:
            raise SQLAlchemyError(
                f"Database error while retrieving posts by location prefix "
                f"for user {user_id}: {str(e)}"
            ) from e