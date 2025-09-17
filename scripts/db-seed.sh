#!/bin/bash
set -e

echo "🌱 Database seeding script..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

echo "📊 Seeding database with sample data..."
uv run python -c "
import asyncio
from decimal import Decimal
from api_server.database import get_session
from api_server.models.user import User
from api_server.models.item import Item
from sqlmodel import Session

def seed_database():
    with next(get_session()) as session:
        # Check if data already exists
        existing_users = session.query(User).count()
        if existing_users > 0:
            print('⚠️  Database already contains data. Skipping seeding.')
            return
        
        print('Creating sample users...')
        # Create sample users
        user1 = User(
            line_user_id='sample_user_1',
            display_name='Sample User 1',
            email='user1@example.com',
            picture_url='https://example.com/avatar1.jpg'
        )
        user2 = User(
            line_user_id='sample_user_2',
            display_name='Sample User 2',
            email='user2@example.com',
            picture_url='https://example.com/avatar2.jpg'
        )
        
        session.add(user1)
        session.add(user2)
        session.commit()
        session.refresh(user1)
        session.refresh(user2)
        
        print('Creating sample items...')
        # Create sample items
        items = [
            Item(name='Laptop', description='High-performance laptop', price=Decimal('999.99'), user_id=user1.id),
            Item(name='Mouse', description='Wireless mouse', price=Decimal('29.99'), user_id=user1.id),
            Item(name='Keyboard', description='Mechanical keyboard', price=Decimal('79.99'), user_id=user1.id),
            Item(name='Monitor', description='4K monitor', price=Decimal('299.99'), user_id=user2.id),
            Item(name='Headphones', description='Noise-cancelling headphones', price=Decimal('199.99'), user_id=user2.id),
        ]
        
        for item in items:
            session.add(item)
        
        session.commit()
        
        print(f'✅ Created {len(items)} sample items for {2} users')
        print('🌱 Database seeding completed successfully!')

seed_database()
"

echo "✅ Database seeding completed!"