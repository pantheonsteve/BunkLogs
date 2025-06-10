#!/bin/bash
# Setup Google Cloud Secret Manager for sensitive data

PROJECT_ID="bunklogsauth"

echo "🔐 Setting up Secret Manager..."

# Create secrets
echo "Creating secrets..."
echo -n '$#u&&du@pa3k)bn-)7s&hvr=i#a*qs9t=@g!%y5huhw)g9&yi!' | gcloud secrets create django-secret-key --data-file=-
echo -n 'April221979!' | gcloud secrets create database-password --data-file=-
echo -n '$am0$3tLane' | gcloud secrets create email-password --data-file=-

# Grant Cloud Run service account access to secrets
SERVICE_ACCOUNT="$PROJECT_ID@appspot.gserviceaccount.com"

gcloud secrets add-iam-policy-binding django-secret-key \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding database-password \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding email-password \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

echo "✅ Secrets created successfully!"
echo "Now update your Django settings to use Secret Manager."
