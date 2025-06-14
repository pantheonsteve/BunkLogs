#!/bin/bash

# Setup script for GitHub secrets needed for frontend deployment
# This script helps you identify what secrets need to be set up

echo "🔧 Frontend Deployment Setup Helper"
echo "======================================"
echo ""

echo "📋 Required GitHub Secrets:"
echo ""

echo "1. GCP_SA_KEY"
echo "   Description: Google Cloud Platform service account key (JSON format)"
echo "   Location: Should be downloaded from GCP Console > IAM & Admin > Service Accounts"
echo "   Required permissions:"
echo "   - Storage Admin (for bucket access)"
echo "   - Compute Admin (for CDN setup)"
echo "   - DNS Administrator (for SSL certificate)"
echo ""

echo "2. RENDER_BACKEND_URL" 
echo "   Description: Your Render.com backend URL"
echo "   Example: https://your-backend-app.onrender.com"
echo "   Note: Don't include trailing slash"
echo ""

echo "3. GOOGLE_CLIENT_ID"
echo "   Description: Google OAuth client ID for authentication"
echo "   Location: Google Cloud Console > APIs & Credentials > OAuth 2.0 Client IDs"
echo ""

echo "🔗 Setting up secrets:"
echo "1. Go to: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/settings/secrets/actions"
echo "2. Click 'New repository secret'"
echo "3. Add each secret listed above"
echo ""

echo "🚀 Testing the setup:"
echo "1. Make a small change to any file in the frontend/ directory"
echo "2. Commit and push to main branch"
echo "3. Check GitHub Actions tab for deployment status"
echo ""

echo "📱 Current Git Repository:"
REPO_URL=$(git config --get remote.origin.url)
if [ -n "$REPO_URL" ]; then
    REPO_NAME=$(echo "$REPO_URL" | sed 's/.*github.com[:/]\([^.]*\).*/\1/')
    echo "   Repository: $REPO_NAME"
    echo "   Secrets URL: https://github.com/$REPO_NAME/settings/secrets/actions"
    echo "   Actions URL: https://github.com/$REPO_NAME/actions"
else
    echo "   Could not determine repository URL"
fi

echo ""
echo "✅ Next steps after setting up secrets:"
echo "1. Update your Render.com backend CORS settings"
echo "2. Configure DNS for bunklogs.net domain"
echo "3. Test frontend deployment"
