# 🚀 BunkLogs Deployment Guide

## Quick Start Deployment Commands

### Backend (Django + Elastic Beanstalk)
```bash
cd backend
./deploy_with_timeout.sh    # Recommended: Full monitoring
# OR
eb deploy --timeout 1200    # Standard with extended timeout
# OR  
./deploy_fast.sh           # Quick deployment
```

### Frontend (React + Static Hosting)
```bash
cd frontend
./deploy.sh                # Automated frontend deployment
```

---

## 🎯 Backend Deployment (Django API)

### Platform: AWS Elastic Beanstalk (Docker)

### ⚡ Quick Deploy (Most Common)
```bash
cd backend
./deploy_with_timeout.sh
```
- **Includes**: Progress monitoring, timeout warnings, local testing option
- **Timeout**: 20 minutes (handles long Docker builds)
- **Safety**: Rolling deployment with health checks

### 🔧 Pre-Deployment Checklist
1. **Validate Configuration**:
   ```bash
   cd backend
   ./validate_timeout_config.sh
   ```

2. **Test Docker Build Locally** (Optional but Recommended):
   ```bash
   docker build -t bunklogs-backend-test . --progress=plain
   docker rmi bunklogs-backend-test  # cleanup
   ```

3. **Check Environment Variables** in `.ebextensions/03_django.config`:
   - `DJANGO_SECRET_KEY` - Update with production secret
   - `DJANGO_ALLOWED_HOSTS` - Verify domain names
   - Email settings (if using email features)

### 📋 Backend Deployment Options

| Command | Use Case | Features |
|---------|----------|----------|
| `./deploy_with_timeout.sh` | **Production** | Full monitoring, 20min timeout, safety checks |
| `eb deploy --timeout 1200` | **Standard** | Basic EB deploy with extended timeout |
| `./deploy_fast.sh` | **Quick Updates** | Fast deployment for small changes |
| `eb deploy` | **Emergency** | Default EB (5min timeout - may fail) |

### 🐳 Docker Build Optimizations (Already Configured)
- ✅ **Multi-stage build**: Wheels built in builder stage
- ✅ **Extended timeout**: 20 minutes for complex builds  
- ✅ **Optimized context**: 57 exclusions in `.dockerignore`
- ✅ **Fast installs**: Pre-built wheels (2-4min builds)

### 🔍 Monitoring & Troubleshooting
```bash
# Check deployment status
eb status

# View deployment events
eb events --follow

# Check application logs
eb logs

# Check application health
eb health

# SSH into instance (if needed)
eb ssh
```

### ⚠️ Common Issues & Solutions

**Build Timeout (>20 minutes)**:
- Check Docker build logs: `eb logs`
- Verify wheel optimization is working
- Consider removing unnecessary dependencies

**Health Check Failures**:
- Check Django settings in production
- Verify database migrations completed
- Check application logs: `eb logs`

**Deployment Stuck**:
- Use rolling deployment (already configured)
- Check EB events: `eb events`
- Consider `eb abort` if needed

**Docker Command Not Found**:
- If using Podman instead of Docker, use `--skip-test` flag:
  ```bash
  ./deploy_fast.sh --skip-test
  ```
- Or use the timeout deployment which doesn't require local Docker:
  ```bash
  ./deploy_with_timeout.sh
  ```

**Deployment Timeout Issues (Extended Build Times)**:
- Current Docker builds are taking 20+ minutes, exceeding EB timeout limits
- Even with extended timeout configuration (20 minutes), complex builds may fail
- **Immediate Solutions**:
  - Use the current working version while optimizing build process
  - Consider simplifying Dockerfile dependencies
  - Implement pre-built base images for faster builds
- **Long-term**: Migrate to a different deployment strategy (e.g., separate CI/CD pipeline)

**Google OAuth "redirect_uri_mismatch" Error**:
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Navigate to **APIs & Services** > **Credentials**
- Find your OAuth 2.0 Client ID and edit it
- In **Authorized redirect URIs**, ensure you have:
  ```
  https://admin.bunklogs.net/api/auth/google/callback/
  ```
