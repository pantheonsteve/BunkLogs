#!/bin/bash
set -e

echo "🚀 Fast EB Deploy - Optimized for sub-10 minute builds"
echo "========================================================="

# Check if we're in the right directory
if [ ! -f "Dockerfile.fast-eb" ]; then
    echo "❌ Error: Dockerfile.fast-eb not found. Run from backend directory."
    exit 1
fi

# Backup current Dockerfile and use the fast one
if [ -f "Dockerfile" ]; then
    cp Dockerfile Dockerfile.backup.$(date +%s)
fi
cp Dockerfile.fast-eb Dockerfile

echo "✅ Using optimized Dockerfile for faster builds"

# Deploy with increased timeout
echo "🚀 Starting EB deployment..."
eb deploy --timeout 30 || {
    echo "❌ Deployment failed"
    # Restore original Dockerfile
    if [ -f "Dockerfile.backup.*" ]; then
        latest_backup=$(ls -t Dockerfile.backup.* | head -n1)
        cp "$latest_backup" Dockerfile
        echo "🔄 Restored original Dockerfile"
    fi
    exit 1
}

echo "✅ Deployment successful!"

# Restore original Dockerfile
if [ -f "Dockerfile.backup.*" ]; then
    latest_backup=$(ls -t Dockerfile.backup.* | head -n1)
    cp "$latest_backup" Dockerfile
    rm Dockerfile.backup.*
    echo "🔄 Restored original Dockerfile"
fi

echo "🎉 Fast deployment complete!"
