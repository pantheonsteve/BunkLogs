#!/bin/bash

# Script to regenerate Google Cloud service account key for GitHub Actions
# Run this script to fix the "Invalid JWT Signature" error

set -e

# Configuration
PROJECT_ID="bunklogsauth"
SA_EMAIL="github-actions@bunklogsauth.iam.gserviceaccount.com"
KEY_FILE="github-actions-key.json"

echo "🔧 Fixing Google Cloud Authentication for GitHub Actions"
echo "Project: $PROJECT_ID"
echo "Service Account: $SA_EMAIL"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null; then
    echo "❌ Not authenticated with Google Cloud. Please run:"
    echo "gcloud auth login"
    exit 1
fi

# Set the project
echo "📋 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Check if service account exists
echo "🔍 Checking if service account exists..."
if ! gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID > /dev/null 2>&1; then
    echo "❌ Service account $SA_EMAIL not found."
    echo "Creating service account..."
    
    gcloud iam service-accounts create github-actions \
        --project=$PROJECT_ID \
        --display-name="GitHub Actions Service Account" \
        --description="Service account for GitHub Actions CI/CD"
    
    echo "✅ Service account created."
fi

# Check and add required permissions
echo "🔐 Checking service account permissions..."

REQUIRED_ROLES=(
    "roles/run.admin"
    "roles/cloudsql.client"
    "roles/storage.admin"
    "roles/artifactregistry.writer"
    "roles/cloudbuild.builds.builder"
    "roles/secretmanager.secretAccessor"
    "roles/logging.viewer"
    "roles/compute.loadBalancerAdmin"
)

for role in "${REQUIRED_ROLES[@]}"; do
    echo "Checking role: $role"
    if ! gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --format="value(bindings.role)" \
        --filter="bindings.members:serviceAccount:$SA_EMAIL AND bindings.role:$role" | grep -q "$role"; then
        
        echo "Adding role: $role"
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$role" \
            --quiet
    else
        echo "✅ Role $role already assigned"
    fi
done

# Remove any existing keys to clean up
echo "🧹 Cleaning up old service account keys..."
EXISTING_KEYS=$(gcloud iam service-accounts keys list \
    --iam-account=$SA_EMAIL \
    --format="value(name)" \
    --filter="keyType:USER_MANAGED")

if [ ! -z "$EXISTING_KEYS" ]; then
    echo "Found existing keys, removing them..."
    echo "$EXISTING_KEYS" | while read -r key; do
        if [ ! -z "$key" ]; then
            echo "Removing key: $key"
            gcloud iam service-accounts keys delete "$key" \
                --iam-account=$SA_EMAIL \
                --quiet
        fi
    done
fi

# Generate new key
echo "🔑 Generating new service account key..."
gcloud iam service-accounts keys create $KEY_FILE \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT_ID

echo ""
echo "✅ Service account key generated successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Copy the content below (including the curly braces)"
echo "2. Go to GitHub repository Settings → Secrets and variables → Actions"
echo "3. Update the GCP_SA_KEY secret with this content"
echo ""
echo "🔐 Service Account Key Content:"
echo "=================================================================================="
cat $KEY_FILE
echo ""
echo "=================================================================================="
echo ""

# Clean up the key file
echo "🧹 Removing local key file for security..."
rm $KEY_FILE

echo "✅ Setup complete! Update your GitHub secret and try deploying again."
echo ""
echo "💡 Security tip: Consider migrating to Workload Identity Federation for better security."
echo "   See scripts/fix-gcp-auth.md for instructions."
