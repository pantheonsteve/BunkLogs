# Fix Google Cloud Authentication for GitHub Actions

## The Problem
The GitHub Actions deployment is failing with "Invalid JWT Signature" error for the service account `github-actions@bunklogsauth.iam.gserviceaccount.com`. This indicates the `GCP_SA_KEY` secret needs to be regenerated.

## Solution Steps

### 1. Generate New Service Account Key

Run these commands in your terminal (make sure you're authenticated with Google Cloud CLI):

```bash
# Set your project ID
export PROJECT_ID=bunklogsauth

# Set the service account email
export SA_EMAIL=github-actions@bunklogsauth.iam.gserviceaccount.com

# Check if the service account exists
gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID

# Generate a new key for the service account
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=$SA_EMAIL \
  --project=$PROJECT_ID

# Display the key content (you'll copy this to GitHub)
cat github-actions-key.json
```

### 2. Update GitHub Secret

1. Go to your GitHub repository: https://github.com/yourusername/BunkLogs
2. Navigate to Settings → Secrets and variables → Actions
3. Find the `GCP_SA_KEY` secret and click "Update"
4. Copy the entire content of `github-actions-key.json` (including the curly braces)
5. Paste it as the new secret value
6. Save the secret

### 3. Verify Service Account Permissions

Make sure the service account has the necessary permissions:

```bash
# Check current IAM bindings
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:$SA_EMAIL"

# If missing permissions, add them:
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudbuild.builds.builder"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/logging.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/compute.loadBalancerAdmin"
```

### 4. Clean Up

After updating the GitHub secret, remove the local key file:

```bash
rm github-actions-key.json
```

### 5. Test the Fix

1. Push a commit to the main branch to trigger the deployment
2. Check the GitHub Actions workflow to see if authentication works
3. Monitor the deployment logs for any remaining issues

## Security Notes

- The service account key is sensitive - never commit it to version control
- Consider using Workload Identity Federation for better security in the future
- Regularly rotate service account keys (every 90 days recommended)
- Review and minimize the permissions granted to the service account

## Alternative: Workload Identity Federation (Recommended for Production)

For better security, consider migrating to Workload Identity Federation instead of service account keys:

```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-actions" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc "github-actions-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow GitHub repository to impersonate service account
gcloud iam service-accounts add-iam-policy-binding \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository/yourusername/BunkLogs" \
  "$SA_EMAIL"
```

Then update the GitHub workflow to use workload identity instead of service account keys.
