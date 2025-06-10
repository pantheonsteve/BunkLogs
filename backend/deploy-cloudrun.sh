#!/bin/bash
# Enhanced deployment script for Google Cloud Run

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

# Build image using Cloud Build (more reliable than local build)
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
  --set-env-vars=DEBUG=False,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_CLOUD_SQL_AUTH_PROXY=True,GS_BUCKET_NAME=bunk-logs-static,DJANGO_SETTINGS_MODULE=config.settings.production,POSTGRES_USER=stevebresnick,POSTGRES_HOST=/cloudsql/bunklogsauth:us-central1:bunk-logs,POSTGRES_PORT=5432,POSTGRES_DB=bunk-logs-clc \
  --set-env-vars="DATABASE_URL=postgresql://stevebresnick:April221979!@bunk-logs-clc?host=/cloudsql/bunklogsauth:us-central1:bunk-logs" \
  --set-env-vars="SECRET_KEY=\$#u&&du@pa3k)bn-)7s&hvr=i#a*qs9t=@g!%y5huhw)g9&yi!" \
  --set-env-vars="POSTGRES_PASSWORD=April221979!" \
  --set-env-vars="ALLOWED_HOSTS=bunklogs.net,bunklogs.run.app,localhost:5173" \
  --max-instances=10 \
  --min-instances=0 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=900 \
  --port=8080 \
  --no-traffic

# Create and run migration job
echo "🔄 Running database migrations..."
gcloud run jobs replace --region=$REGION << EOF
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: migrate-job
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    spec:
      template:
        metadata:
          annotations:
            run.googleapis.com/cloudsql-instances: $CLOUD_SQL_INSTANCE
        spec:
          containers:
          - image: $IMAGE_NAME:latest
            command: ["python"]
            args: ["manage.py", "migrate"]
            env:
            - name: DEBUG
              value: "False"
            - name: GOOGLE_CLOUD_PROJECT
              value: "$PROJECT_ID"
            - name: USE_CLOUD_SQL_AUTH_PROXY
              value: "True"
            - name: DJANGO_SETTINGS_MODULE
              value: "config.settings.production"
            - name: DATABASE_URL
              value: "postgresql://stevebresnick:April221979!@bunk-logs-clc?host=/cloudsql/bunklogsauth:us-central1:bunk-logs"
            - name: SECRET_KEY
              value: "$#u&&du@pa3k)bn-)7s&hvr=i#a*qs9t=@g!%y5huhw)g9&yi!"
            - name: ALLOWED_HOSTS
              value: "bunklogs.net,*.bunklogs.net,localhost:5173,*.run.app,bunklogs.run.app"
            - name: POSTGRES_USER
              value: "stevebresnick"
            - name: POSTGRES_PASSWORD
              value: "April221979!"
            - name: POSTGRES_HOST
              value: "/cloudsql/bunklogsauth:us-central1:bunk-logs"
            - name: POSTGRES_PORT
              value: "5432"
            - name: POSTGRES_DB
              value: "bunk-logs-clc"
            resources:
              limits:
                cpu: 1000m
                memory: 1Gi
          restartPolicy: Never
      backoffLimit: 3
EOF

# Execute migration job
gcloud run jobs execute migrate-job --region=$REGION --wait

# Collect static files job
echo "📁 Collecting static files..."
gcloud run jobs replace --region=$REGION << EOF
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: collectstatic-job
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    spec:
      template:
        metadata:
          annotations:
            run.googleapis.com/cloudsql-instances: $CLOUD_SQL_INSTANCE
        spec:
          containers:
          - image: $IMAGE_NAME:latest
            command: ["python"]
            args: ["manage.py", "collectstatic", "--noinput"]
            env:
            - name: DEBUG
              value: "False"
            - name: GOOGLE_CLOUD_PROJECT
              value: "$PROJECT_ID"
            - name: USE_CLOUD_SQL_AUTH_PROXY
              value: "True"
            - name: GS_BUCKET_NAME
              value: "bunk-logs-static"
            - name: DJANGO_SETTINGS_MODULE
              value: "config.settings.production"
            - name: DATABASE_URL
              value: "postgresql://stevebresnick:April221979!@bunk-logs-clc?host=/cloudsql/bunklogsauth:us-central1:bunk-logs"
            - name: SECRET_KEY
              value: "$#u&&du@pa3k)bn-)7s&hvr=i#a*qs9t=@g!%y5huhw)g9&yi!"
            - name: ALLOWED_HOSTS
              value: "bunklogs.net,*.bunklogs.net,localhost:5173,*.run.app,bunklogs.run.app"
            - name: POSTGRES_USER
              value: "stevebresnick"
            - name: POSTGRES_PASSWORD
              value: "April221979!"
            - name: POSTGRES_HOST
              value: "/cloudsql/bunklogsauth:us-central1:bunk-logs"
            - name: POSTGRES_PORT
              value: "5432"
            - name: POSTGRES_DB
              value: "bunk-logs-clc"
            resources:
              limits:
                cpu: 1000m
                memory: 1Gi
          restartPolicy: Never
      backoffLimit: 3
EOF

gcloud run jobs execute collectstatic-job --region=$REGION --wait

# Shift traffic to new revision
echo "🔀 Shifting traffic to new revision..."
gcloud run services update-traffic $SERVICE_NAME \
  --to-latest \
  --region=$REGION

# Get the service URL
echo "✅ Deployment completed!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo "🌐 Service URL: $SERVICE_URL"

echo "📋 Next steps:"
echo "1. Test the application at: $SERVICE_URL"
echo "2. Check logs: gcloud logs read --service=$SERVICE_NAME"
echo "3. Update your frontend to use the new backend URL"
