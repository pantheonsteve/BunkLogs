#!/bin/bash
# Enhanced deployment script for Google Cloud Run with Datadog

set -e

# Configuration
PROJECT_ID="bunklogsauth"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev"
SERVICE_NAME="bunk-logs-backend"
IMAGE_NAME="$REGISTRY/$PROJECT_ID/bunk-logs/django"
CLOUD_SQL_INSTANCE="$PROJECT_ID:$REGION:bunk-logs"

echo "🚀 Starting deployment to Google Cloud Run..."

# Create environment variables file
echo "📝 Creating environment variables file..."
cat > env.yaml << EOF
DEBUG: "False"
GOOGLE_CLOUD_PROJECT: "$PROJECT_ID"
USE_CLOUD_SQL_AUTH_PROXY: "True"
GS_BUCKET_NAME: "bunk-logs-static"
DJANGO_SETTINGS_MODULE: "config.settings.production_gcs"
POSTGRES_USER: "stevebresnick"
POSTGRES_HOST: "/cloudsql/bunklogsauth:us-central1:bunk-logs"
POSTGRES_PORT: "5432"
POSTGRES_DB: "bunk-logs-clc"
DJANGO_ALLOWED_HOSTS: "bunklogs.net,bunklogs.run.app,localhost:5173,bunk-logs-backend-koumwfa74a-uc.a.run.app,bunk-logs-backend-461994890254.us-central1.run.app"
DD_SERVICE: "bunk-logs-backend"
DD_ENV: "production"
DD_VERSION: "latest"
DD_LOGS_INJECTION: "false"
DD_DJANGO_USE_HANDLER_RESOURCE_FORMAT: "true"
DD_DJANGO_INSTRUMENT_TEMPLATES: "true"
EOF

# Authenticate and set project
echo "🔐 Setting up authentication..."
gcloud config set project $PROJECT_ID
gcloud auth configure-docker $REGISTRY

# Grant Secret Manager access to Cloud Run service account
echo "🔑 Granting Secret Manager access..."
PROJECT_NUMBER=$(gcloud projects list --filter="project_id:$PROJECT_ID" --format="value(project_number)")
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
echo "Using service account: $SERVICE_ACCOUNT"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# Grant Cloud Storage access to Cloud Run service account for static files
echo "☁️ Granting Cloud Storage access..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"

# Create required secrets if they don't exist
echo "🔐 Creating required secrets..."

# Create DJANGO_SECRET_KEY secret (Django expects this name)
if ! gcloud secrets describe DJANGO_SECRET_KEY --project=$PROJECT_ID &>/dev/null; then
  echo "Creating DJANGO_SECRET_KEY secret..."
  echo "\$#u&&du@pa3k)bn-)7s&hvr=i#a*qs9t=@g!%y5huhw)g9&yi" | gcloud secrets create DJANGO_SECRET_KEY --data-file=- --project=$PROJECT_ID
else
  echo "DJANGO_SECRET_KEY secret already exists"
fi

# Create DATABASE_URL secret
if ! gcloud secrets describe DATABASE_URL --project=$PROJECT_ID &>/dev/null; then
  echo "Creating DATABASE_URL secret..."
  DATABASE_URL="postgres://stevebresnick:\$(gcloud secrets versions access latest --secret=DB_PASSWORD --project=$PROJECT_ID)@/cloudsql/bunklogsauth:us-central1:bunk-logs/bunk-logs-clc"
  echo "$DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=- --project=$PROJECT_ID
else
  echo "DATABASE_URL secret already exists"
fi

# Create DD_API_KEY secret
if ! gcloud secrets describe DD_API_KEY --project=$PROJECT_ID &>/dev/null; then
  echo "Creating DD_API_KEY secret..."
  echo "f326b91021b9866c6d93fadced72b167" | gcloud secrets create DD_API_KEY --data-file=- --project=$PROJECT_ID
else
  echo "DD_API_KEY secret already exists"
fi

# Grant Secret Manager access to Cloud Run service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# Build image using Cloud Build
echo "📦 Building image with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

# Deploy to Cloud Run with proper configuration
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_NAME:latest \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --add-cloudsql-instances=$CLOUD_SQL_INSTANCE \
  --port=8080 \
  --execution-environment=gen2 \
  --env-vars-file=env.yaml \
  --set-secrets="POSTGRES_PASSWORD=DB_PASSWORD:latest,DATABASE_URL=DATABASE_URL:latest,DD_API_KEY=DD_API_KEY:latest,DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest,DJANGO_AWS_ACCESS_KEY_ID=DJANGO_AWS_ACCESS_KEY_ID:latest,DJANGO_AWS_SECRET_ACCESS_KEY=DJANGO_AWS_SECRET_ACCESS_KEY:latest,DJANGO_AWS_STORAGE_BUCKET_NAME=DJANGO_AWS_STORAGE_BUCKET_NAME:latest,DJANGO_ADMIN_URL=DJANGO_ADMIN_URL:latest,MAILGUN_API_KEY=MAILGUN_API_KEY:latest,MAILGUN_DOMAIN=MAILGUN_DOMAIN:latest" \
  --max-instances=10 \
  --min-instances=0 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=900 \
  --no-traffic

