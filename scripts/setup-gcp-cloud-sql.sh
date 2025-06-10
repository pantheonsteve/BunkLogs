#!/bin/bash
# scripts/setup-cheap-cloud-sql.sh
# Corrected Cloud SQL setup for $9/month instead of $50/month

set -e

PROJECT_ID="bunklogsauth"
REGION="us-central1"
INSTANCE_NAME="bunk-logs-clc"
DB_PASSWORD=$(openssl rand -base64 32)

echo "🔧 Setting up Cloud SQL PostgreSQL (Enterprise Edition) - ~$9/month"
echo "⚠️  NOTE: Using Enterprise Edition (not Enterprise Plus) for cheaper pricing"

# Enable Cloud SQL API
gcloud services enable sqladmin.googleapis.com

# Create Cloud SQL instance with Enterprise edition (not Enterprise Plus!)
echo "📦 Creating Cloud SQL instance (Enterprise edition)..."
gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --edition=ENTERPRISE \
    --region=$REGION \
    --storage-size=10GB \
    --storage-type=SSD \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --deletion-protection

echo "✅ Instance created successfully!"

# Create database and user
echo "👤 Creating database and user..."
gcloud sql databases create bunk_logs --instance=$INSTANCE_NAME

gcloud sql users create bunk_logs_user \
    --instance=$INSTANCE_NAME \
    --password=$DB_PASSWORD

# Get connection info
CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)")
PUBLIC_IP=$(gcloud sql instances describe $INSTANCE_NAME --format="value(ipAddresses[0].ipAddress)")

echo "✅ Setup complete!"
echo ""
echo "📋 Connection Details:"
echo "   Instance: $INSTANCE_NAME"
echo "   Connection Name: $CONNECTION_NAME"
echo "   Public IP: $PUBLIC_IP"
echo "   Database: bunk_logs"
echo "   User: bunk_logs_user"
echo "   Password: $DB_PASSWORD"
echo ""
echo "💰 Expected Monthly Cost: ~$9-12 (Enterprise edition)"
echo ""
echo "🔗 For Cloud Run, use this connection string:"
echo "   DATABASE_URL=postgresql://bunk_logs_user:$DB_PASSWORD@//bunk_logs?host=/cloudsql/$CONNECTION_NAME"
echo ""
echo "⚡ For external connections:"
echo "   DATABASE_URL=postgresql://bunk_logs_user:$DB_PASSWORD@$PUBLIC_IP:5432/bunk_logs"

# Store secrets for deployment
echo "🔐 Storing connection string in Secret Manager..."
echo -n "postgresql://bunk_logs_user:$DB_PASSWORD@//bunk_logs?host=/cloudsql/$CONNECTION_NAME" | \
    gcloud secrets create DATABASE_URL --data-file=- --replication-policy=automatic

echo "✅ Secret stored as 'DATABASE_URL'"