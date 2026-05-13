# BunkLogs Backend - Podman Setup Guide

This guide provides all the necessary commands to run the BunkLogs backend using podman instead of Docker.

## Prerequisites

1. **Install podman** (if not already installed):
   ```bash
   # On macOS with Homebrew
   brew install podman
   
   # Start podman machine
   podman machine init
   podman machine start
   ```

2. **Install podman-compose** (Docker Compose compatibility):
   ```bash
   pip3 install podman-compose
   # OR
   brew install podman-compose
   ```

## Quick Start Commands

### 1. Navigate to Backend Directory
```bash
cd /Users/steve.bresnick/Projects/BunkLogs/backend
```

### 2. Build and Start All Services
```bash
# Using podman-compose (recommended)
podman-compose -f docker-compose.local.yml up --build

# Or run in detached mode
podman-compose -f docker-compose.local.yml up --build -d
```

### 3. Stop All Services
```bash
podman-compose -f docker-compose.local.yml down
```

### 4. Stop and Remove Volumes (Clean Reset)
```bash
podman-compose -f docker-compose.local.yml down -v
```

## Individual Service Commands

### PostgreSQL Database
```bash
# Start just PostgreSQL
podman-compose -f docker-compose.local.yml up postgres -d

# Connect to PostgreSQL
podman exec -it bunk_logs_local_postgres psql -U postgres -d bunk_logs

# View PostgreSQL logs
podman logs bunk_logs_local_postgres
```

### Redis
```bash
# Start just Redis
podman-compose -f docker-compose.local.yml up redis -d

# Connect to Redis CLI
podman exec -it bunk_logs_local_redis redis-cli

# View Redis logs
podman logs bunk_logs_local_redis
```

### Django Application
```bash
# Build Django image
podman-compose -f docker-compose.local.yml build django

# Start Django (after postgres and redis are running)
podman-compose -f docker-compose.local.yml up django

# Run Django management commands
podman exec -it bunk_logs_local_django python manage.py migrate
podman exec -it bunk_logs_local_django python manage.py createsuperuser
podman exec -it bunk_logs_local_django python manage.py collectstatic

# Access Django shell
podman exec -it bunk_logs_local_django python manage.py shell
```

### Mailpit (Email Testing)
```bash
# Start Mailpit
podman-compose -f docker-compose.local.yml up mailpit -d

# Access Mailpit web interface at: http://localhost:8025
```

## Development Workflow

### 1. First Time Setup
```bash
# Navigate to backend
cd /Users/steve.bresnick/Projects/BunkLogs/backend

# Build and start all services
podman-compose -f docker-compose.local.yml up --build -d

# Run initial migrations
podman exec -it bunk_logs_local_django python manage.py migrate

# Create superuser
podman exec -it bunk_logs_local_django python manage.py createsuperuser

# Load sample data (if available)
podman exec -it bunk_logs_local_django python manage.py loaddata sample_data.json
```

### 2. Daily Development
```bash
# Start services
podman-compose -f docker-compose.local.yml up -d

# View logs
podman-compose -f docker-compose.local.yml logs -f django

# Stop when done
podman-compose -f docker-compose.local.yml down
```

### 3. Testing CounselorLog Feature
```bash
# Run Django shell to test the model
podman exec -it bunk_logs_local_django python manage.py shell

# In the shell:
# from bunklogs.models import CounselorLog
# from django.contrib.auth import get_user_model
# User = get_user_model()
# counselor = User.objects.filter(role='counselor').first()
# log = CounselorLog.objects.create(counselor=counselor, day_quality=4, support=3, elaboration="Test log")
# print(log)
```

## Troubleshooting

### Common Issues and Solutions

1. **Port Already in Use**
   ```bash
   # Kill processes using ports
   sudo lsof -ti:8000 | xargs kill -9
   sudo lsof -ti:5432 | xargs kill -9
   
   # Or change ports in docker-compose.local.yml
   ```

2. **Permission Issues**
   ```bash
   # Fix volume permissions
   sudo chown -R $(id -u):$(id -g) /Users/steve.bresnick/Projects/BunkLogs/backend
   ```

3. **Database Connection Issues**
   ```bash
   # Restart PostgreSQL
   podman restart bunk_logs_local_postgres
   
   # Check PostgreSQL is ready
   podman exec bunk_logs_local_postgres pg_isready
   ```

4. **Clean Rebuild**
   ```bash
   # Stop everything
   podman-compose -f docker-compose.local.yml down -v
   
   # Remove all images
   podman rmi $(podman images -q)
   
   # Rebuild from scratch
   podman-compose -f docker-compose.local.yml up --build
   ```

### Viewing Logs
```bash
# All services
podman-compose -f docker-compose.local.yml logs -f

# Specific service
podman-compose -f docker-compose.local.yml logs -f django
podman-compose -f docker-compose.local.yml logs -f postgres
```

### Accessing Services
- **Django Application**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin
- **API Root**: http://localhost:8000/api/v1/
- **CounselorLog API**: http://localhost:8000/api/v1/counselor-logs/
- **Mailpit (Email Testing)**: http://localhost:8025
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Alternative: Pure Podman Commands (without podman-compose)

If you prefer not to use podman-compose, here are the equivalent podman commands:

### Network and Volumes
```bash
# Create network
podman network create bunk_logs_network

# Create volumes
podman volume create bunk_logs_local_postgres_data
podman volume create bunk_logs_local_postgres_data_backups
podman volume create static_volume
podman volume create media_volume
```

### Start Services Individually
```bash
# PostgreSQL
podman run -d \
  --name bunk_logs_local_postgres \
  --network bunk_logs_network \
  -v bunk_logs_local_postgres_data:/var/lib/postgresql/data \
  -v bunk_logs_local_postgres_data_backups:/backups \
  --env-file ./.envs/.local/.postgres \
  -p 5432:5432 \
  postgres:16

# Redis
podman run -d \
  --name bunk_logs_local_redis \
  --network bunk_logs_network \
  -p 6379:6379 \
  redis:7

# Mailpit
podman run -d \
  --name bunk_logs_local_mailpit \
  --network bunk_logs_network \
  -p 8025:8025 \
  docker.io/axllent/mailpit:latest

# Django (after building the image)
podman build -t bunk_logs_local_django -f ./compose/local/django/Dockerfile --build-arg BUILD_ENVIRONMENT=local .

podman run -d \
  --name bunk_logs_local_django \
  --network bunk_logs_network \
  -v .:/app:z \
  -v static_volume:/app/staticfiles \
  -v media_volume:/app/media \
  --env-file ./.envs/.local/.django \
  --env-file ./.envs/.local/.postgres \
  -e USE_DOCKER=yes \
  -p 8000:8000 \
  bunk_logs_local_django \
  /start
```

## Environment Files

Make sure you have the environment files set up correctly:

- `.envs/.local/.django` - Django settings
- `.envs/.local/.postgres` - PostgreSQL settings

These should already exist in your project. If not, copy from the examples or create them based on your configuration needs.

## Next Steps

1. Start the services with podman-compose
2. Access the Django admin at http://localhost:8000/admin
3. Test the CounselorLog API endpoints at http://localhost:8000/api/v1/counselor-logs/
4. Use the frontend (if running separately) to test the complete counselor log workflow

The CounselorLog feature is now fully integrated and ready for testing with podman!