- Save changes and wait 5-10 minutes for propagation

---

## 🌐 Frontend Deployment (React SPA)

### Platform: Static Hosting (Vercel/Netlify/S3+CloudFront)

### ⚡ Quick Deploy
```bash
cd frontend
./deploy.sh
```

### 🔧 Manual Deployment Steps
1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   # OR
   pnpm install
   ```

2. **Build Production Bundle**:
   ```bash
   npm run build
   # OR  
   pnpm build
   ```

3. **Deploy Built Files**:
   - **Vercel**: `vercel --prod`
   - **Netlify**: Drag `dist/` folder to Netlify dashboard
   - **S3+CloudFront**: Upload `dist/` contents to S3 bucket

### ⚙️ Frontend Configuration

**Environment Variables** (Set in hosting platform):
```bash
VITE_API_URL=https://your-backend-url.elasticbeanstalk.com
VITE_APP_ENV=production
```

**Build Settings**:
- **Build Command**: `npm run build` or `pnpm build`
- **Publish Directory**: `dist`
- **Node Version**: 18+ (check `package.json`)

---

## 🔄 Full Application Deployment Workflow

### For Complete Deployment (Backend + Frontend):

1. **Deploy Backend First**:
   ```bash
   cd backend
   ./deploy_with_timeout.sh
   ```

2. **Get Backend URL**:
   ```bash
   eb status  # Note the CNAME/URL
   ```

3. **Update Frontend Config** (if URL changed):
   - Update `VITE_API_URL` in hosting platform
   - OR update `src/config.js` if hardcoded

4. **Deploy Frontend**:
   ```bash
   cd frontend
   ./deploy.sh
   ```

### 🧪 Testing Deployed Application
1. **Backend API**: `https://your-app.elasticbeanstalk.com/api/health/`
2. **Frontend**: Check main domain loads correctly
3. **Integration**: Test frontend can connect to backend API

---

## 📁 Important Files & Directories

### Backend Configuration
```
backend/
├── .ebextensions/           # EB configuration
│   ├── 00_timeout.config   # 20-minute timeout settings
│   ├── 01_django.config    # Django environment  
│   ├── 02_commands.config  # Database migration
│   └── 03_django.config    # Production settings
├── Dockerfile              # Multi-stage Docker build
├── .dockerignore          # Build context optimization
├── requirements/          # Python dependencies
│   └── production.txt     # Production packages
└── deploy_with_timeout.sh # Main deployment script
```

### Frontend Configuration  
```
frontend/
├── src/
│   ├── api.js            # Backend API configuration
│   └── config.js         # Environment configuration
├── dist/                 # Built files (generated)
├── package.json          # Dependencies & scripts
├── vite.config.js        # Build configuration
└── deploy.sh            # Deployment script
```

---

## 🚨 Emergency Procedures

### Backend Issues
```bash
# Rollback to previous version
eb deploy --version-label <previous-version>

# Abort stuck deployment
eb abort

# Emergency restart
eb restart-app-server

# Check recent deployments
eb history
```

### Frontend Issues
- **Vercel**: Use dashboard to rollback deployment
- **Netlify**: Use dashboard to rollback to previous deploy
- **S3**: Restore from backup or redeploy previous build

---

## 📝 Environment-Specific Notes

### Production
- ✅ Extended timeouts configured (20 minutes)
- ✅ Rolling deployments for safety
- ✅ Enhanced health monitoring
- ✅ Docker build optimization active

### Development
- Use `docker-compose.local.yml` for local development
- Database: Local PostgreSQL or SQLite
- Debug mode enabled in local settings

### Staging (if used)
- Same as production but with staging environment variables
- Separate EB environment: `bunklogs-backend-staging`

---

## 💻 Local Development Workflow

### 🛠️ Setting Up Local Environment

