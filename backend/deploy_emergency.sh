#!/bin/bash
# EMERGENCY EB DEPLOYMENT - Ultra Fast
# Use this when you need to deploy ASAP under EB timeout limits

set -e

echo "🚨 EMERGENCY FAST DEPLOYMENT"
echo "============================"
echo "This uses minimal dependencies to avoid EB timeout"
echo "⚠️  Some features may be temporarily disabled"
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Run from backend directory"
    exit 1
fi

# Backup current files
timestamp=$(date +%s)
echo "📋 Backing up current files..."
[ -f "Dockerfile" ] && cp Dockerfile "Dockerfile.backup.$timestamp"
[ -f "requirements/production.txt" ] && cp requirements/production.txt "requirements/production.backup.$timestamp"

# Use ultra-fast configuration
echo "🔧 Switching to ultra-fast build configuration..."
cp Dockerfile.ultra-fast Dockerfile
cp requirements/production-fast.txt requirements/production.txt

# Deploy with extended timeout
echo "🚀 Starting ultra-fast deployment..."
echo "⏱️  Expected build time: 5-8 minutes (vs 25+ minutes)"

eb deploy --timeout 30 --verbose || {
    echo "❌ Deployment failed"
    
    # Restore files
    echo "🔄 Restoring original files..."
    [ -f "Dockerfile.backup.$timestamp" ] && cp "Dockerfile.backup.$timestamp" Dockerfile
    [ -f "requirements/production.backup.$timestamp" ] && cp "requirements/production.backup.$timestamp" requirements/production.txt
    
    exit 1
}

echo "✅ Ultra-fast deployment successful!"

# Restore original files
echo "🔄 Restoring original configuration..."
[ -f "Dockerfile.backup.$timestamp" ] && cp "Dockerfile.backup.$timestamp" Dockerfile
[ -f "requirements/production.backup.$timestamp" ] && cp "requirements/production.backup.$timestamp" requirements/production.txt

# Clean up backups
rm -f "Dockerfile.backup.$timestamp" "requirements/production.backup.$timestamp"

echo ""
echo "🎉 Emergency deployment complete!"
echo "⚠️  Note: Some features (pandas, Pillow, MFA) temporarily disabled"
echo "💡 Deploy with full requirements once EB timeout is resolved"
