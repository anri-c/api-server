# API Server

A modern FastAPI-based REST API server with PostgreSQL database, LINE OAuth authentication, and comprehensive testing.

## Features

- **FastAPI Framework**: High-performance async web framework with automatic API documentation
- **PostgreSQL Database**: Robust relational database with SQLModel ORM
- **LINE OAuth Authentication**: Secure authentication using LINE Login
- **JWT Token Management**: Stateless authentication with JSON Web Tokens
- **Comprehensive Testing**: Unit and integration tests with high coverage
- **Code Quality**: Automated linting, formatting, and type checking
- **Development Tools**: Pre-commit hooks, quality checks, and development scripts

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL database
- LINE Developer Account (for OAuth)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd api-server
   ```

2. **Set up development environment**
   ```bash
   ./scripts/setup-dev.sh
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Set up database**
   ```bash
   ./scripts/db-migrate.sh
   ./scripts/db-seed.sh  # Optional: add sample data
   ```

5. **Start development server**
   ```bash
   ./scripts/dev-server.sh
   ```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development

### Project Structure

```
api-server/
├── src/api_server/          # Main application code
│   ├── models/              # SQLModel database models
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic layer
│   ├── routers/             # API route handlers
│   ├── schemas/             # Pydantic schemas for API
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection setup
│   ├── dependencies.py      # FastAPI dependencies
│   ├── exceptions.py        # Custom exception classes
│   ├── logging_config.py    # Logging configuration
│   ├── middleware.py        # Custom middleware
│   └── main.py              # FastAPI application entry point
├── tests/                   # Test files
├── scripts/                 # Development scripts
├── .env.example             # Environment variables template
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

### Available Scripts

| Script | Description |
|--------|-------------|
| `./scripts/setup-dev.sh` | Set up development environment |
| `./scripts/dev-server.sh` | Start development server |
| `./scripts/db-migrate.sh` | Run database migrations |
| `./scripts/db-seed.sh` | Seed database with sample data |
| `./scripts/lint.sh` | Run linting checks |
| `./scripts/format.sh` | Format code |
| `./scripts/test.sh` | Run tests with coverage |
| `./scripts/quality-check.sh` | Run all quality checks |

### Make Commands

You can also use Make commands for common tasks:

```bash
make help              # Show available commands
make dev-install       # Install development dependencies
make lint              # Run linting checks
make format            # Format code
make test              # Run tests with coverage
make quality-check     # Run all quality checks
make dev-server        # Start development server
make clean             # Clean up cache files
```

### Code Quality

This project uses several tools to maintain code quality:

- **Ruff**: Fast Python linter and formatter
- **mypy**: Static type checking (currently disabled due to complex type issues)
- **pytest**: Testing framework with async support
- **pre-commit**: Git hooks for code quality

Run quality checks:
```bash
./scripts/quality-check.sh
```

### Testing

Run tests with coverage:
```bash
./scripts/test.sh
```

Run specific test files:
```bash
uv run pytest tests/test_auth_service.py -v
```

Run tests with specific markers:
```bash
uv run pytest -m "not integration" -v
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost/dbname` |
| `DEBUG` | Enable debug mode | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LINE_CLIENT_ID` | LINE OAuth client ID | `your_line_client_id` |
| `LINE_CLIENT_SECRET` | LINE OAuth client secret | `your_line_client_secret` |
| `LINE_REDIRECT_URI` | LINE OAuth redirect URI | `http://localhost:8000/auth/callback` |
| `JWT_SECRET` | JWT signing secret | `your_jwt_secret_key` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | JWT expiration time in minutes | `1440` |

### LINE OAuth Setup

1. Create a LINE Developer account at https://developers.line.biz/
2. Create a new LINE Login channel
3. Configure the redirect URI: `http://localhost:8000/auth/callback`
4. Copy the Channel ID and Channel Secret to your `.env` file

## API Documentation

### Authentication

The API uses LINE OAuth for authentication with JWT tokens:

1. **LINE Login**: Redirect users to LINE OAuth
2. **Callback**: Handle OAuth callback and create JWT token
3. **Protected Routes**: Include JWT token in Authorization header

Example:
```bash
curl -H "Authorization: Bearer <jwt_token>" http://localhost:8000/api/items/
```

### Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/health` | Health check | No |
| POST | `/auth/line/callback` | LINE OAuth callback | No |
| GET | `/api/items/` | List user's items | Yes |
| POST | `/api/items/` | Create new item | Yes |
| GET | `/api/items/{id}` | Get item by ID | Yes |
| PUT | `/api/items/{id}` | Update item | Yes |
| DELETE | `/api/items/{id}` | Delete item | Yes |

For detailed API documentation, visit http://localhost:8000/docs when the server is running.

## Deployment

### Production Setup

1. **Environment Configuration**
   ```bash
   export DEBUG=false
   export LOG_LEVEL=WARNING
   export DATABASE_URL=postgresql://user:pass@prod-db/dbname
   ```

2. **Database Migration**
   ```bash
   ./scripts/db-migrate.sh
   ```

3. **Run with Production Server**
   ```bash
   uv run uvicorn api_server.main:app --host 0.0.0.0 --port 8000
   ```

### Docker (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Run quality checks**
   ```bash
   ./scripts/quality-check.sh
   ```
5. **Commit your changes**
   ```bash
   git commit -m "Add your feature"
   ```
6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Create a Pull Request**

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions and methods
- Write comprehensive docstrings
- Maintain test coverage above 80%
- Use meaningful variable and function names

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check PostgreSQL is running
   - Verify DATABASE_URL in .env file
   - Ensure database exists

2. **LINE OAuth Error**
   - Verify LINE_CLIENT_ID and LINE_CLIENT_SECRET
   - Check redirect URI configuration
   - Ensure LINE channel is properly configured

3. **Import Errors**
   - Run `uv sync` to install dependencies
   - Check Python version (3.13+ required)

4. **Test Failures**
   - Ensure test database is configured
   - Run `./scripts/db-migrate.sh` for test database
   - Check for conflicting processes on test ports

### Getting Help

- Check the [FastAPI documentation](https://fastapi.tiangolo.com/)
- Review [SQLModel documentation](https://sqlmodel.tiangolo.com/)
- Check [LINE Login documentation](https://developers.line.biz/en/docs/line-login/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.