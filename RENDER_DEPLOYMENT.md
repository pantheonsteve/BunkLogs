# Render.com Deployment Guide

## Overview
BunkLogs is now optimized for deployment on Render.com with special configurations for handling bulk user imports without timeout issues.

## Key Optimizations

### 1. Gunicorn Configuration
- **Timeout**: 10 minutes (600 seconds) for long-running bulk operations
- **Workers**: Single worker (`WEB_CONCURRENCY=1`) for memory efficiency during bulk ops
- **Graceful Timeout**: 2 minutes to allow proper cleanup

### 2. Bulk Import Optimizations
- **Batch Processing**: Users are imported in configurable batches (default: 25)
- **Fast Password Hashing**: Optional PBKDF2 instead of Argon2 for bulk operations
- **Memory Management**: Delays between batches prevent memory exhaustion
- **Transaction Safety**: Each batch is processed in its own database transaction

## Deployment

### Automatic Deployment
1. Push to your main branch
2. Render.com will automatically build and deploy using `render.yaml`

### Manual Deployment
```bash
# Using the deployment script
./deploy-render.sh

# Or using Render CLI directly
render deploy
```

## Environment Variables
Set these in your Render.com dashboard:

### Required
- `DJANGO_SECRET_KEY`: Your Django secret key
- `DATABASE_URL`: Provided by Render.com PostgreSQL
- `DJANGO_SETTINGS_MODULE`: `config.settings.production`

### Optional (with defaults)
- `WEB_CONCURRENCY`: `1` (recommended for bulk operations)
- `TIMEOUT`: `600` (10 minutes)

## Bulk User Import

### Via Django Admin
1. Navigate to `/admin/users/user/`
2. Click "Import Users from CSV"
3. Configure batch size (start with 25 for large files)
4. Enable "Use fast password hashing" for better performance
5. Test with "Dry run" first

### Via Management Command
For very large files (1000+ users), use the command line:

```bash
# Dry run first
python manage.py import_users users.csv --dry-run --batch-size=25

# Actual import
python manage.py import_users users.csv --batch-size=25 --fast-hashing
```

## Troubleshooting

### Import Timeouts
If imports still timeout:
1. **Reduce batch size**: Try 10 or 15 instead of 25
2. **Use command line**: Direct SSH to Render.com and run management command
3. **Upgrade plan**: Higher Render.com plans have more resources
4. **Split files**: Break large CSV files into smaller chunks

### Memory Issues
- Ensure `WEB_CONCURRENCY=1` for bulk operations
- Use smaller batch sizes
- Monitor usage in Render.com dashboard

### Database Connection Issues
- Check `DATABASE_URL` environment variable
- Verify PostgreSQL instance is running
- Check connection limits on your database plan

## CSV Format
```csv
email,first_name,last_name,role,password,is_active,is_staff
john@example.com,John,Doe,Counselor,,true,false
jane@example.com,Jane,Smith,Unit Head,custom_password,true,true
```

### Required Fields
- `email`: Unique email address
- `first_name`: User's first name
- `last_name`: User's last name

### Optional Fields
- `role`: Admin, Camper Care, Unit Head, Counselor (default: Counselor)
- `password`: Custom password (random generated if empty)
- `is_active`: true/false (default: true)
- `is_staff`: true/false (default: false)

## Health Check
The application includes a health check endpoint at `/health/` that Render.com uses to monitor service health.

## Performance Tips
1. **Schedule large imports**: Run during off-peak hours
2. **Monitor resources**: Use Render.com metrics dashboard
3. **Progressive imports**: Start small and increase batch size
4. **Use dry runs**: Always test with dry run first

## Support
For deployment issues, check:
1. Render.com build logs
2. Application logs in Render.com dashboard
3. Health check endpoint: `https://your-app.onrender.com/health/`
