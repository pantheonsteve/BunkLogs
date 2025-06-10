#!/bin/bash
# scripts/deploy.sh

set -e

PROJECT_ID="bunklogsauth"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev"

echo "🚀 Starting deployment..."

# Build and push backend
echo "📦 Building Django backend..."
podman build -t $REGISTRY/$PROJECT_ID/bunk-logs/django:latest \
  -f compose/production/django/Dockerfile .

podman push $REGISTRY/$PROJECT_ID/bunk-logs/django:latest

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy bunk-logs-backend \
  --image=$REGISTRY/$PROJECT_ID/bunk-logs/django:latest \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:bunk-logs \
  --env-vars-file=.envs/.production/.django \
  --max-instances=10 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=900 \
  --no-traffic

# Run migrations
echo "🔄 Running migrations..."
gcloud run jobs create migrate-job \
  --image=$REGISTRY/$PROJECT_ID/bunk-logs/django:latest \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:bunk-logs \
  --env-vars-file=.envs/.production/.django \
  --args="python,manage.py,migrate" \
  --replace

gcloud run jobs execute migrate-job --region=$REGION --wait

# Shift traffic to new revision
echo "🔀 Shifting traffic..."
gcloud run services update-traffic bunk-logs-backend \
  --to-latest \
  --region=$REGION

echo "✅ Backend deployment complete!"

# Build and deploy frontend
echo "📦 Building React frontend..."
cd frontend
npm run build

# Deploy to Cloud Storage + CDN (or Cloud Run)
gsutil -m rsync -r -d dist/ gs://bunk-log-static/

echo "✅ Frontend deployment complete!"
echo "🎉 Deployment finished successfully!"