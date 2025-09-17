#!/bin/bash
set -e

echo "🔧 Setting up development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file from .env.example"
        echo "📝 Please update the .env file with your configuration"
    else
        echo "❌ .env.example file not found. Please create .env file manually."
    fi
fi

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
uv run pre-commit install

# Make scripts executable
echo "🔐 Making scripts executable..."
chmod +x scripts/*.sh

# Run initial quality checks
echo "🔍 Running initial quality checks..."
./scripts/lint.sh

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🚀 To start the development server, run:"
echo "   ./scripts/dev-server.sh"
echo ""
echo "🧪 To run tests, run:"
echo "   ./scripts/test.sh"
echo ""
echo "🔍 To run quality checks, run:"
echo "   ./scripts/quality-check.sh"