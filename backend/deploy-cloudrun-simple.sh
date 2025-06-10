#!/bin/bash
# Simplified deployment script for Google Cloud Run

set -e

# Configuration
PROJECT_ID="bunklogsauth"
REGION="us-central1" 
REGISTRY="us-central1-docker.pkg.dev"
SERVICE_NAME="bunk-logs-backend"
IMAGE_NAME="$REGISTRY/$PROJECT_ID/bunk-logs/django"
CLOUD_SQL_INSTANCE="$PROJECT_ID:$REGION:bunk-logs"

echo "🚀 Starting deployment to Google Cloud Run..."

# Authenticate and set project
echo "🔐 Setting up authentication..."
gcloud config set project $PROJECT_ID
gcloud auth configure-docker $REGISTRY

# Build image using Cloud Build
echo "📦 Building image with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_NAME:latest \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --add-cloudsql-instances=$CLOUD_SQL_INSTANCE \
  --set-env-vars="DEBUG=False,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_CLOUD_SQL_AUTH_PROXY=True,DJANGO_SETTINGS_MODULE=config.settings.cloudrun,DATABASE_URL=postgresql://stevebresnick:April221979!@bunk-logs-clc?host=/cloudsql/bunklogsauth:us-central1:bunk-logs,DJANGO_SECRET_KEY=\$#u&&du@pa3k)bn-)7s&hvr=i#a*qs9t=@g!%y5huhw)g9&yi!,POSTGRES_USER=stevebresnick,POSTGRES_PASSWORD=April221979!,POSTGRES_HOST=/cloudsql/bunklogsauth:us-central1:bunk-logs,POSTGRES_PORT=5432,POSTGRES_DB=bunk-logs-clc,AWS_ACCESS_KEY_ID=dummy,AWS_SECRET_ACCESS_KEY=dummy,AWS_STORAGE_BUCKET_NAME=dummy-bucket,MAILGUN_API_KEY=dummy,MAILGUN_SENDER_DOMAIN=dummy.mailgun.org" \
  --max-instances=10 \
  --min-instances=0 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=900 \
  --port=8080

# Get the service URL
echo "✅ Deployment completed!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo "🌐 Service URL: $SERVICE_URL"

echo "📋 Next steps:"
echo "1. Test the application at: $SERVICE_URL"
echo "2. Check logs: gcloud logs read --service=$SERVICE_NAME"
echo "3. Run migrations manually if needed"
echo "4. Update your frontend to use the new backend URL"
