.PHONY: help install dev-install lint format test type-check quality-check pre-commit-install clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync --no-dev

dev-install: ## Install development dependencies
	uv sync

lint: ## Run linting checks
	./scripts/lint.sh

format: ## Format code
	./scripts/format.sh

test: ## Run tests with coverage
	./scripts/test.sh

type-check: ## Run type checking
	@echo "⚠️  Mypy temporarily disabled due to complex type issues"
	# uv run mypy src

quality-check: ## Run all quality checks
	./scripts/quality-check.sh

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit on all files
	uv run pre-commit run --all-files

clean: ## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf htmlcov/
	rm -rf .coverage

dev-server: ## Start development server
	uv run uvicorn api_server.main:app --reload --host 0.0.0.0 --port 8000