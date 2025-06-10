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
   # Start development environment (if not already running)
   ./dev.sh docker-up      # Start PostgreSQL, Redis, and Mailpit
   ./dev.sh start          # Start Django server
   
   # Development commands
   ./dev.sh test           # Run tests
   ./dev.sh migrate        # Run migrations
   ./dev.sh shell          # Django shell
   ./dev.sh help           # See all commands
   ```

3. **Access Development Services**
   - Django: http://localhost:8000
   - Admin: http://localhost:8000/admin/ (admin@bunklogs.com / admin123)
   - API Docs: http://localhost:8000/api/schema/swagger-ui/
   - Email Testing: http://localhost:8025

### Container Requirements

The project uses **Podman** (preferred) or Docker for containerized services:

#### Required Services
- **PostgreSQL 15**: Primary database
- **Redis 7**: Caching and session storage  
- **Mailpit**: Email testing (development only)

#### Container Setup Options

**Option 1: Podman Desktop (Recommended for macOS)**
```bash
# Install Podman Desktop from https://podman-desktop.io/
# The setup script will automatically configure Podman

./setup-local-dev.sh  # Handles Podman setup
```

**Option 2: Docker**
```bash
# If you prefer Docker over Podman
# Edit dev.sh to use 'docker' instead of 'podman'

./dev.sh docker-up
```

**Option 3: Local Services**
```bash
# Install services locally (alternative to containers)
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis

# Update .env file with local connection strings
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
   - **`POSTGRES_PASSWORD`**: Your production database password

   ```bash
   # To get the service account key content:
   cat github-actions-key.json
   
   # Generate a strong Django secret key:
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   **Note**: The current setup uses hardcoded values for development, but you should rotate secrets for production use.

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
├── deploy-cloudrun-fixed.sh # Enhanced Cloud Run deployment script
├── deploy-cloudrun-simple.sh # Simple Cloud Run deployment script
├── test_orders_api.py      # API testing script
├── bunk_logs/              # Main Django app
│   ├── api/                # REST API endpoints and serializers
│   ├── bunks/              # Bunk and cabin management
│   ├── bunklogs/           # Bunk logs functionality
│   ├── campers/            # Camper management
│   ├── orders/             # Order management system
│   ├── users/              # User management and authentication
│   └── contrib/            # Additional utilities
├── config/                 # Django settings and configuration
│   ├── settings/           # Environment-specific settings
│   │   ├── base.py         # Base settings
│   │   ├── local.py        # Local development settings
│   │   ├── production.py   # Production settings
│   │   └── cloudrun.py     # Cloud Run specific settings
│   ├── urls.py             # URL routing
│   └── wsgi.py             # WSGI application
├── compose/                # Docker configurations
│   ├── local/              # Local development containers
│   └── production/         # Production containers
├── requirements/           # Python dependencies
│   ├── base.txt            # Base requirements
│   ├── local.txt           # Local development requirements
│   └── production.txt      # Production requirements
├── docs/                   # Documentation
├── tests/                  # Test files
└── staticfiles/            # Collected static files
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
| `docker-up` | Start Docker/Podman services (PostgreSQL, Redis, Mailpit) |
| `docker-down` | Stop Docker/Podman services |
| `docker-reset` | Reset Docker/Podman services and volumes |
| `lint` | Run code linting with flake8 |
| `format` | Format code with black |
| `requirements` | Update requirements.txt files |
| `clean` | Clean cache and temp files |
| `logs` | Show application logs |
| `backup-db` | Backup local database |
| `restore-db` | Restore local database |
| `help` | Show help message |

### Quick Examples

```bash
# Setup and start development
./dev.sh setup
./dev.sh docker-up
./dev.sh start

# Run tests and check code quality
./dev.sh test
./dev.sh test-coverage
./dev.sh lint

# Database operations
./dev.sh migrate
./dev.sh shell
./dev.sh backup-db

# Reset environment if needed
./dev.sh docker-reset
```

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
# Build and deploy with the enhanced script
./deploy-cloudrun-fixed.sh

# Or use the simple deployment script
./deploy-cloudrun-simple.sh

# Or manually with gcloud
gcloud builds submit --config cloudbuild.yaml .
```

## 🌍 **Environment URLs**

### Local Development
- **Django Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/schema/swagger-ui/
- **API Schema**: http://localhost:8000/api/schema/
- **ReDoc Documentation**: http://localhost:8000/api/schema/redoc/
- **Email Testing (Mailpit)**: http://localhost:8025

### Production
- **Django Application**: https://bunk-logs-backend-koumwfa74a-uc.a.run.app
- **Admin Panel**: https://bunk-logs-backend-koumwfa74a-uc.a.run.app/admin/
- **API Documentation**: https://bunk-logs-backend-koumwfa74a-uc.a.run.app/api/schema/swagger-ui/
- **API Schema**: https://bunk-logs-backend-koumwfa74a-uc.a.run.app/api/schema/
- **ReDoc Documentation**: https://bunk-logs-backend-koumwfa74a-uc.a.run.app/api/schema/redoc/

