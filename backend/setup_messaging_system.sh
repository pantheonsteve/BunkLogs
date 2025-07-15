#!/bin/bash

# BunkLogs Messaging System - Quick Setup Script
# This script helps you get the messaging system up and running

echo "🎯 BunkLogs Messaging System Setup"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the Django project root directory"
    exit 1
fi

# Set up environment
echo "📋 Setting up environment..."
export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || echo "⚠️  No .env file found, using defaults"

# Run migrations
echo "📊 Running messaging migrations..."
python manage.py migrate messaging

# Setup initial data
echo "📧 Setting up initial messaging data..."
python manage.py setup_messaging

# Test the system
echo "🧪 Testing the system..."
echo ""
echo "1. Testing daily report generation..."
python manage.py preview_daily_report

echo ""
echo "2. Testing email service..."
python manage.py test_email_service --to test@example.com

echo ""
echo "3. Testing dry-run of daily reports..."
python manage.py send_daily_reports --dry-run

echo ""
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Configure Mailgun settings for production"
echo "2. Set up recipient email addresses in Django admin"
echo "3. Deploy to Render.com with the provided render.yaml"
echo ""
echo "Commands to try:"
echo "  python manage.py preview_daily_report --open-browser"
echo "  python manage.py send_daily_reports --dry-run"
echo "  python manage.py test_email_service --to your@email.com"
