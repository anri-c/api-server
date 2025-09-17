# Development Guide

This guide covers the development workflow, architecture, coding standards, and best practices for contributing to the API server project.

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL (for integration tests)
- Git
- Code editor with Python support (VS Code, PyCharm, etc.)

### Development Setup

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd api-server
   ./scripts/setup-dev.sh
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your development configuration
   ```

3. **Start Development Server**
   ```bash
   ./scripts/dev-server.sh
   ```

## Project Architecture

### Overview

The project follows a layered architecture pattern:

```
┌─────────────────┐
│   API Routes    │  ← FastAPI routers and endpoints
├─────────────────┤
│   Services      │  ← Business logic layer
├─────────────────┤
│  Repositories   │  ← Data access layer
├─────────────────┤
│    Models       │  ← SQLModel database models
└─────────────────┘
```

### Directory Structure

```
src/api_server/
├── models/              # Database models (SQLModel)
│   ├── __init__.py
│   ├── user.py         # User model
│   └── item.py         # Item model
├── repositories/        # Data access layer
│   ├── __init__.py
│   ├── user_repository.py
│   └── item_repository.py
├── services/           # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py
│   ├── user_service.py
│   └── item_service.py
├── routers/            # API route handlers
│   ├── __init__.py
│   ├── auth.py
│   ├── health.py
│   └── items.py
├── schemas/            # Pydantic schemas for API
│   ├── __init__.py
│   ├── auth_schemas.py
│   └── item_schemas.py
├── config.py           # Configuration management
├── database.py         # Database connection setup
├── dependencies.py     # FastAPI dependencies
├── exceptions.py       # Custom exception classes
├── logging_config.py   # Logging configuration
├── middleware.py       # Custom middleware
└── main.py            # FastAPI application entry point
```

### Layer Responsibilities

#### 1. Models Layer (`models/`)
- Define database schema using SQLModel
- Handle data validation at the database level
- Define relationships between entities

```python
# Example: models/item.py
from sqlmodel import SQLModel, Field
from decimal import Decimal
from datetime import datetime

class Item(SQLModel, table=True):
    __tablename__ = "items"
    
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(max_digits=10, decimal_places=2)
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
```

#### 2. Repositories Layer (`repositories/`)
- Handle database operations (CRUD)
- Abstract database access from business logic
- Implement query optimization

```python
# Example: repositories/item_repository.py
from typing import List, Optional
from sqlmodel import Session, select
from models.item import Item

class ItemRepository:
    def __init__(self, session: Session):
        self.session = session
    
    async def create(self, item: Item) -> Item:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item
    
    async def get_by_id(self, item_id: int) -> Optional[Item]:
        return self.session.get(Item, item_id)
    
    async def get_by_user_id(self, user_id: int) -> List[Item]:
        statement = select(Item).where(Item.user_id == user_id)
        return self.session.exec(statement).all()
```

#### 3. Services Layer (`services/`)
- Implement business logic
- Coordinate between repositories
- Handle complex operations and validations

```python
# Example: services/item_service.py
from typing import List
from repositories.item_repository import ItemRepository
from schemas.item_schemas import ItemCreate, ItemResponse

class ItemService:
    def __init__(self, repository: ItemRepository):
        self.repository = repository
    
    async def create_item(self, item_data: ItemCreate, user_id: int) -> ItemResponse:
        # Business logic validation
        if item_data.price <= 0:
            raise ValueError("Price must be positive")
        
        # Create item
        item = Item(**item_data.dict(), user_id=user_id)
        created_item = await self.repository.create(item)
        
        return ItemResponse.from_orm(created_item)
```

#### 4. Routers Layer (`routers/`)
- Define API endpoints
- Handle HTTP requests/responses
- Implement authentication and authorization

```python
# Example: routers/items.py
from fastapi import APIRouter, Depends, HTTPException
from services.item_service import ItemService
from schemas.item_schemas import ItemCreate, ItemResponse

router = APIRouter(prefix="/api/items", tags=["items"])

@router.post("/", response_model=ItemResponse)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),
    item_service: ItemService = Depends(get_item_service)
):
    return await item_service.create_item(item_data, current_user.id)
```

## Development Workflow

### 1. Feature Development

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write Tests First (TDD)**
   ```bash
   # Create test file
   touch tests/test_your_feature.py
   
   # Write failing tests
   # Implement feature
   # Make tests pass
   ```

3. **Run Quality Checks**
   ```bash
   ./scripts/quality-check.sh
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

### 2. Testing Strategy

#### Test Types

1. **Unit Tests** - Test individual components in isolation
2. **Integration Tests** - Test component interactions
3. **End-to-End Tests** - Test complete user workflows

#### Test Structure

