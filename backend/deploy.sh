#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to backend directory
cd "$SCRIPT_DIR"

echo "🚀 Deploying Django Backend to Elastic Beanstalk..."
echo "================================================"

# Deploy to EB
echo "📦 Deploying application..."
eb deploy

# Run migrations
echo "🗄️  Running database migrations..."
eb ssh -c "sudo docker exec \$(sudo docker ps -q) python manage.py migrate --noinput"

# Show status
echo "✅ Deployment complete!"
eb status

echo ""
echo "📋 To view logs, run: eb logs"