#!/bin/bash

# BunkLogs Backend Podman Management Script
# Usage: ./podman-manage.sh [command]

set -e

BACKEND_DIR="/Users/steve.bresnick/Projects/BunkLogs/backend"
COMPOSE_FILE="docker-compose.local.yml"

cd "$BACKEND_DIR"

case "$1" in
    "start")
        echo "🚀 Starting BunkLogs backend with podman..."
        podman-compose -f "$COMPOSE_FILE" up -d
        echo "✅ Services started!"
        echo "📱 Django: http://localhost:8000"
        echo "📧 Mailpit: http://localhost:8025"
        echo "🗄️  PostgreSQL: localhost:5432"
        ;;
    
    "stop")
        echo "🛑 Stopping BunkLogs backend..."
        podman-compose -f "$COMPOSE_FILE" down
        echo "✅ Services stopped!"
        ;;
    
    "restart")
        echo "🔄 Restarting BunkLogs backend..."
        podman-compose -f "$COMPOSE_FILE" down
        podman-compose -f "$COMPOSE_FILE" up -d
        echo "✅ Services restarted!"
        ;;
    
    "build")
        echo "🔨 Building BunkLogs backend..."
        podman-compose -f "$COMPOSE_FILE" build
        echo "✅ Build complete!"
        ;;
    
    "rebuild")
        echo "🔨 Rebuilding and starting BunkLogs backend..."
        podman-compose -f "$COMPOSE_FILE" down
        podman-compose -f "$COMPOSE_FILE" up --build -d
        echo "✅ Rebuild and start complete!"
        ;;
    
    "logs")
        echo "📋 Showing logs (Ctrl+C to exit)..."
        podman-compose -f "$COMPOSE_FILE" logs -f
        ;;
    
    "django-logs")
        echo "📋 Showing Django logs (Ctrl+C to exit)..."
        podman-compose -f "$COMPOSE_FILE" logs -f django
        ;;
    
    "shell")
        echo "🐍 Opening Django shell..."
        podman exec -it bunk_logs_local_django python manage.py shell
        ;;
    
    "migrate")
        echo "🗄️  Running migrations..."
        podman exec -it bunk_logs_local_django python manage.py migrate
        echo "✅ Migrations complete!"
        ;;
    
    "createsuperuser")
        echo "👤 Creating superuser..."
        podman exec -it bunk_logs_local_django python manage.py createsuperuser
        ;;
    
    "collectstatic")
        echo "📁 Collecting static files..."
        podman exec -it bunk_logs_local_django python manage.py collectstatic --noinput
        echo "✅ Static files collected!"
        ;;
    
    "test-counselor-log")
        echo "🧪 Testing CounselorLog model..."
        podman exec -it bunk_logs_local_django python manage.py shell -c "
from bunklogs.models import CounselorLog
from django.contrib.auth import get_user_model
User = get_user_model()

print('=== CounselorLog Model Test ===')
print(f'CounselorLog model fields: {[f.name for f in CounselorLog._meta.fields]}')

# Try to get a counselor user
counselors = User.objects.filter(role='counselor')
print(f'Found {counselors.count()} counselor(s)')

if counselors.exists():
    counselor = counselors.first()
    print(f'Testing with counselor: {counselor.username}')
    
    # Check if there are existing logs
    existing_logs = CounselorLog.objects.filter(counselor=counselor).count()
    print(f'Existing logs for this counselor: {existing_logs}')
    
    print('✅ CounselorLog model is working correctly!')
else:
    print('⚠️  No counselor users found. Create some test users first.')
        "
        ;;
    
    "psql")
        echo "🗄️  Opening PostgreSQL shell..."
        podman exec -it bunk_logs_local_postgres psql -U postgres -d bunk_logs
        ;;
    
    "redis-cli")
        echo "🔴 Opening Redis CLI..."
        podman exec -it bunk_logs_local_redis redis-cli
        ;;
    
    "status")
        echo "📊 Service status:"
        podman-compose -f "$COMPOSE_FILE" ps
        ;;
    
    "clean")
        echo "🧹 Cleaning up (removing containers and volumes)..."
        read -p "This will remove all data. Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            podman-compose -f "$COMPOSE_FILE" down -v
            podman system prune -f
            echo "✅ Cleanup complete!"
        else
            echo "❌ Cleanup cancelled."
        fi
        ;;
    
    "setup")
        echo "🏗️  Initial setup..."
        echo "Building and starting services..."
        podman-compose -f "$COMPOSE_FILE" up --build -d
        
        echo "Waiting for services to be ready..."
        sleep 10
        
        echo "Running migrations..."
        podman exec -it bunk_logs_local_django python manage.py migrate
        
        echo "Collecting static files..."
        podman exec -it bunk_logs_local_django python manage.py collectstatic --noinput
        
        echo "✅ Setup complete!"
        echo "🎯 Next steps:"
        echo "  1. Create a superuser: ./podman-manage.sh createsuperuser"
        echo "  2. Access Django admin: http://localhost:8000/admin"
        echo "  3. Test CounselorLog: ./podman-manage.sh test-counselor-log"
        ;;
    
    *)
        echo "BunkLogs Backend Podman Management Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start              Start all services"
        echo "  stop               Stop all services"
        echo "  restart            Restart all services"
        echo "  build              Build images"
        echo "  rebuild            Rebuild and start"
        echo "  logs               Show all logs"
        echo "  django-logs        Show Django logs only"
        echo "  shell              Open Django shell"
        echo "  migrate            Run Django migrations"
        echo "  createsuperuser    Create Django superuser"
        echo "  collectstatic      Collect static files"
        echo "  test-counselor-log Test CounselorLog model"
        echo "  psql               Open PostgreSQL shell"
        echo "  redis-cli          Open Redis CLI"
        echo "  status             Show service status"
        echo "  clean              Clean up containers and volumes"
        echo "  setup              Initial setup (build, migrate, etc.)"
        echo ""
        echo "Examples:"
        echo "  $0 setup           # First time setup"
        echo "  $0 start           # Start services"
        echo "  $0 logs            # View logs"
        echo "  $0 shell           # Django shell"
        ;;
esac
