"""Test configuration and fixtures.

This module provides test configuration, database setup, fixtures,
and test data factories for comprehensive testing of the API server.
"""

import pytest
import pytest_asyncio
from typing import Generator, AsyncGenerator, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool
from datetime import datetime, timedelta
from decimal import Decimal

from src.api_server.main import app
from src.api_server.database import get_session
from src.api_server.config import Settings
from src.api_server.models.user import User, UserCreate
from src.api_server.models.item import Item, ItemCreate
from src.api_server.services.auth_service import AuthService, LineUserProfile


# Test database configuration
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with test database configuration."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        debug=True,
        log_level="DEBUG",
        environment="testing",
        line_client_id="test_client_id",
        line_client_secret="test_client_secret",
        line_redirect_uri="http://localhost:8000/auth/callback",
        jwt_secret="test_jwt_secret_key_for_testing_only",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60 * 24 * 365  # 1 year for testing
    )


@pytest.fixture(scope="function")
def test_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Clean up
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(test_session: Session) -> TestClient:
    """Create test client with test database session."""
    
    def get_test_session():
        return test_session
    
    # Override the database session dependency
    app.dependency_overrides[get_session] = get_test_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_auth_service(test_settings: Settings) -> Mock:
    """Create mock authentication service for testing."""
    mock_service = Mock(spec=AuthService)
    mock_service.settings = test_settings
    
    # Mock LINE API responses
    mock_service.verify_line_access_token = AsyncMock()
    mock_service.get_line_user_profile = AsyncMock()
    mock_service.authenticate_line_user = AsyncMock()
    
    # Mock JWT operations
    mock_service.create_jwt_token = Mock(return_value="test_jwt_token")
    mock_service.verify_jwt_token = Mock()
    mock_service.extract_token_from_header = Mock(return_value="test_jwt_token")
    mock_service.get_current_user_id = AsyncMock(return_value=1)
    
    return mock_service


@pytest.fixture(scope="function")
def sample_line_profile() -> LineUserProfile:
    """Create sample LINE user profile for testing."""
    return LineUserProfile(
        userId="test_line_user_123",
        displayName="Test User",
        pictureUrl="https://example.com/profile.jpg",
        statusMessage="Hello, World!"
    )


@pytest.fixture(scope="function")
def sample_user_data() -> UserCreate:
    """Create sample user data for testing."""
    return UserCreate(
        line_user_id="test_line_user_123",
        display_name="Test User",
        picture_url="https://example.com/profile.jpg",
        email="test@example.com"
    )


@pytest.fixture(scope="function")
def sample_item_data() -> ItemCreate:
    """Create sample item data for testing."""
    return ItemCreate(
        name="Test Item",
        description="This is a test item",
        price=Decimal("99.99")
    )


@pytest.fixture(scope="function")
def test_user(test_session: Session, sample_user_data: UserCreate) -> User:
    """Create a test user in the database."""
    user = User(**sample_user_data.dict())
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_item(test_session: Session, test_user: User, sample_item_data: ItemCreate) -> Item:
    """Create a test item in the database."""
    item = Item(**sample_item_data.dict(), user_id=test_user.id)
    test_session.add(item)
    test_session.commit()
    test_session.refresh(item)
    return item


@pytest.fixture(scope="function")
def multiple_test_users(test_session: Session) -> list[User]:
    """Create multiple test users in the database."""
    users = []
    for i in range(3):
        user_data = UserCreate(
            line_user_id=f"test_line_user_{i}",
            display_name=f"Test User {i}",
            picture_url=f"https://example.com/profile_{i}.jpg",
            email=f"test{i}@example.com"
        )
        user = User(**user_data.dict())
        test_session.add(user)
        users.append(user)
    
    test_session.commit()
    for user in users:
        test_session.refresh(user)
    
    return users


@pytest.fixture(scope="function")
def multiple_test_items(test_session: Session, test_user: User) -> list[Item]:
    """Create multiple test items for a user."""
    items = []
    for i in range(3):
        item_data = ItemCreate(
            name=f"Test Item {i}",
            description=f"This is test item {i}",
            price=Decimal(f"{10.00 + i}")
        )
        item = Item(**item_data.dict(), user_id=test_user.id)
        test_session.add(item)
        items.append(item)
    
    test_session.commit()
    for item in items:
        test_session.refresh(item)
    
    return items


@pytest.fixture(scope="function")
def auth_headers() -> Dict[str, str]:
    """Create authentication headers for testing."""
    return {"Authorization": "Bearer test_jwt_token"}