## 👤 **Admin Credentials**

### Local Development
- **Username**: `**********`
- **Email**: `**********`
- **Password**: `**********`

### Production
- **Username**: `**********`
- **Email**: `**********`
- **Password**: `**********`

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
   - Production: `config.settings.production` 
   - Cloud Run: `config.settings.cloudrun`

4. **Container and dependency management**:
   - Use Podman Desktop or Docker for containers
   - Keep requirements files updated
   - Test with `./dev.sh test` before pushing

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

5. **Container services not accessible**:
   ```bash
   # For Podman users - ensure machine is running
   podman machine start
   
   # Reset all services
   ./dev.sh docker-reset
   ```

6. **API authentication issues**:
   ```bash
   # Test API endpoints
   python test_orders_api.py
   
   # Check if superuser exists
   ./dev.sh shell
   # In shell: from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(is_superuser=True))
   ```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# In .env file, add:
DJANGO_LOG_LEVEL=DEBUG

# Restart Django
./dev.sh start

# View detailed logs
./dev.sh logs
```

### Health Checks

```bash
# Check service status
./dev.sh docker-up  # Should show all services as healthy

# Test database connection
./dev.sh shell
>>> from django.db import connection; connection.ensure_connection()

# Test Redis connection  
./dev.sh shell
>>> from django.core.cache import cache; cache.set('test', 'value'); print(cache.get('test'))

# Test API endpoints
curl http://localhost:8000/api/schema/
```

### Logs and Debugging

```bash
# Local development logs
./dev.sh logs

# Production logs (Cloud Run)
gcloud run services logs read bunk-logs-backend --region=us-central1

# Docker/Podman service logs
podman compose -f docker-compose.local.yml logs
# or
docker compose -f docker-compose.local.yml logs
```

## 📚 **API Documentation**

### Interactive Documentation
- **Local**: http://localhost:8000/api/schema/swagger-ui/
- **Production**: https://bunk-logs-backend-koumwfa74a-uc.a.run.app/api/schema/swagger-ui/

### Available API Endpoints

#### Core Resources
- `/api/users/` - User management
- `/api/bunks/` - Bunk assignments  
- `/api/campers/` - Camper management
- `/api/bunklogs/` - Bunk logs
- `/api/orders/` - Order management system
- `/api/items/` - Item catalog
- `/api/item-categories/` - Item categories
- `/api/order-types/` - Order types

#### Authentication
- `/api/auth/token/` - Get JWT token
- `/api/auth/token/refresh/` - Refresh JWT token
- `/auth/signup/` - User registration
- `/auth/login/` - User login

#### Documentation
- `/api/schema/` - OpenAPI schema
- `/api/schema/swagger-ui/` - Interactive Swagger UI
- `/api/schema/redoc/` - ReDoc documentation

For detailed API documentation, see `API_DOCUMENTATION.md`.

## ⚙️ **Environment Configuration**

### Environment Files

| File | Purpose | Usage |
|------|---------|-------|
| `.env.local` | Template for local development | Copy to `.env` and customize |
| `.env` | Your local environment variables | Auto-created by setup script |
| `.envs/.local/.django` | Docker container environment | Used by docker-compose |
| `.envs/.production/.django` | Production environment | Used for production deployment |

### Key Environment Variables

#### Local Development
```bash
# Database
DATABASE_URL=postgres://postgres:postgres@postgres:5432/bunk_logs
POSTGRES_DB=bunk_logs_local
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Django
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=<your-local-secret-key>
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Redis
REDIS_URL=redis://redis:6379/0

# Email (Mailpit for testing)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mailpit
EMAIL_PORT=1025
```

#### Production
```bash
# Django
DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.cloudrun
DJANGO_SECRET_KEY=<strong-production-secret>
DJANGO_ALLOWED_HOSTS=bunklogs.net,*.run.app

# Database (Cloud SQL)
DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/project:region:instance
USE_CLOUD_SQL_AUTH_PROXY=True

# Static Files
GS_BUCKET_NAME=bunk-logs-static
```

### Updating Environment Variables

```bash
# Edit local environment
nano .env

# View current environment (in Django shell)
./dev.sh shell
>>> import os; print(os.environ.get('DEBUG'))

# Restart services after changes
./dev.sh docker-reset
```

## 🧪 **Testing**

### Running Tests

```bash
# Run all tests
./dev.sh test

# Run tests with coverage
./dev.sh test-coverage

# Run specific test files
python manage.py test bunk_logs.api.tests
python manage.py test bunk_logs.users.tests

# Run API-specific tests
python test_orders_api.py
python test_auth.py
```

### Test Environment
- Tests run against a separate test database
- PostgreSQL and Redis services required (started with `./dev.sh docker-up`)
- Test data is automatically created and cleaned up

### End-to-End Testing

```bash
# Run workflow tests (requires frontend running)
../scripts/test_workflows.sh

