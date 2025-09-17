#!/bin/bash
set -e

echo "🚀 Starting development server..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file from .env.example"
        echo "📝 Please update the .env file with your configuration"
    else
        echo "❌ .env.example file not found. Please create .env file manually."
        exit 1
    fi
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
uv sync

# Start the development server
echo "🌟 Starting FastAPI development server..."
echo "📍 Server will be available at: http://localhost:8000"
echo "📚 API documentation will be available at: http://localhost:8000/docs"
echo "🔄 Press Ctrl+C to stop the server"
echo ""

uv run uvicorn api_server.main:app --reload --host 0.0.0.0 --port 8000