@pytest.fixture(scope="function")
def invalid_auth_headers() -> Dict[str, str]:
    """Create invalid authentication headers for testing."""
    return {"Authorization": "Bearer invalid_token"}


class TestDataFactory:
    """Factory class for creating test data."""
    
    @staticmethod
    def create_user_data(
        line_user_id: str = "test_line_user",
        display_name: str = "Test User",
        picture_url: str = "https://example.com/profile.jpg",
        email: str = "test@example.com"
    ) -> UserCreate:
        """Create user data with customizable fields."""
        return UserCreate(
            line_user_id=line_user_id,
            display_name=display_name,
            picture_url=picture_url,
            email=email
        )
    
    @staticmethod
    def create_item_data(
        name: str = "Test Item",
        description: str = "Test description",
        price: Decimal = Decimal("10.00")
    ) -> ItemCreate:
        """Create item data with customizable fields."""
        return ItemCreate(
            name=name,
            description=description,
            price=price
        )
    
    @staticmethod
    def create_line_profile(
        user_id: str = "test_line_user",
        display_name: str = "Test User",
        picture_url: str = "https://example.com/profile.jpg",
        status_message: str = "Hello!"
    ) -> LineUserProfile:
        """Create LINE profile data with customizable fields."""
        return LineUserProfile(
            userId=user_id,
            displayName=display_name,
            pictureUrl=picture_url,
            statusMessage=status_message
        )


@pytest.fixture(scope="function")
def test_data_factory() -> TestDataFactory:
    """Provide test data factory."""
    return TestDataFactory()


# Mock patches for external services
@pytest.fixture(scope="function")
def mock_line_api():
    """Mock LINE API calls."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "userId": "test_line_user_123",
            "displayName": "Test User",
            "pictureUrl": "https://example.com/profile.jpg",
            "statusMessage": "Hello, World!"
        }
        
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        yield mock_client


@pytest.fixture(scope="function")
def mock_line_token_verify():
    """Mock LINE token verification API."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "scope": "profile",
            "client_id": "test_client_id",
            "expires_in": 3600
        }
        
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        yield mock_client


# Async test configuration
@pytest_asyncio.fixture(scope="function")
async def async_test_session(test_engine) -> AsyncGenerator[Session, None]:
    """Create async test database session."""
    async with Session(test_engine) as session:
        yield session


# Performance testing utilities
@pytest.fixture(scope="function")
def performance_timer():
    """Timer utility for performance testing."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = datetime.utcnow()
        
        def stop(self):
            self.end_time = datetime.utcnow()
        
        @property
        def duration(self) -> timedelta:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return timedelta(0)
        
        @property
        def duration_ms(self) -> float:
            return self.duration.total_seconds() * 1000
    
    return Timer()


# Database state utilities
@pytest.fixture(scope="function")
def db_state_checker(test_session: Session):
    """Utility for checking database state in tests."""
    class DatabaseStateChecker:
        def __init__(self, session: Session):
            self.session = session
        
        def count_users(self) -> int:
            from sqlalchemy import func
            from src.api_server.models.user import User
            result = self.session.exec(select(func.count(User.id)))
            return result.first() or 0
        
        def count_items(self) -> int:
            from sqlalchemy import func
            from src.api_server.models.item import Item
            result = self.session.exec(select(func.count(Item.id)))
            return result.first() or 0
        
        def user_exists(self, line_user_id: str) -> bool:
            from src.api_server.models.user import User
            result = self.session.exec(select(User).where(User.line_user_id == line_user_id))
            return result.first() is not None
        
        def item_exists(self, item_id: int) -> bool:
            from src.api_server.models.item import Item
            result = self.session.exec(select(Item).where(Item.id == item_id))
            return result.first() is not None
    
    return DatabaseStateChecker(test_session)


# Error simulation utilities
@pytest.fixture(scope="function")
def error_simulator():
    """Utility for simulating various error conditions."""
    class ErrorSimulator:
        @staticmethod
        def database_error():
            from sqlalchemy.exc import SQLAlchemyError
            return SQLAlchemyError("Simulated database error")
        
        @staticmethod
        def integrity_error():
            from sqlalchemy.exc import IntegrityError
            return IntegrityError("Simulated integrity error", None, None)
        
        @staticmethod
        def http_error(status_code: int = 500):
            import httpx
            return httpx.HTTPStatusError(
                f"HTTP {status_code}",
                request=Mock(),
                response=Mock(status_code=status_code)
            )
        
        @staticmethod
        def timeout_error():
            import httpx
            return httpx.TimeoutException("Request timeout")
    
    return ErrorSimulator()