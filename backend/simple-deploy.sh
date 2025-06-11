#!/bin/bash
# Simple Django deployment - NO DATADOG

set -e

PROJECT_ID="bunklogsauth"
REGION="us-central1"
SERVICE_NAME="bunk-logs-backend"
IMAGE_NAME="us-central1-docker.pkg.dev/$PROJECT_ID/bunk-logs/django:latest"

echo "🚀 Deploying Django app only..."

# Build the image
gcloud builds submit --config cloudbuild.yaml .

# Create env file to avoid shell escaping issues
cat > env.yaml << EOF
PORT: "8080"
DEBUG: "False"
GOOGLE_CLOUD_PROJECT: "$PROJECT_ID"
USE_CLOUD_SQL_AUTH_PROXY: "True"
GS_BUCKET_NAME: "bunk-logs-static"
DJANGO_SETTINGS_MODULE: "config.settings.production"
POSTGRES_USER: "stevebresnick"
POSTGRES_HOST: "/cloudsql/bunklogsauth:us-central1:bunk-logs"
POSTGRES_PORT: "5432"
POSTGRES_DB: "bunk-logs-clc"
POSTGRES_PASSWORD: "April221979!"
ALLOWED_HOSTS: "bunklogs.net,bunklogs.run.app,localhost:5173"
SECRET_KEY: "\$#u&&du@pa3k)bn-)7s&hvr=i#a*qs9t=@g!%y5huhw)g9&yi!"
DATABASE_URL: "postgresql://stevebresnick:April221979%21@bunk-logs-clc?host=/cloudsql/bunklogsauth:us-central1:bunk-logs"
EOF

# Deploy Django service
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_NAME \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --add-cloudsql-instances=bunklogsauth:us-central1:bunk-logs \
  --port=8080 \
  --execution-environment=gen2 \
  --env-vars-file=env.yaml \
  --max-instances=10 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=900

rm env.yaml
echo "✅ Django deployment complete!"