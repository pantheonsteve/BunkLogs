#!/bin/bash
# Fast deployment script for Elastic Beanstalk
# This script optimizes for speed and provides better feedback

set -e

echo "🚀 Starting optimized Elastic Beanstalk deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "Dockerfile.fast" ]; then
    print_error "Dockerfile.fast not found. Please run this script from the backend directory."
    exit 1
fi

# Use the fast Dockerfile for deployment
print_status "Using optimized Dockerfile for faster builds..."
cp Dockerfile.fast Dockerfile.deploy

# Test the Docker build locally first (optional but recommended)
if [ "${1}" != "--skip-test" ]; then
    print_status "Testing Docker build locally (use --skip-test to skip)..."
    if docker build -f Dockerfile.deploy -t bunklogs-test . > /tmp/docker-build.log 2>&1; then
        print_success "Local Docker build successful!"
        docker rmi bunklogs-test > /dev/null 2>&1 || true
    else
        print_error "Local Docker build failed. Check /tmp/docker-build.log for details."
        tail -20 /tmp/docker-build.log
        exit 1
    fi
fi

# Deploy to Elastic Beanstalk
print_status "Deploying to Elastic Beanstalk..."

# Rename for EB deployment
mv Dockerfile.deploy Dockerfile

# Check if EB CLI is available
if ! command -v eb &> /dev/null; then
    print_error "EB CLI not found. Install it with: pip install awsebcli"
    exit 1
fi

# Deploy with EB
print_status "Running 'eb deploy'..."
if eb deploy; then
    print_success "Deployment completed successfully! 🎉"
    print_status "Your application should be available shortly."
else
    print_error "Deployment failed. Check the EB logs for more details."
    print_status "Run 'eb logs' to see the deployment logs."
    exit 1
fi

# Cleanup
print_status "Cleaning up temporary files..."
rm -f /tmp/docker-build.log

print_success "Deployment process complete!"
print_status "💡 Tips for faster future deployments:"
print_status "  • Only code changes will trigger rebuilds (requirements are cached)"
print_status "  • Use 'eb deploy --timeout 20' for faster timeout if deployment is stable"
print_status "  • Run './deploy_fast.sh --skip-test' to skip local testing"