#### Backend Development Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements/local.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your local settings

# Run database migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

#### Frontend Development Setup
```bash
cd frontend

# Install dependencies
pnpm install
# OR
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your local settings

# Start development server
pnpm dev
# OR
npm run dev
```

### 🐳 Docker Development Environment

#### Using Docker Compose for Full Stack
```bash
# Start all services (recommended for full development)
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Stop services
docker-compose -f docker-compose.local.yml down

# Rebuild containers after code changes
docker-compose -f docker-compose.local.yml up --build
```

#### Backend Only with Docker
```bash
cd backend

# Build and run backend container
docker build -f Dockerfile -t bunklogs-backend-dev .
docker run -p 8000:8000 --env-file .env bunklogs-backend-dev

# Or use docker-compose for backend + database
docker-compose -f docker-compose.local.yml up backend postgres
```

### 🔄 Development Workflow

#### Daily Development Process
1. **Start Development Environment**:
   ```bash
   # Option 1: Full Docker stack
   docker-compose -f docker-compose.local.yml up -d
   
   # Option 2: Native development
   cd backend && source .venv/bin/activate && python manage.py runserver &
   cd frontend && pnpm dev
   ```

2. **Make Changes**:
   - Edit code in your preferred IDE/editor
   - Backend changes: Auto-reload with Django development server
   - Frontend changes: Hot-reload with Vite

3. **Test Changes**:
   ```bash
   # Backend tests
   cd backend && python manage.py test
   
   # Frontend tests (if configured)
   cd frontend && pnpm test
   
   # Integration tests
   ./e2e_test.sh
   ```

4. **Database Management**:
   ```bash
   # Create new migration after model changes
   python manage.py makemigrations
   
   # Apply migrations
   python manage.py migrate
   
   # Reset database (careful!)
   python manage.py flush
   ```

### 🧪 Testing Strategy

#### Backend Testing
```bash
cd backend

# Run all tests
python manage.py test

# Run specific app tests
python manage.py test bunk_logs.orders
python manage.py test bunk_logs.users

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

#### Frontend Testing
```bash
cd frontend

# Unit tests (if configured)
pnpm test

# E2E tests
pnpm test:e2e

# Build test
pnpm build
```

#### Integration Testing
```bash
# Full application test
./e2e_test.sh

# API testing
cd backend && python test_orders_api.py
cd backend && python test_auth.py
```

### 🔧 Debugging & Development Tools

#### Backend Debugging
```bash
# Django shell
python manage.py shell

# Database shell
python manage.py dbshell

# Check for issues
python manage.py check

# Collect static files
python manage.py collectstatic
```

#### Frontend Debugging
```bash
# Check bundle size
pnpm build && pnpm preview

# Lint code
pnpm lint

# Format code
pnpm format
```

---

## 📝 Version Control Strategy

### 🌟 Git Workflow (Recommended)

#### Branch Structure
```
main/master          # Production-ready code
├── develop          # Integration branch for features
├── feature/auth     # Feature branches
├── feature/orders   # Feature branches
├── hotfix/critical  # Critical fixes
└── release/v1.0     # Release preparation
```

#### Daily Git Workflow
```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# Work on feature with frequent commits
git add .
git commit -m "feat: add user authentication endpoint"

# Push feature branch
git push -u origin feature/your-feature-name

# When feature is complete, merge to develop
git checkout develop
git pull origin develop
git merge feature/your-feature-name
git push origin develop

# Deploy to staging for testing
git checkout develop
./deploy_staging.sh  # If you have staging environment

# When ready for production
git checkout main
git pull origin main
git merge develop
git tag v1.0.1
git push origin main --tags

# Deploy to production
./deploy_with_timeout.sh
```

### 📋 Commit Message Strategy

#### Conventional Commits Format
```bash
# Feature additions
git commit -m "feat: add order management API"
git commit -m "feat(frontend): implement order tracking page"

