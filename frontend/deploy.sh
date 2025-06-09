#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to frontend directory
cd "$SCRIPT_DIR"

# Set your bucket and distribution ID here
BUCKET_NAME="clc.bunklogs.net"
DISTRIBUTION_ID="E2CLDWS22HRV27" 

echo "🚀 Deploying Frontend to S3 + CloudFront..."
echo "=========================================="

# Build
echo "🔨 Building production bundle..."
npm run build

# Upload to S3
echo "📤 Uploading to S3..."
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete --cache-control "public, max-age=31536000" --exclude "index.html"
aws s3 cp dist/index.html s3://$BUCKET_NAME/index.html --cache-control "no-cache, no-store, must-revalidate"

# Invalidate CloudFront
echo "🔄 Invalidating CloudFront cache..."
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"

echo "✅ Frontend deployment complete!"
echo "🌐 Your site will be updated globally in a few minutes."