# Create and run migration job
echo "🔄 Running database migrations..."
gcloud run jobs create migrate-job \
  --image=$IMAGE_NAME:latest \
  --region=$REGION \
  --task-timeout=900 \
  --max-retries=3 \
  --parallelism=1 \
  --cpu=1 \
  --memory=1Gi \
  --set-cloudsql-instances=$CLOUD_SQL_INSTANCE \
  --set-env-vars=DEBUG=False,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_CLOUD_SQL_AUTH_PROXY=True,DJANGO_SETTINGS_MODULE=config.settings.production_gcs,POSTGRES_USER=stevebresnick,POSTGRES_HOST=/cloudsql/bunklogsauth:us-central1:bunk-logs,POSTGRES_PORT=5432,POSTGRES_DB=bunk-logs-clc,DJANGO_ALLOWED_HOSTS=bunklogs.net \
  --set-secrets=POSTGRES_PASSWORD=DB_PASSWORD:latest,DATABASE_URL=DATABASE_URL:latest,DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest \
  --command=python \
  --args=manage.py,migrate \
  --execute-now \
  --wait || echo "Migration job may already exist, trying to update and execute..."

if [ $? -ne 0 ]; then
  echo "Creating job failed, trying to update existing job..."
  gcloud run jobs update migrate-job \
    --image=$IMAGE_NAME:latest \
    --region=$REGION \
    --task-timeout=900 \
    --max-retries=3 \
    --parallelism=1 \
    --cpu=1 \
    --memory=1Gi \
    --set-cloudsql-instances=$CLOUD_SQL_INSTANCE \
    --set-env-vars=DEBUG=False,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_CLOUD_SQL_AUTH_PROXY=True,DJANGO_SETTINGS_MODULE=config.settings.production_gcs,POSTGRES_USER=stevebresnick,POSTGRES_HOST=/cloudsql/bunklogsauth:us-central1:bunk-logs,POSTGRES_PORT=5432,POSTGRES_DB=bunk-logs-clc,DJANGO_ALLOWED_HOSTS=bunklogs.net \
    --set-secrets=POSTGRES_PASSWORD=DB_PASSWORD:latest,DATABASE_URL=DATABASE_URL:latest,DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest \
    --command=python \
    --args=manage.py,migrate
  
  gcloud run jobs execute migrate-job --region=$REGION --wait
fi

# Collect static files job
echo "📁 Collecting static files..."
gcloud run jobs create collectstatic-job \
  --image=$IMAGE_NAME:latest \
  --region=$REGION \
  --task-timeout=900 \
  --max-retries=3 \
  --parallelism=1 \
  --cpu=1 \
  --memory=1Gi \
  --set-cloudsql-instances=$CLOUD_SQL_INSTANCE \
  --set-env-vars=DEBUG=False,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_CLOUD_SQL_AUTH_PROXY=True,GS_BUCKET_NAME=bunk-logs-static,DJANGO_SETTINGS_MODULE=config.settings.production_gcs,POSTGRES_USER=stevebresnick,POSTGRES_HOST=/cloudsql/bunklogsauth:us-central1:bunk-logs,POSTGRES_PORT=5432,POSTGRES_DB=bunk-logs-clc,DJANGO_ALLOWED_HOSTS=bunklogs.net \
  --set-secrets=POSTGRES_PASSWORD=DB_PASSWORD:latest,DATABASE_URL=DATABASE_URL:latest,DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest \
  --command=python \
  --args=manage.py,collectstatic,--noinput \
  --execute-now \
  --wait || echo "Collectstatic job may already exist, trying to update and execute..."

if [ $? -ne 0 ]; then
  echo "Creating collectstatic job failed, trying to update existing job..."
  gcloud run jobs update collectstatic-job \
    --image=$IMAGE_NAME:latest \
    --region=$REGION \
    --task-timeout=900 \
    --max-retries=3 \
    --parallelism=1 \
    --cpu=1 \
    --memory=1Gi \
    --set-cloudsql-instances=$CLOUD_SQL_INSTANCE \
    --set-env-vars=DEBUG=False,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_CLOUD_SQL_AUTH_PROXY=True,GS_BUCKET_NAME=bunk-logs-static,DJANGO_SETTINGS_MODULE=config.settings.production_gcs,POSTGRES_USER=stevebresnick,POSTGRES_HOST=/cloudsql/bunklogsauth:us-central1:bunk-logs,POSTGRES_PORT=5432,POSTGRES_DB=bunk-logs-clc,DJANGO_ALLOWED_HOSTS=bunklogs.net \
    --set-secrets=POSTGRES_PASSWORD=DB_PASSWORD:latest,DATABASE_URL=DATABASE_URL:latest,DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest \
    --command=python \
    --args=manage.py,collectstatic,--noinput
  
  gcloud run jobs execute collectstatic-job --region=$REGION --wait
fi

# Shift traffic to new revision
echo "🔀 Shifting traffic to new revision..."
gcloud run services update-traffic $SERVICE_NAME \
  --to-latest \
  --region=$REGION

# Get the service URL
echo "✅ Deployment completed!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo "🌐 Service URL: $SERVICE_URL"

# Clean up temporary files
echo "🧹 Cleaning up..."
rm -f env.yaml

echo "📋 Next steps:"
echo "1. Test the application at: $SERVICE_URL"
echo "2. Check logs: gcloud logs read --service=$SERVICE_NAME"
echo "3. Monitor with Datadog: https://app.datadoghq.com/apm/services"
echo "4. Update your frontend to use the new backend URL"

# Test the deployment
echo "🧪 Testing deployment..."
if curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL" | grep -q "200\|302\|301"; then
    echo "✅ Service is responding!"
else
    echo "⚠️  Service may not be responding correctly. Check logs:"
    echo "   gcloud logs read --service=$SERVICE_NAME --limit=50"
fi