# Bug fixes
git commit -m "fix: resolve Docker timeout issues"
git commit -m "fix(auth): handle token expiration properly"

# Documentation
git commit -m "docs: update deployment README"

# Configuration changes
git commit -m "config: extend EB timeout to 20 minutes"

# Refactoring
git commit -m "refactor: optimize Docker build process"

# Tests
git commit -m "test: add orders API integration tests"

# Chores (dependencies, build, etc.)
git commit -m "chore: update Django to 4.2.7"
```

### 🛡️ Protecting Your Work

#### Essential Git Practices
```bash
# Save work before major changes
git add .
git commit -m "wip: save current progress"
git push origin feature/your-branch

# Create backup branch before risky operations
git checkout -b backup/before-major-refactor

# Stash changes when switching branches
git stash push -m "current work on auth feature"
git checkout other-branch
# Later: git stash pop

# Check what you're about to commit
git diff --staged
git status

# Amend last commit if needed (before pushing)
git add forgotten-file.py
git commit --amend --no-edit
```

#### Daily Backup Strategy
```bash
# End of day - save all work
git add .
git commit -m "eod: save progress on [feature description]"
git push origin current-branch

# Weekly - create backup tags
git tag backup/week-$(date +%Y-%m-%d)
git push origin --tags
```

### 🚀 Deployment Branch Strategy

#### Production Deployment
```bash
# Only deploy from main/master branch
git checkout main
git pull origin main

# Verify you're on the right branch and commit
git branch --show-current
git log --oneline -5

# Tag the release
git tag v$(date +%Y.%m.%d)-prod
git push origin --tags

# Deploy
./deploy_with_timeout.sh
```

#### Emergency Hotfixes
```bash
# Create hotfix from production
git checkout main
git checkout -b hotfix/critical-bug-fix

# Make minimal changes
# ... fix the bug ...

# Test and commit
git add .
git commit -m "hotfix: resolve critical production issue"

# Merge to main and develop
git checkout main
git merge hotfix/critical-bug-fix
git push origin main

git checkout develop
git merge hotfix/critical-bug-fix
git push origin develop

# Deploy immediately
./deploy_with_timeout.sh

# Clean up
git branch -d hotfix/critical-bug-fix
```

### 📊 Git History Management

#### Keeping Clean History
```bash
# Interactive rebase to clean up commits before pushing
git rebase -i HEAD~3

# Squash feature commits before merging
git checkout feature/my-feature
git rebase -i develop

# Force push after rebase (only on feature branches!)
git push --force-with-lease origin feature/my-feature
```

#### Important Git Configurations
```bash
# Set up git properly
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Useful aliases
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual '!gitk'

# Safe defaults
git config --global push.default simple
git config --global pull.rebase true
```

---

## 🔑 Key Reminders

### Before Every Deployment
1. ✅ Test locally with Docker
2. ✅ Check environment variables are set
3. ✅ Verify database migrations are ready
4. ✅ Ensure secrets are updated in production

### After Every Deployment  
1. ✅ Check application health: `eb health`
2. ✅ Test main functionality
3. ✅ Monitor logs for errors: `eb logs`
4. ✅ Verify frontend can connect to backend

### Monthly Maintenance
1. 🔄 Update dependencies in `requirements/production.txt`
2. 🔄 Review and update environment variables
3. 🔄 Check EB platform version updates
4. 🔄 Monitor application performance metrics

---

## 📞 Quick Reference Commands

```bash
# Backend deployment status
cd backend && eb status

# View backend logs  
cd backend && eb logs

# Validate backend configuration
cd backend && ./validate_timeout_config.sh

# Test backend Docker build
cd backend && docker build -t test . --progress=plain

# Frontend build and test
cd frontend && npm run build && npm run preview

# Full deployment workflow
cd backend && ./deploy_with_timeout.sh && cd ../frontend && ./deploy.sh
```

**🎉 You're ready to deploy! The timeout issues are resolved and optimizations are active.**
