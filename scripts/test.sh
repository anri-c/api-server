#!/bin/bash
set -e

echo "🧪 Running tests with coverage..."
uv run pytest --cov=src --cov-report=term-missing --cov-report=html

echo "✅ Tests completed!"