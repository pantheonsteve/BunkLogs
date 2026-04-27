#!/usr/bin/env bash
# Build script optimized for Render.com deployment
set -o errexit

echo "🔧 Installing Python dependencies..."
pip install -r requirements/production.txt

echo "📦 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗄️ Running database migrations..."
# Before each migrate attempt, wait until Postgres is accepting connections AND
# is not in recovery mode (pg_is_in_recovery() = false). A database in recovery
# mode accepts reads but rejects writes, which causes migration cleanup to fail
# mid-transaction even though the migration SQL already ran. Retrying migrate up
# to 5 times with exponential back-off handles any transient re-entry into
# recovery mode that occurs during the migration itself.
MAX_RETRIES=5
WAIT=5
for attempt in $(seq 1 $MAX_RETRIES); do
    echo "  ↳ Waiting for database to be ready (attempt $attempt)..."
    python manage.py wait_for_db
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