```python
# tests/test_item_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from services.item_service import ItemService
from schemas.item_schemas import ItemCreate

class TestItemService:
    @pytest.fixture
    def mock_repository(self):
        return Mock()
    
    @pytest.fixture
    def item_service(self, mock_repository):
        return ItemService(mock_repository)
    
    @pytest.mark.asyncio
    async def test_create_item_success(self, item_service, mock_repository):
        # Arrange
        item_data = ItemCreate(name="Test Item", price="10.00")
        mock_repository.create = AsyncMock(return_value=Mock(id=1))
        
        # Act
        result = await item_service.create_item(item_data, user_id=1)
        
        # Assert
        assert result.id == 1
        mock_repository.create.assert_called_once()
```

#### Running Tests

```bash
# Run all tests
./scripts/test.sh

# Run specific test file
uv run pytest tests/test_item_service.py -v

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run only unit tests
uv run pytest -m "not integration"

# Run only integration tests
uv run pytest -m integration
```

### 3. Code Quality

#### Linting and Formatting

```bash
# Check code style
./scripts/lint.sh

# Format code
./scripts/format.sh

# Run all quality checks
./scripts/quality-check.sh
```

#### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.12.12
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Coding Standards

### 1. Python Style Guide

Follow PEP 8 with these specific guidelines:

- **Line Length**: 88 characters (Black default)
- **Imports**: Use absolute imports, group by standard/third-party/local
- **Naming**: Use snake_case for functions/variables, PascalCase for classes
- **Type Hints**: Required for all function signatures

```python
# Good
from typing import List, Optional
from decimal import Decimal

async def get_items_by_price_range(
    min_price: Decimal,
    max_price: Optional[Decimal] = None,
    limit: int = 20
) -> List[Item]:
    """Get items within a price range."""
    pass

# Bad
def get_items(minPrice, maxPrice=None, limit=20):
    pass
```

### 2. Documentation Standards

#### Docstrings

Use Google-style docstrings:

```python
def calculate_total_price(items: List[Item], tax_rate: float = 0.1) -> Decimal:
    """Calculate total price including tax.
    
    Args:
        items: List of items to calculate total for
        tax_rate: Tax rate as decimal (default: 0.1 for 10%)
    
    Returns:
        Total price including tax
    
    Raises:
        ValueError: If tax_rate is negative
    
    Example:
        >>> items = [Item(price=Decimal('10.00'))]
        >>> calculate_total_price(items, 0.1)
        Decimal('11.00')
    """
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")
    
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)
```

#### API Documentation

Document API endpoints with comprehensive examples:

```python
@router.post("/", response_model=ItemResponse, status_code=201)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),
    item_service: ItemService = Depends(get_item_service)
) -> ItemResponse:
    """Create a new item.
    
    Creates a new item for the authenticated user.
    
    Args:
        item_data: Item creation data
        current_user: Authenticated user (injected)
        item_service: Item service (injected)
    
    Returns:
        Created item with ID and timestamps
    
    Raises:
        HTTPException: 400 if validation fails
        HTTPException: 401 if not authenticated
    """
    return await item_service.create_item(item_data, current_user.id)
```

### 3. Error Handling

#### Custom Exceptions

Create specific exception classes:

```python
# exceptions.py
class APIException(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ItemNotFoundError(APIException):
    """Raised when an item is not found."""
    
    def __init__(self, item_id: int):
        super().__init__(f"Item with id {item_id} not found", 404)

class ValidationError(APIException):
    """Raised when validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, 400)
```

#### Error Handling in Services

```python
async def get_item_by_id(self, item_id: int, user_id: int) -> ItemResponse:
    """Get item by ID with user access check."""
    try:
        item = await self.repository.get_by_id(item_id)
        if not item:
            raise ItemNotFoundError(item_id)
        
        if item.user_id != user_id:
            raise ItemAccessDeniedError(item_id, user_id)
        
        return ItemResponse.from_orm(item)
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting item {item_id}: {e}")
        raise APIException("Database error occurred", 500) from e
```

### 4. Logging Standards

Use structured logging:

```python
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

async def create_item(self, item_data: ItemCreate, user_id: int) -> ItemResponse:
    """Create a new item."""
    logger.info(
        "Creating item for user",
        extra={
            "user_id": user_id,
            "item_name": item_data.name,
            "item_price": str(item_data.price)
        }
    )
    
    try:
        # Implementation
        logger.info(
            "Item created successfully",
            extra={"item_id": created_item.id, "user_id": user_id}
        )
        return created_item
    
    except Exception as e:
        logger.error(
            "Failed to create item",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise
```

## Database Development

### 1. Model Design

#### Relationships

```python
# models/user.py
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: int | None = Field(default=None, primary_key=True)
    line_user_id: str = Field(unique=True, index=True)
    display_name: str
    
    # Relationship
    items: List["Item"] = Relationship(back_populates="user")

# models/item.py
class Item(SQLModel, table=True):
    __tablename__ = "items"
    
    id: int | None = Field(default=None, primary_key=True)
    name: str
    user_id: int = Field(foreign_key="users.id")
    
    # Relationship
    user: User = Relationship(back_populates="items")
```

#### Indexes

```python
class Item(SQLModel, table=True):
    __tablename__ = "items"
    __table_args__ = (
        Index("idx_items_user_created", "user_id", "created_at"),
        Index("idx_items_price", "price"),
    )
```

