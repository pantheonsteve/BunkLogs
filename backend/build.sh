#!/usr/bin/env bash
# Build script optimized for Render.com deployment
set -o errexit

echo "🔧 Installing Python dependencies..."
pip install -r requirements/production.txt

echo "📦 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗄️ Running database migrations..."
# Retry migrate up to 5 times with exponential back-off so that transient
# Postgres states (recovery mode, brief failover) don't fail the build.
MAX_RETRIES=5
WAIT=5
for attempt in $(seq 1 $MAX_RETRIES); do
    if python manage.py migrate; then
        echo "✅ Migration succeeded on attempt $attempt."
        break
    fi
    if [ "$attempt" -eq "$MAX_RETRIES" ]; then
        echo "❌ Migration failed after $MAX_RETRIES attempts. Aborting."
        exit 1
    fi
    echo "⚠️  Migration attempt $attempt failed — retrying in ${WAIT}s..."
    sleep "$WAIT"
    WAIT=$((WAIT * 2))
done

echo "✅ Build completed successfully!"
