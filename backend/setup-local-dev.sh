#!/bin/bash

# Local Development Setup Script
set -e

echo "🚀 Setting up BunkLogs Backend for Local Development"
echo "=================================================="

# Check if .env exists, if not copy from .env.local
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.local template..."
    cp .env.local .env
    echo "✅ .env file created. Please review and update with your local settings."
else
    echo "✅ .env file already exists."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created."
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements/local.txt

echo ""
echo "🐳 Starting Docker services..."
echo "================================"

# Start Docker services (PostgreSQL and Redis)
docker compose -f docker-compose.local.yml up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "👤 Creating superuser (if needed)..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@bunklogs.com', 'admin123')
    print("✅ Superuser 'admin' created with password 'admin123'")
else:
    print("✅ Superuser already exists")
EOF

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "To start development:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start Django server: python manage.py runserver"
echo "3. Open browser: http://localhost:8000"
echo "4. Admin panel: http://localhost:8000/admin/"
echo "5. API docs: http://localhost:8000/api/docs/"
echo ""
echo "Superuser credentials:"
echo "Username: admin"
echo "Password: admin123"
echo ""
echo "To stop Docker services: docker compose -f docker-compose.local.yml down"
