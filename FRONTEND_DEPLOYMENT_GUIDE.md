# Frontend Deployment to Google Cloud Storage

This document outlines the new deployment strategy where:
- **Backend**: Deployed manually to Render.com
- **Frontend**: Automatically deployed to Google Cloud Storage via GitHub Actions

## Overview

The frontend is automatically deployed to Google Cloud Storage when changes are pushed to the `main` branch under the `frontend/` directory. The deployment includes:

1. Building the React/Vite application
2. Uploading to Google Cloud Storage bucket
3. Setting up Cloud CDN for global distribution
4. Configuring SSL certificate for HTTPS
5. Cache invalidation for immediate updates

## Required GitHub Secrets

You need to set up the following secrets in your GitHub repository:

### 1. GCP_SA_KEY
Your Google Cloud Platform service account key (JSON format).

### 2. RENDER_BACKEND_URL
The URL of your backend deployed on Render.com (e.g., `https://your-app-name.onrender.com`)

### 3. GOOGLE_CLIENT_ID
Your Google OAuth client ID for authentication.

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact names listed above

## Deployment Process

### Automatic Deployment
- Triggers on pushes to `main` branch with changes in `frontend/` directory
- Can also be triggered manually via GitHub Actions

### Manual Deployment
1. Go to GitHub Actions in your repository
2. Select "Deploy Frontend to Google Cloud Storage"
3. Click "Run workflow"
4. Select the branch and run

## Backend Configuration for Render.com

Since your backend is now on Render.com, make sure to:

### 1. Update CORS Settings
Add your frontend domain to the allowed origins in your Django settings:

```python
CORS_ALLOWED_ORIGINS = [
    "https://bunklogs.net",
    "https://storage.googleapis.com/bunk-logs-frontend-prod",
    # ... other origins
]
```

### 2. Update CSRF Trusted Origins
```python
CSRF_TRUSTED_ORIGINS = [
    'https://bunklogs.net',
    'https://storage.googleapis.com/bunk-logs-frontend-prod',
    # ... other origins
]
```

### 3. Set Environment Variables on Render.com
Make sure these environment variables are set in your Render.com service:
- `FRONTEND_URL=https://bunklogs.net`
- `DJANGO_ALLOWED_HOSTS=your-render-app.onrender.com,bunklogs.net`

## Domain Configuration

Your frontend will be available at:
- **Direct Storage URL**: `https://storage.googleapis.com/bunk-logs-frontend-prod/index.html`
- **CDN URL**: `https://bunklogs.net` (requires DNS configuration)

### DNS Setup
1. Get the Load Balancer IP from the GitHub Actions deployment logs
2. Create an A record for `bunklogs.net` pointing to that IP
3. Wait for DNS propagation (usually 5-15 minutes)

## Monitoring and Troubleshooting

### Checking Deployment Status
- View GitHub Actions logs for detailed deployment information
- Check the "Actions" tab in your GitHub repository

### Common Issues

1. **Build Failures**: Check the frontend build logs in GitHub Actions
2. **Permission Issues**: Verify your GCP service account has the necessary permissions
3. **CORS Errors**: Ensure your backend allows requests from the frontend domain
4. **CDN Cache**: Use the cache invalidation step or wait for cache TTL

### Useful Commands

Check bucket contents:
```bash
gsutil ls gs://bunk-logs-frontend-prod/
```

Manual cache invalidation:
```bash
gcloud compute url-maps invalidate-cdn-cache bunk-logs-frontend-map --path="/*" --global
```

## File Structure

```
.github/
└── workflows/
    ├── deploy-frontend.yml                 # Active frontend deployment
    ├── deploy-backend-old.yml.disabled     # Disabled backend deployment
    └── deploy-production-old.yml.disabled  # Disabled full deployment
```

## Next Steps

1. **Set up the required GitHub secrets** (listed above)
2. **Update your Render.com backend** with the correct CORS and domain settings
3. **Configure DNS** to point bunklogs.net to the Load Balancer IP
4. **Test the deployment** by making a change to the frontend and pushing to main
5. **Verify functionality** by testing the frontend with your Render.com backend

## Benefits of This Setup

- **Faster deployments**: Frontend deploys independently of backend
- **Global CDN**: Fast loading times worldwide via Google Cloud CDN
- **Cost-effective**: Pay-per-use for storage and CDN
- **Automatic SSL**: Managed SSL certificates
- **Easy rollbacks**: Previous versions are preserved in the bucket