# Run e2e tests
../e2e_test.sh
```

## 🚀 **Deployment Options**

### 1. Automatic Deployment (Recommended)
Push to `main` branch triggers automatic deployment via GitHub Actions.

### 2. Enhanced Manual Deployment
```bash
./deploy-cloudrun-fixed.sh
```
Features:
- Database migrations
- Static file collection
- Traffic management
- Comprehensive error handling

### 3. Simple Manual Deployment
```bash
./deploy-cloudrun-simple.sh
```
Basic deployment without advanced features.

### 4. Custom Deployment
```bash
# Build image
gcloud builds submit --config cloudbuild.yaml .

# Deploy with custom settings
gcloud run deploy bunk-logs-backend \
  --image=us-central1-docker.pkg.dev/bunklogsauth/bunk-logs/django:latest \
  --region=us-central1 \
  --allow-unauthenticated
```

## 📱 **Frontend Integration**

### API Base URLs
- **Local**: `http://localhost:8000/api/`
- **Production**: `https://bunk-logs-backend-koumwfa74a-uc.a.run.app/api/`

### Authentication Flow
1. User registers/logs in via frontend
2. Backend returns JWT tokens (access + refresh)
3. Frontend stores tokens and includes in API calls
4. Backend validates tokens for protected endpoints

### CORS Configuration
The backend is configured to accept requests from:
- `localhost:5173` (Vite dev server)
- `localhost:3000` (alternative dev server)
- Production frontend domains

## 📚 **Next Steps**

1. **Set up local development** using the setup script
2. **Configure GitHub secrets** for automatic deployment
3. **Create your first feature branch** and start developing
4. **Test your changes** with the test suite
5. **Push to GitHub** and watch automatic deployment work
6. **Access your live application** at the production URL
7. **Monitor with logging** and error tracking

## 🤝 **Contributing**

### Development Workflow
1. Create feature branch from `main`
2. Make changes and test locally with `./dev.sh test`
3. Run code quality checks: `./dev.sh lint && ./dev.sh format`
4. Create pull request on GitHub
5. Merge to `main` for automatic deployment

### Code Standards
- Follow PEP 8 style guidelines
- Use `./dev.sh format` to format code with Black
- Use `./dev.sh lint` to check code quality with flake8
- Write tests for new features
- Update documentation as needed

### Branch Naming
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical production fixes
- `docs/description` - Documentation updates

## 🆘 **Common Issues & Solutions**

| Issue | Solution |
|-------|----------|
| Podman not found | Install [Podman Desktop](https://podman-desktop.io/) |
| Permission denied on scripts | Run `chmod +x ./dev.sh ./setup-local-dev.sh` |
| Database connection error | Run `./dev.sh docker-reset` |
| Static files not loading | Run `./dev.sh collectstatic` |
| Tests failing | Ensure containers are running: `./dev.sh docker-up` |
| Port already in use | Check for other Django instances: `pkill -f runserver` |

## 📊 **Project Status**

### ✅ Completed Features
- ✅ User authentication and management
- ✅ Bunk and camper management
- ✅ Bunk logs system
- ✅ Orders CRUD API
- ✅ JWT authentication
- ✅ Role-based permissions
- ✅ API documentation
- ✅ Local development environment
- ✅ Production deployment
- ✅ CI/CD pipeline

### 🚧 In Development
- Frontend React application
- Real-time notifications
- Advanced reporting features
- Mobile app integration

## 📊 **Monitoring & Maintenance**

### Local Development Monitoring
```bash
# View application logs
./dev.sh logs

# Monitor database activity
./dev.sh shell
>>> from django.db import connection; print(connection.queries[-5:])

# Check container resource usage
podman stats
# or
docker stats
```

### Production Monitoring
```bash
# View Cloud Run logs
gcloud run services logs read bunk-logs-backend --region=us-central1 --limit=50

# Monitor service health
gcloud run services describe bunk-logs-backend --region=us-central1

# Check deployment history
gcloud run revisions list --service=bunk-logs-backend --region=us-central1
```

### Maintenance Tasks
```bash
# Regular database backup (local)
./dev.sh backup-db

# Update dependencies
pip list --outdated
pip install -r requirements/local.txt --upgrade

# Clean up development environment
./dev.sh clean

# Reset development environment
./dev.sh docker-reset
```

### Performance Optimization
- Monitor database query performance with Django Debug Toolbar
- Use Redis caching for frequently accessed data
- Optimize static file serving with whitenoise
- Monitor Cloud Run metrics in Google Cloud Console

---

**Happy coding! 🎉**

For additional help, check:
- `API_DOCUMENTATION.md` for API details
- `README.md` for quick start guide
- GitHub Issues for known problems
- Production logs for deployment issues