### 2. Migrations

Create migration scripts for schema changes:

```python
# migrations/001_create_items_table.py
from sqlmodel import SQLModel
from database import engine

def upgrade():
    """Create items table."""
    SQLModel.metadata.create_all(engine, tables=[Item.__table__])

def downgrade():
    """Drop items table."""
    Item.__table__.drop(engine)
```

### 3. Repository Patterns

#### Base Repository

```python
from typing import TypeVar, Generic, List, Optional
from sqlmodel import SQLModel, Session, select

T = TypeVar('T', bound=SQLModel)

class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: type[T]):
        self.session = session
        self.model = model
    
    async def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
    
    async def get_by_id(self, id: int) -> Optional[T]:
        return self.session.get(self.model, id)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        statement = select(self.model).limit(limit).offset(offset)
        return self.session.exec(statement).all()
```

#### Specific Repository

```python
class ItemRepository(BaseRepository[Item]):
    def __init__(self, session: Session):
        super().__init__(session, Item)
    
    async def get_by_user_id(self, user_id: int) -> List[Item]:
        statement = select(Item).where(Item.user_id == user_id)
        return self.session.exec(statement).all()
    
    async def search_by_name(self, query: str, user_id: int) -> List[Item]:
        statement = (
            select(Item)
            .where(Item.user_id == user_id)
            .where(Item.name.ilike(f"%{query}%"))
        )
        return self.session.exec(statement).all()
```

## API Development

### 1. Schema Design

#### Request/Response Schemas

```python
# schemas/item_schemas.py
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)

class ItemCreate(ItemBase):
    @validator('name')
    def validate_name(cls, v):
        if not v or v.isspace():
            raise ValueError('Name cannot be empty')
        return v.strip()

class ItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    price: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)

class ItemResponse(ItemBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None
    
    class Config:
        from_attributes = True
```

### 2. Router Organization

#### Route Groups

```python
# routers/items.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List

router = APIRouter(prefix="/api/items", tags=["items"])

@router.get("/", response_model=List[ItemResponse])
async def get_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    item_service: ItemService = Depends(get_item_service)
):
    """Get paginated list of user's items."""
    return await item_service.get_items(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        search=search
    )
```

### 3. Dependency Injection

#### Service Dependencies

```python
# dependencies.py
from fastapi import Depends
from sqlmodel import Session
from database import get_session
from repositories.item_repository import ItemRepository
from services.item_service import ItemService

def get_item_repository(session: Session = Depends(get_session)) -> ItemRepository:
    return ItemRepository(session)

def get_item_service(
    repository: ItemRepository = Depends(get_item_repository)
) -> ItemService:
    return ItemService(repository)
```

## Performance Optimization

### 1. Database Optimization

#### Query Optimization

```python
# Use select_related equivalent
async def get_items_with_user(self, user_id: int) -> List[Item]:
    statement = (
        select(Item, User)
        .join(User)
        .where(Item.user_id == user_id)
    )
    results = self.session.exec(statement).all()
    return [item for item, user in results]

# Use pagination
async def get_items_paginated(
    self, 
    user_id: int, 
    limit: int = 20, 
    offset: int = 0
) -> List[Item]:
    statement = (
        select(Item)
        .where(Item.user_id == user_id)
        .limit(limit)
        .offset(offset)
        .order_by(Item.created_at.desc())
    )
    return self.session.exec(statement).all()
```

#### Connection Pooling

```python
# database.py
from sqlmodel import create_engine

engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 2. Caching

#### Response Caching

```python
from functools import lru_cache
from fastapi import Depends
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=128)
def get_cached_config():
    return load_config()

async def get_items_cached(user_id: int) -> List[ItemResponse]:
    cache_key = f"user:{user_id}:items"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    items = await self.repository.get_by_user_id(user_id)
    redis_client.setex(cache_key, 300, json.dumps(items))
    return items
```

## Debugging and Troubleshooting

### 1. Logging for Debugging

```python
import logging
import sys

# Configure detailed logging for development
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log')
    ]
)

# Log SQL queries
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 2. Debug Endpoints

```python
@router.get("/debug/database")
async def debug_database(session: Session = Depends(get_session)):
    """Debug database connection."""
    try:
        result = session.exec("SELECT 1").first()
        return {"status": "connected", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### 3. Testing Utilities

```python
# tests/utils.py
from typing import Dict, Any
from fastapi.testclient import TestClient

def create_test_item(client: TestClient, auth_headers: Dict[str, str]) -> Dict[str, Any]:
    """Helper to create a test item."""
    item_data = {
        "name": "Test Item",
        "description": "Test Description",
        "price": "10.00"
    }
    response = client.post("/api/items/", json=item_data, headers=auth_headers)
    return response.json()

def assert_item_response(item: Dict[str, Any], expected_name: str):
    """Helper to assert item response format."""
    assert "id" in item
    assert item["name"] == expected_name
    assert "created_at" in item
```

This development guide provides comprehensive information for contributing to the project. Follow these guidelines to maintain code quality and consistency across the codebase.