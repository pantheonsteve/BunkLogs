#!/bin/bash

# Local Development Setup Script
set -e

# Set PostgreSQL environment variables for building psycopg on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
    export LDFLAGS="-L/opt/homebrew/opt/postgresql@16/lib"
    export CPPFLAGS="-I/opt/homebrew/opt/postgresql@16/include"
    export PKG_CONFIG_PATH="/opt/homebrew/opt/postgresql@16/lib/pkgconfig"
fi

# Enable reading .env file for Django
export DJANGO_READ_DOT_ENV_FILE=True

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
    # Use Python 3.12 which is required for Django 5.0.13
    python3.12 -m venv venv
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
echo "🐳 Starting container services..."
echo "================================"

# Check if Podman is installed
if command -v podman &> /dev/null; then
    echo "✅ Podman detected"
    CONTAINER_CMD="podman"
    COMPOSE_CMD="podman-compose"
    
    # Check if podman-compose is available, fallback to podman compose
    if ! command -v podman-compose &> /dev/null; then
        COMPOSE_CMD="podman compose"
    fi
    
    # Ensure Podman machine is running
    if ! podman machine list | grep -q "Currently running"; then
        echo "🚀 Starting Podman machine..."
        podman machine start
    fi
    
    # Verify Podman is accessible
    if ! podman info &> /dev/null; then
        echo "⚠️  Podman machine started but not accessible. Please check your Podman installation."
        SKIP_CONTAINERS=true
    else
        SKIP_CONTAINERS=false
    fi
else
    echo "⚠️  Podman not found. Please install Podman Desktop:"
    echo "   • Podman Desktop: https://podman-desktop.io/"
    echo ""
    echo "📝 Alternative: Use local PostgreSQL and Redis installations"
    echo "   For PostgreSQL: brew services start postgresql@16"
    echo "   For Redis: brew install redis && brew services start redis"
    echo ""
    echo "⏩ Skipping container setup for now..."
    SKIP_CONTAINERS=true
fi

if [ "$SKIP_CONTAINERS" != "true" ]; then
    # Start container services (PostgreSQL and Redis)
    echo "🚀 Starting services with $CONTAINER_CMD..."
    $COMPOSE_CMD -f docker-compose.local.yml up -d
    
    # Wait for PostgreSQL to be ready and create database if needed
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Create database if it doesn't exist
    echo "🗄️ Creating database if needed..."
    $CONTAINER_CMD exec bunk_logs_local_postgres createdb -U postgres bunk_logs_local 2>/dev/null || true
    
    # Run migrations
    echo "🗄️ Running database migrations..."
    python manage.py migrate
else
    echo "🗄️ To run migrations later (after setting up database):"
    echo "   python manage.py migrate"
fi

if [ "$SKIP_CONTAINERS" != "true" ]; then
    # Create superuser if it doesn't exist
    echo "👤 Creating superuser (if needed)..."
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@bunklogs.com').exists():
    User.objects.create_superuser(email='admin@bunklogs.com', password='admin123')
    print("✅ Superuser 'admin@bunklogs.com' created with password 'admin123'")
else:
    print("✅ Superuser already exists")
EOF

    # Collect static files
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput
else
    echo "👤 To create superuser later (after setting up database):"
    echo "   python manage.py createsuperuser"
    echo ""
    echo "📁 To collect static files later:"
    echo "   python manage.py collectstatic --noinput"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
if [ "$SKIP_CONTAINERS" != "true" ]; then
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
    echo "To stop container services: $COMPOSE_CMD -f docker-compose.local.yml down"
else
    echo "Next steps:"
    echo "1. Install Podman Desktop from: https://podman-desktop.io/"
    echo "2. Or setup local PostgreSQL and Redis:"
    echo "   brew install redis"
    echo "   brew services start postgresql@16"
    echo "   brew services start redis"
    echo "3. Update your .env file with database connection details"
    echo "4. Run: python manage.py migrate"
    echo "5. Run: python manage.py createsuperuser"
    echo "6. Start Django server: python manage.py runserver"
    echo ""
    echo "Virtual environment is ready! Activate with:"
    echo "source venv/bin/activate"
fi
