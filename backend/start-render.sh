#!/bin/bash
# 
# Optimized deployment script for Render.com with bulk operation support
#

set -o errexit
set -o pipefail
set -o nounset

echo "🚀 Starting BunkLogs deployment with bulk operation optimizations..."

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

# Create cache table if it doesn't exist
echo "📊 Setting up cache table..."
python manage.py createcachetable || echo "Cache table already exists"

# Use environment variables for configuration
PORT=${PORT:-8080}
WEB_CONCURRENCY=${WEB_CONCURRENCY:-2}
TIMEOUT=${TIMEOUT:-300}

echo "🌐 Starting server on port $PORT with $WEB_CONCURRENCY workers and ${TIMEOUT}s timeout..."

# Start gunicorn with optimized settings for bulk operations
exec gunicorn config.wsgi \
    --bind 0.0.0.0:$PORT \
    --workers=$WEB_CONCURRENCY \
    --worker-class=sync \
    --timeout=$TIMEOUT \
    --keepalive=2 \
    --max-requests=1000 \
    --max-requests-jitter=50 \
    --preload-app \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info \
    --chdir=/opt/render/project/src/backend
