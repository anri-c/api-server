#!/bin/bash
set -e

echo "✨ Formatting code with Ruff..."
uv run ruff format src tests

echo "🔧 Fixing linting issues with Ruff..."
uv run ruff check --fix src tests

echo "✅ Code formatting complete!"