#!/bin/bash
set -e

echo "🗄️  Database migration script..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

# Load environment variables
source .env

echo "📊 Creating database tables..."
uv run python -c "
from api_server.database import engine
from api_server.models import *
from sqlmodel import SQLModel

print('Creating all tables...')
SQLModel.metadata.create_all(engine)
print('✅ Database tables created successfully!')
"

echo "✅ Database migration completed!"