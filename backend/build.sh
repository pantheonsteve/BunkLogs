#!/usr/bin/env bash
# Build script optimized for Render.com deployment
set -o errexit

echo "🔧 Installing Python dependencies..."
pip install -r requirements/production.txt

echo "📦 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗄️ Running database migrations..."
python manage.py migrate

echo "✅ Build completed successfully!"