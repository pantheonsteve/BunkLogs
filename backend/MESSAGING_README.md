# BunkLogs Email Messaging Service

A professional email workflow system that automatically generates and sends daily order reports to camp staff.

## 🚀 Quick Start

### 1. Preview the Email Template (Local Testing)
```bash
# Set up environment and preview today's report
export $(cat .env | grep -v '^#' | xargs) && python manage.py preview_daily_report --open-browser

# Preview a specific date
export $(cat .env | grep -v '^#' | xargs) && python manage.py preview_daily_report --date 2025-07-14 --open-browser

# Just generate without opening browser
export $(cat .env | grep -v '^#' | xargs) && python manage.py preview_daily_report
```

### 2. Test Email Sending (Development Mode)
```bash
# Test the email service (logs to console in development)
export $(cat .env | grep -v '^#' | xargs) && python manage.py test_email_service --to your@email.com

# Test the full daily report workflow (dry run)
export $(cat .env | grep -v '^#' | xargs) && python manage.py send_daily_reports --dry-run

# Send to specific email addresses (dry run)
export $(cat .env | grep -v '^#' | xargs) && python manage.py send_daily_reports --recipients manager@camp.com maintenance@camp.com --dry-run
```

### 3. Setup Initial Data (Run Once)
```bash
export $(cat .env | grep -v '^#' | xargs) && python manage.py setup_messaging
```

## 📧 Production Deployment

### 1. Configure Mailgun
Set these environment variables in Render.com:
```bash
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-domain.com
MAILGUN_FROM_EMAIL=reports@your-domain.com
```

### 2. Configure Recipients
1. Create a superuser: `python manage.py createsuperuser`
2. Visit `/admin/messaging/` in your app
3. Add email recipients to the "daily-reports" group

### 3. Automatic Daily Emails
The `render.yaml` file includes a cron job that runs daily at 8 AM:
```yaml
- type: cron
  name: daily-reports
  startCommand: "python manage.py send_daily_reports"
  schedule: "0 8 * * *"  # Daily at 8 AM
```

## 🛠️ Available Commands

### Core Commands
```bash
# Send daily reports (production)
python manage.py send_daily_reports

# Send reports for specific date
python manage.py send_daily_reports --date 2025-07-14

# Send to specific recipients
python manage.py send_daily_reports --recipients email1@camp.com email2@camp.com

# Dry run (test without sending)
python manage.py send_daily_reports --dry-run
```

### Preview & Testing
```bash
# Preview in browser (local only)
python manage.py preview_daily_report --open-browser

# Preview specific date
python manage.py preview_daily_report --date 2025-07-14

# Test email service
python manage.py test_email_service --to your@email.com

# Setup initial data
python manage.py setup_messaging
```

## 🌐 API Endpoints

### Preview Email (Production)
```bash
# View HTML email in browser
GET https://your-app.onrender.com/api/messaging/preview/daily_report/?format=html

# Get JSON data
GET https://your-app.onrender.com/api/messaging/preview/daily_report/?format=json&date=2025-07-15

# Get text version
GET https://your-app.onrender.com/api/messaging/preview/daily_report/?format=text
```

### Send Test Email
```bash
POST https://your-app.onrender.com/api/messaging/preview/send_test/
{
  "recipients": ["test@example.com"],
  "date": "2025-07-15"
}
```

## 📊 What the Emails Include

The daily reports automatically include:
- **Summary Statistics**: Total orders, maintenance requests, camper care requests
- **Maintenance Requests Table**: Order #, Bunk, Submitted by, Status, Items, Notes
- **Camper Care Requests Table**: Same format as maintenance
- **Professional Styling**: Responsive HTML design with status colors
- **Empty State**: Nice message when no orders exist

## 🎯 Sample Output

```
Daily Orders Report - July 14, 2025 (2 Orders)
================================================================================

SUMMARY
-------
Total Orders: 2
Maintenance Requests: 2
Camper Care Requests: 0
Bunks with Orders: 2

MAINTENANCE REQUESTS
-------------------
Order #75 - Bunk 21 - Session 1 - 2025
Submitted by: Finn Cresswell
Status: Submitted
Items: Lightbulb (1), Shower Curtain (1)

Order #76 - Bunk 23 - Session 1 - 2025
Submitted by: Marton Lorinc
Status: Submitted
Items: Window or Door not opening/closing properly (1), Garbage Bags (1)
```

## 🔧 Troubleshooting

### Local Development Issues
```bash
# If environment variables not working
export DJANGO_SECRET_KEY='dev-secret-key'
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/bunk_logs_local'

# If migration errors
python manage.py makemigrations messaging
python manage.py migrate messaging
```

### Production Issues
```bash
# Check email logs in Django admin
# Visit /admin/messaging/emaillog/

# Test email service
python manage.py test_email_service --to your@email.com

# Check cron job status in Render.com dashboard
# Look for "daily-reports" service logs
```

### No Orders Found
This is normal! The system handles empty days gracefully with a nice "quiet day" message.

## 🚀 Extending the System

### Add New Report Types
1. Create new template in `messaging/templates/email/`
2. Add new method to `EmailTemplateService`
3. Create new management command or extend existing

### Add New Recipients
1. Use Django admin: `/admin/messaging/emailrecipientgroup/`
2. Or use management command with custom recipient groups

### Change Schedule
Modify the cron expression in `render.yaml`:
```yaml
schedule: "0 6 * * *"  # 6 AM daily
schedule: "0 8 * * 1"  # 8 AM Mondays only
schedule: "0 9 * * 1-5"  # 9 AM weekdays
```

---

**The system is now ready to automatically send beautiful daily order reports to your camp staff!** 📧✨
