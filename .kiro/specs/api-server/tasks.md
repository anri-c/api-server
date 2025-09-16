# Implementation Plan

- [x] 1. Set up project structure and dependencies
  - Initialize uv project with pyproject.toml configuration
  - Add FastAPI, SQLModel, PostgreSQL, and authentication dependencies
  - Configure Ruff for linting and formatting
  - Set up basic project directory structure
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Implement configuration management
  - Create config.py with Pydantic settings for database, LINE login, and JWT
  - Add environment variable support for all configuration values
  - Implement configuration validation and error handling
  - _Requirements: 1.4, 6.5_

- [x] 3. Set up database connection and models
- [x] 3.1 Implement database connection utilities
  - Create database.py with SQLModel engine and session management
  - Implement connection pooling and session dependency injection
  - Add database initialization and table creation logic
  - _Requirements: 4.5, 5.1, 5.3_

- [x] 3.2 Create User model with LINE integration
  - Implement User SQLModel with LINE user fields (line_user_id, display_name, etc.)
  - Add proper type hints and validation for all user fields
  - Create database table with appropriate constraints and indexes
  - _Requirements: 4.1, 4.4, 6.4_

- [x] 3.3 Create Item model with user relationships
  - Implement Item SQLModel with user foreign key relationship
  - Add comprehensive type hints and field validation
  - Create database table with proper relationships and constraints
  - _Requirements: 4.1, 4.4, 6.4_

- [x] 4. Implement authentication system
- [x] 4.1 Create authentication service
  - Implement AuthService class with LINE OAuth verification
  - Add JWT token creation and validation methods
  - Include comprehensive type hints for all authentication functions
  - Add error handling for authentication failures
  - _Requirements: 3.1, 3.2, 3.3, 6.4_

- [x] 4.2 Create user repository and service
  - Implement UserRepository with database operations for user management
  - Create UserService with business logic for user creation and retrieval
  - Add proper type hints and error handling for all user operations
  - _Requirements: 4.5, 4.6, 6.4_

- [x] 4.3 Implement authentication middleware and dependencies
  - Create JWT token validation dependency for protected routes
  - Implement current user dependency injection
  - Add authentication middleware for request processing
  - Include comprehensive error handling for authentication failures
  - _Requirements: 3.1, 3.2, 3.4, 6.4_

- [x] 5. Create API schemas and validation
- [x] 5.1 Implement authentication schemas
  - Create Pydantic schemas for LINE login requests and responses
  - Implement JWT token response schemas with proper type hints
  - Add user response schemas for API endpoints
  - Include comprehensive validation rules for all authentication data
  - _Requirements: 4.1, 4.2, 4.3, 6.4_

- [x] 5.2 Implement item schemas
  - Create Pydantic schemas for item CRUD operations (Create, Update, Response)
  - Add comprehensive validation rules with proper type hints
  - Include user relationship handling in item schemas
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 6.4_

- [-] 6. Implement repository layer
- [x] 6.1 Create item repository
  - Implement ItemRepository with full CRUD operations
  - Add user-scoped item queries (users can only access their own items)
  - Include comprehensive type hints and error handling
  - Add database transaction management
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 4.6_

- [-] 7. Implement service layer
- [x] 7.1 Create item service
  - Implement ItemService with business logic for item operations
  - Add user authorization checks for item access
  - Include comprehensive type hints and validation
  - Add proper error handling and business rule enforcement
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 8. Create API routers and endpoints
- [x] 8.1 Implement health check endpoint
  - Create health router with basic health check endpoint
  - Add database connectivity check in health endpoint
  - Include proper response schemas and error handling
  - _Requirements: 2.1_

- [x] 8.2 Implement authentication endpoints
  - Create auth router with LINE login callback endpoint
  - Implement JWT token generation and user creation/login logic
  - Add proper error handling and response schemas
  - Include comprehensive type hints for all endpoint functions
  - _Requirements: 3.1, 3.2, 3.3, 6.4_

- [x] 8.3 Implement item CRUD endpoints
  - Create items router with full CRUD operations (GET, POST, PUT, DELETE)
  - Add authentication requirements for all item endpoints
  - Implement user-scoped operations (users can only manage their own items)
  - Include proper request/response schemas and error handling
  - Add comprehensive type hints for all endpoint functions
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 6.4_

- [x] 9. Implement error handling and logging
- [x] 9.1 Create global exception handlers
  - Implement custom exception classes for different error types
  - Create FastAPI global exception handlers for consistent error responses
  - Add proper HTTP status codes and error message formatting
  - Include comprehensive type hints for all exception handling code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.4_

- [x] 9.2 Add logging configuration
  - Implement structured logging with proper log levels
  - Add request/response logging middleware
  - Include error logging with context information
  - Configure log formatting and output destinations
  - _Requirements: 3.2, 6.5_

- [x] 10. Create FastAPI application setup
  - Implement main.py with FastAPI application initialization
  - Register all routers and configure middleware
  - Add database startup/shutdown lifecycle management
  - Include CORS configuration and security headers
  - Add comprehensive type hints for application setup
  - _Requirements: 1.4, 6.4, 6.5_

- [x] 11. Implement comprehensive testing
- [x] 11.1 Set up test infrastructure
  - Create conftest.py with test database setup and fixtures
  - Implement test client configuration with authentication mocking
  - Add test data factories for users and items
  - Configure pytest with async support and coverage reporting
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 11.2 Write unit tests for services and repositories
  - Create unit tests for AuthService with mocked LINE API calls
  - Implement unit tests for UserService and ItemService
  - Add unit tests for UserRepository and ItemRepository
  - Include comprehensive test coverage for all business logic
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 11.3 Write integration tests for API endpoints
  - Create integration tests for authentication endpoints with real database
  - Implement integration tests for item CRUD endpoints
  - Add tests for error handling and edge cases
  - Include tests for user authorization and data isolation
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 12. Add development tools and quality checks
- [ ] 12.1 Configure Ruff and type checking
  - Set up Ruff configuration for linting and formatting
  - Configure mypy for comprehensive type checking
  - Add pre-commit hooks for code quality enforcement
  - Create scripts for running all quality checks
  - _Requirements: 6.3, 6.4_

- [ ] 12.2 Create development scripts and documentation
  - Add development server startup scripts
  - Create database migration and seeding scripts
  - Implement environment setup documentation
  - Add API documentation and usage examples
  - _Requirements: 6.5, 6.6_