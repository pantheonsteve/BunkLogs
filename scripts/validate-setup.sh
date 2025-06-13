#!/bin/bash

# Script to validate GitHub Actions workflow and GCP authentication
# Run this after updating the GCP_SA_KEY secret

set -e

PROJECT_ID="bunklogsauth"
BACKEND_SERVICE="bunk-logs-backend"
REGION="us-central1"

echo "🔍 Validating GitHub Actions and GCP setup..."
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Check if GitHub CLI is available (optional)
if command -v gh &> /dev/null; then
    echo "📋 Checking GitHub repository secrets..."
    if gh secret list | grep -q "GCP_SA_KEY"; then
        echo "✅ GCP_SA_KEY secret exists in GitHub"
    else
        echo "⚠️  GCP_SA_KEY secret not found in GitHub repository"
        echo "   Make sure you've updated the secret in GitHub Settings → Secrets and variables → Actions"
    fi
    echo ""
fi

# Check GitHub Actions workflow file
echo "📋 Validating GitHub Actions workflow..."
WORKFLOW_FILE=".github/workflows/deploy-production.yml"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "❌ GitHub Actions workflow file not found: $WORKFLOW_FILE"
    exit 1
fi

echo "✅ GitHub Actions workflow file exists"

# Check for required secrets in workflow
REQUIRED_SECRETS=("GCP_SA_KEY" "GOOGLE_CLIENT_ID")
for secret in "${REQUIRED_SECRETS[@]}"; do
    if grep -q "\${{ secrets\.$secret }}" "$WORKFLOW_FILE"; then
        echo "✅ Workflow references secret: $secret"
    else
        echo "⚠️  Workflow missing reference to secret: $secret"
    fi
done

echo ""

# Validate workflow syntax (basic check)
echo "📋 Checking workflow syntax..."
if python3 -c "import yaml; yaml.safe_load(open('$WORKFLOW_FILE'))" 2>/dev/null; then
    echo "✅ Workflow YAML syntax is valid"
else
    echo "❌ Workflow YAML syntax has errors"
    exit 1
fi

echo ""

# Check if gcloud is authenticated
if command -v gcloud &> /dev/null; then
    echo "📋 Checking Google Cloud authentication..."
    
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null; then
        CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
        echo "✅ Authenticated with Google Cloud as: $CURRENT_ACCOUNT"
        
        # Check project access
        if gcloud config get-value project > /dev/null 2>&1; then
            CURRENT_PROJECT=$(gcloud config get-value project)
            echo "✅ Current project: $CURRENT_PROJECT"
            
            if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
                echo "✅ Project matches expected: $PROJECT_ID"
            else
                echo "⚠️  Current project ($CURRENT_PROJECT) doesn't match expected ($PROJECT_ID)"
                echo "   Run: gcloud config set project $PROJECT_ID"
            fi
        fi
        
        # Check service account
        SA_EMAIL="github-actions@$PROJECT_ID.iam.gserviceaccount.com"
        if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID > /dev/null 2>&1; then
            echo "✅ Service account exists: $SA_EMAIL"
        else
            echo "❌ Service account not found: $SA_EMAIL"
            echo "   Run the regenerate-gcp-key.sh script to create it"
        fi
        
        # Check Cloud Run service
        if gcloud run services describe $BACKEND_SERVICE --region=$REGION --project=$PROJECT_ID > /dev/null 2>&1; then
            echo "✅ Cloud Run service exists: $BACKEND_SERVICE"
        else
            echo "⚠️  Cloud Run service not found: $BACKEND_SERVICE"
            echo "   This is normal for first deployment"
        fi
        
    else
        echo "❌ Not authenticated with Google Cloud"
        echo "   Run: gcloud auth login"
    fi
else
    echo "⚠️  Google Cloud CLI not installed"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
fi

echo ""

# Check local test setup
echo "📋 Checking local test environment..."

# Backend tests
if [ -f "backend/manage.py" ]; then
    echo "✅ Django backend found"
    
    cd backend
    if [ -f "requirements/local.txt" ]; then
        echo "✅ Backend requirements file exists"
    else
        echo "❌ Backend requirements file missing"
    fi
    
    # Check if we can run tests (without actually running them)
    if python manage.py check > /dev/null 2>&1; then
        echo "✅ Django configuration is valid"
    else
        echo "⚠️  Django configuration has issues"
    fi
    cd ..
else
    echo "❌ Django backend not found"
fi

# Frontend tests
if [ -f "frontend/package.json" ]; then
    echo "✅ Frontend package.json found"
    
    cd frontend
    if [ -f "package-lock.json" ]; then
        echo "✅ Frontend lockfile exists"
    else
        echo "⚠️  Frontend lockfile missing (run npm install)"
    fi
    
    # Check test script
    if grep -q '"test"' package.json; then
        echo "✅ Frontend test script configured"
    else
        echo "❌ Frontend test script missing"
    fi
    cd ..
else
    echo "❌ Frontend package.json not found"
fi

echo ""
echo "🎯 Summary:"
echo "============"
echo "If all checks passed with ✅, your setup should work correctly."
echo "If you see ❌ or ⚠️  items, address them before deploying."
echo ""
echo "🚀 To test the fix:"
echo "1. Make sure you've updated the GCP_SA_KEY secret in GitHub"
echo "2. Push a commit to the main branch"
echo "3. Check the GitHub Actions workflow in the Actions tab"
echo ""
echo "📖 For detailed instructions, see: scripts/fix-gcp-auth.md"
