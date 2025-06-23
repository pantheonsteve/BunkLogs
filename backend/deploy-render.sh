#!/bin/bash
# Deploy to Render.com
# This script helps with manual deployments if needed

set -e

echo "🚀 Deploying BunkLogs to Render.com..."

# Check if we have the Render CLI
if ! command -v render &> /dev/null; then
    echo "⚠️  Render CLI not found. Installing..."
    npm install -g @render-com/cli
fi

# Deploy using render.yaml
echo "📦 Deploying services..."
render deploy

echo "✅ Deployment complete!"
echo "🔗 Check your deployment status at: https://dashboard.render.com/"
echo ""
echo "💡 Tips for bulk operations:"
echo "   - The timeout is set to 10 minutes for bulk imports"
echo "   - Use single worker (WEB_CONCURRENCY=1) for memory efficiency"
echo "   - Monitor memory usage during large imports"
echo ""
echo "🔧 If imports still timeout, consider:"
echo "   - Reducing batch size in admin interface"
echo "   - Using the management command: python manage.py import_users <csv_file>"
echo "   - Upgrading to a higher Render.com plan for more resources"
