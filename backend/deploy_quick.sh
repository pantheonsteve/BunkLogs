#!/bin/bash
# Quick development deployment - skips full rebuild for code-only changes
# Use this for rapid iteration when you're only changing Python code

set -e

echo "⚡ Quick deployment for code changes only..."

# Check if this is just a code change (no requirements.txt changes)
if git diff --name-only HEAD~1 | grep -E "requirements/|Dockerfile"; then
    echo "⚠️  Requirements or Docker files changed. Use full deployment instead."
    echo "Run: ./deploy_fast.sh"
    exit 1
fi

# Create minimal Dockerfile for code-only changes
cat > Dockerfile.quick << 'EOF'
# Quick deployment - reuses existing base image
FROM your-app-name:latest AS base

# Only copy changed code files
COPY . /app/

# Quick restart
CMD ["/app/start.sh"]
EOF

echo "🔄 This would use Docker layer caching for super fast deployments..."
echo "💡 For now, use: ./deploy_fast.sh"
echo "💡 Future optimization: Set up CI/CD with proper image caching"

rm -f Dockerfile.quick
