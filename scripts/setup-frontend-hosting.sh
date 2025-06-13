#!/bin/bash
# Setup proper website hosting for Google Cloud Storage frontend

set -e

PROJECT_ID="bunklogsauth"
BUCKET_NAME="bunk-logs-frontend-prod"
DOMAIN="bunklogs.net"

echo "🌐 Setting up proper website hosting for $DOMAIN..."

# 1. Ensure bucket has website configuration
echo "📁 Configuring bucket for website hosting..."
gsutil web set -m index.html -e index.html gs://$BUCKET_NAME

# 2. Create backend bucket for load balancer
echo "🔗 Creating backend bucket..."
gcloud compute backend-buckets create frontend-backend-bucket \
    --gcs-bucket-name=$BUCKET_NAME || echo "Backend bucket already exists"

# 3. Create URL map
echo "🗺️ Creating URL map..."
gcloud compute url-maps create frontend-url-map \
    --default-backend-bucket=frontend-backend-bucket || echo "URL map already exists"

# 4. Create SSL certificate
echo "🔒 Creating managed SSL certificate..."
gcloud compute ssl-certificates create frontend-ssl-cert \
    --domains=$DOMAIN || echo "SSL certificate already exists"

# 5. Create HTTPS proxy
echo "🛡️ Creating HTTPS proxy..."
gcloud compute target-https-proxies create frontend-https-proxy \
    --url-map=frontend-url-map \
    --ssl-certificates=frontend-ssl-cert || echo "HTTPS proxy already exists"

# 6. Create forwarding rule (global IP)
echo "📡 Creating forwarding rule..."
gcloud compute forwarding-rules create frontend-forwarding-rule \
    --global \
    --target-https-proxy=frontend-https-proxy \
    --ports=443 || echo "Forwarding rule already exists"

# 7. Get the external IP
echo "🌍 Getting external IP address..."
EXTERNAL_IP=$(gcloud compute forwarding-rules describe frontend-forwarding-rule --global --format="get(IPAddress)")

echo ""
echo "✅ Frontend hosting setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Point your domain DNS to this IP: $EXTERNAL_IP"
echo "2. Update your DNS A record for $DOMAIN to point to $EXTERNAL_IP"
echo "3. Wait for DNS propagation (may take up to 24 hours)"
echo "4. SSL certificate will be automatically provisioned once DNS is configured"
echo ""
echo "🔍 Current status:"
echo "- Bucket: gs://$BUCKET_NAME"
echo "- External IP: $EXTERNAL_IP"
echo "- Domain: $DOMAIN"
echo "- Direct access: https://storage.googleapis.com/$BUCKET_NAME/index.html"
echo ""
echo "📊 Check certificate status:"
echo "gcloud compute ssl-certificates describe frontend-ssl-cert --global"
