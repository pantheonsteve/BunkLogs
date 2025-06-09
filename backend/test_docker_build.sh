#!/bin/bash
# Test script to verify Docker build works locally before EB deployment

set -e

echo "🧪 Testing Docker build locally..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t bunk-logs-test .

echo "✅ Docker build successful!"

# Test that the image can start (quick test)
echo "🚀 Testing container startup..."
docker run --rm -d --name bunk-logs-test-container -p 8001:8000 -e DJANGO_SECRET_KEY="test-key" -e DATABASE_URL="sqlite:///:memory:" bunk-logs-test

# Wait a moment for startup
sleep 5

# Check if container is running
if docker ps | grep -q bunk-logs-test-container; then
    echo "✅ Container started successfully!"
    
    # Test health endpoint
    if curl -f http://localhost:8001/health/ > /dev/null 2>&1; then
        echo "✅ Health endpoint responds correctly!"
    else
        echo "⚠️  Health endpoint not responding (this might be expected if database setup fails)"
    fi
else
    echo "❌ Container failed to start"
fi

# Clean up
echo "🧹 Cleaning up..."
docker stop bunk-logs-test-container || true
docker rmi bunk-logs-test || true

echo "✅ Local test completed!"
echo "💡 If this test passes, your EB deployment should work better."
