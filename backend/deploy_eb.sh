#!/bin/bash
# Elastic Beanstalk deployment script
# Place this in backend/deploy_eb.sh

set -e

echo "Preparing Elastic Beanstalk deployment..."

# Create deployment directory
rm -rf eb-deployment
mkdir eb-deployment

# Copy application files
cp -r . eb-deployment/
cd eb-deployment

# Use the EB-optimized Dockerfile
cp Dockerfile.eb Dockerfile

# Remove unnecessary files for deployment
rm -rf .git
rm -rf __pycache__
rm -rf *.pyc
rm -rf .pytest_cache
rm -rf .venv
rm -rf eb-deployment
rm -rf compose
rm -rf docker-compose*.yml
rm -rf .envs

# Create a simple .env file for EB environment variables
cat > .env << EOF
DJANGO_SETTINGS_MODULE=config.settings.production
EOF

echo "Deployment package ready in eb-deployment directory"
echo "You can now zip this directory and upload to Elastic Beanstalk"
echo ""
echo "To zip: cd eb-deployment && zip -r ../bunk-logs-eb.zip . && cd .."
echo "Then upload bunk-logs-eb.zip to Elastic Beanstalk"
