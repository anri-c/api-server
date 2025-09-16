"""Database connection and session management.

This module provides SQLModel engine setup, connection pooling, session management,
and database initialization utilities for the API server.
"""

from typing import Generator, Any
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import settings
# Import models to register them with SQLModel
from .models import User, Item  # noqa: F401


# Create database engine with connection pooling
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_size=10,  # Number of connections to maintain in the pool
    max_overflow=20,  # Additional connections that can be created on demand
    pool_timeout=30,  # Timeout for getting connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    poolclass=QueuePool,  # Use QueuePool for connection pooling
    connect_args={
        "check_same_thread": False  # Required for SQLite, ignored for PostgreSQL
    } if settings.database_url.startswith("sqlite") else {}
)


def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session.
    
    This function provides a database session for dependency injection
    in FastAPI endpoints. The session is automatically closed after use.
    
    Yields:
        Session: SQLModel database session
        
    Example:
        @app.get("/items/")
        def get_items(session: Session = Depends(get_session)):
            return session.exec(select(Item)).all()
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def create_db_and_tables() -> None:
    """Create database tables based on SQLModel definitions.
    
    This function creates all tables defined in SQLModel models.
    It should be called during application startup.
    
    Note:
        This function is idempotent - it won't recreate existing tables.
    """
    SQLModel.metadata.create_all(engine)


def drop_db_and_tables() -> None:
    """Drop all database tables.
    
    This function drops all tables defined in SQLModel models.
    Use with caution - this will delete all data!
    
    Warning:
        This function will permanently delete all data in the database.
        Only use for testing or development purposes.
    """
    SQLModel.metadata.drop_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Generator[None, None, None]:
    """FastAPI lifespan context manager for database initialization.
    
    This context manager handles database setup during application startup
    and cleanup during shutdown.
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control to the application
        
    Example:
        app = FastAPI(lifespan=lifespan)
    """
    # Startup: Create database tables
    create_db_and_tables()
    yield
    # Shutdown: Close database connections
    engine.dispose()


def get_database_info() -> dict[str, Any]:
    """Get database connection information for health checks.
    
    Returns:
        dict: Database connection information including URL and pool status
        
    Example:
        info = get_database_info()
        print(f"Database URL: {info['url']}")
        print(f"Pool size: {info['pool_size']}")
    """
    return {
        "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,  # Hide credentials
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "invalid": engine.pool.invalid()
    }


def test_database_connection() -> bool:
    """Test database connection.
    
    Returns:
        bool: True if connection is successful, False otherwise
        
    Example:
        if test_database_connection():
            print("Database connection successful")
        else:
            print("Database connection failed")
    """
    try:
        with Session(engine) as session:
            session.exec("SELECT 1")
            return True
    except Exception:
        return False
