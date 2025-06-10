# 🚀 BunkLogs Backend Development Guide

Complete step-by-step guide for developing the BunkLogs Django backend with automatic deployment to Google Cloud Run.

## 📋 **Quick Start**

```bash
# 1. Set up local development
./setup-local-dev.sh

# 2. Start development server
./dev.sh start

# 3. Open in browser
open http://localhost:8000
```

## 🛠️ **Development Workflow**

### Phase 1: Local Development Setup

1. **Initial Setup**
   ```bash
   # Clone repository (if not already done)
   git clone <your-repo-url>
   cd BunkLogs/backend
   
   # Set up local environment
   ./setup-local-dev.sh
   ```

2. **Daily Development**
   ```bash
   # Start development environment
   ./dev.sh docker-up      # Start PostgreSQL and Redis
   ./dev.sh start          # Start Django server
   
   # Development commands
   ./dev.sh test           # Run tests
   ./dev.sh migrate        # Run migrations
   ./dev.sh shell          # Django shell
   ./dev.sh help           # See all commands
   ```

### Phase 2: GitHub Setup for Auto-Deployment

1. **Push Code to GitHub**
   ```bash
   # Initialize git (if not already done)
   git init
   git add .
   git commit -m "Initial commit"
   
   # Add GitHub remote
   git remote add origin https://github.com/yourusername/bunklogs.git
   git push -u origin main
   ```

2. **Set Up GitHub Secrets**
   
   Go to your GitHub repository → Settings → Secrets and variables → Actions
   
   Add these secrets:
   
   - **`GCP_SA_KEY`**: Contents of `github-actions-key.json` file
   - **`DJANGO_SECRET_KEY`**: A strong secret key for production
   - **`POSTGRES_PASSWORD`**: `April221979` (your current DB password)

   ```bash
   # To get the service account key content:
   cat github-actions-key.json
   
   # Generate a strong Django secret key:
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

### Phase 3: Development Process

1. **Feature Development**
   ```bash
   # Create feature branch
   git checkout -b feature/new-feature
   
   # Make changes
   # ... develop your feature ...
   
   # Test locally
   ./dev.sh test
   ./dev.sh lint
   
   # Commit and push
   git add .
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```

2. **Testing and Deployment**
   ```bash
   # Create pull request on GitHub
   # - This triggers CI tests
   # - Review and merge when ready
   
   # Deploy to production
   git checkout main
   git pull origin main
   # Push to main triggers automatic deployment
   ```

## 🏗️ **Project Structure**

```
backend/
├── .env.local              # Local environment template
├── .env                    # Your local environment (auto-created)
├── setup-local-dev.sh      # Local setup script
├── dev.sh                  # Development helper commands
├── github-actions-key.json # Service account key (don't commit!)
├── bunk_logs/              # Main Django app
├── config/                 # Django settings
├── requirements/           # Python dependencies
└── compose/                # Docker configurations
```

## 🔧 **Available Commands**

The `./dev.sh` script provides these commands:

| Command | Description |
|---------|-------------|
| `setup` | Set up local development environment |
| `start` | Start Django development server |
| `test` | Run tests |
| `test-coverage` | Run tests with coverage report |
| `migrate` | Run database migrations |
| `makemigrations` | Create new migrations |
| `shell` | Open Django shell |
| `superuser` | Create superuser |
| `collectstatic` | Collect static files |
| `docker-up` | Start Docker services (PostgreSQL, Redis) |
| `docker-down` | Stop Docker services |
| `docker-reset` | Reset Docker services and volumes |
| `lint` | Run code linting |
| `format` | Format code with black |
| `clean` | Clean cache and temp files |
| `backup-db` | Backup local database |
| `restore-db` | Restore local database |

## 🚀 **Deployment Pipeline**

### Automatic Deployment Flow

1. **Code Push** → GitHub repository
2. **CI/CD Trigger** → GitHub Actions workflow starts
3. **Testing** → Run tests with PostgreSQL and Redis
4. **Build** → Create Docker image
5. **Deploy** → Push to Google Cloud Run
6. **Migrate** → Run database migrations
7. **Live** → Application available at production URL

### Manual Deployment (if needed)

```bash
# Build and deploy manually
gcloud builds submit --config cloudbuild.yaml .

# Deploy to Cloud Run
./deploy-cloudrun-simple.sh
```

## 🌍 **Environment URLs**

- **Local Development**: http://localhost:8000
- **Local Admin**: http://localhost:8000/admin/
- **Local API Docs**: http://localhost:8000/api/docs/

- **Production**: https://bunk-logs-backend-461994890254.us-central1.run.app
- **Production Admin**: https://bunk-logs-backend-461994890254.us-central1.run.app/admin/
- **Production API Docs**: https://bunk-logs-backend-461994890254.us-central1.run.app/api/docs/

## 👤 **Admin Credentials**

### Local Development
- Username: `admin`
- Password: `admin123`

### Production
- Username: `admin`
- Email: `steve@binklogs.com`
- Password: `admin123456`

## 🔒 **Security Notes**

1. **Never commit sensitive files**:
   ```bash
   # Add to .gitignore
   echo "github-actions-key.json" >> .gitignore
   echo ".env" >> .gitignore
   ```

2. **Rotate secrets regularly**:
   - Change Django secret key in production
   - Rotate service account keys
   - Update database passwords

3. **Use environment-specific settings**:
   - Local: `config.settings.local`
   - Production: `config.settings.cloudrun`

## 🐛 **Troubleshooting**

### Common Issues

1. **Docker services not starting**:
   ```bash
   ./dev.sh docker-reset
   ```

2. **Migration errors**:
   ```bash
   ./dev.sh docker-reset
   ./dev.sh migrate
   ```

3. **GitHub Actions failing**:
   - Check secrets are set correctly
   - Verify service account permissions
   - Check logs in GitHub Actions tab

4. **Static files not loading**:
   ```bash
   ./dev.sh collectstatic
   ```

### Logs and Debugging

```bash
# Local development logs
./dev.sh logs

# Production logs
gcloud run services logs read bunk-logs-backend --region=us-central1

# Docker service logs
docker compose -f docker-compose.local.yml logs
```

## 📚 **Next Steps**

1. **Set up local development** using the setup script
2. **Configure GitHub secrets** for automatic deployment
3. **Create your first feature branch** and start developing
4. **Push to GitHub** and watch automatic deployment work
5. **Access your live application** at the production URL

## 🤝 **Contributing**

1. Create feature branch from `main`
2. Make changes and test locally
3. Create pull request
4. Merge to `main` for automatic deployment

---

**Happy coding! 🎉**
