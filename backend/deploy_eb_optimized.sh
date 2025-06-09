#!/bin/bash
# Elastic Beanstalk deployment script for BunkLogs backend

set -e

echo "🚀 Starting Elastic Beanstalk deployment..."

# Check if eb cli is installed
if ! command -v eb &> /dev/null; then
    echo "❌ EB CLI is not installed. Please install it first:"
    echo "   pip install awsebcli"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "Dockerfile" ] || [ ! -f "manage.py" ]; then
    echo "❌ Please run this script from the backend directory"
    exit 1
fi

echo "✅ Pre-deployment checks passed"

# Show current configuration
echo "📋 Current deployment configuration:"
echo "   - Dockerfile: $(head -1 Dockerfile | cut -c3-)"
echo "   - Django Settings: DJANGO_SETTINGS_MODULE=config.settings.production"
echo "   - Port: 8000"

# Deploy to EB
echo "🔄 Deploying to Elastic Beanstalk..."
eb deploy --timeout 15

echo "✅ Deployment completed!"
echo "📝 You can check the logs with: eb logs"
echo "🌐 You can open the application with: eb open"
