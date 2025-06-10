# BunkLogs Backend API

A comprehensive Django-based REST API for managing summer camp operations, including campers, bunks, orders, and logistics.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: MIT

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker/Podman with Compose
- Git

### Local Development Setup

1. **Clone and Setup Environment:**
   ```bash
   git clone <repository-url>
   cd BunkLogs/backend
   ./setup-local-dev.sh
   ```

2. **Start Development Environment:**
   ```bash
   ./dev.sh docker-up
   ```

3. **Access the Application:**
   - API Documentation: http://localhost:8000/api/schema/swagger-ui/
   - Admin Panel: http://localhost:8000/admin/
   - Email Testing: http://localhost:8025/

### Development Commands

Use the `./dev.sh` helper script for common development tasks:

```bash
./dev.sh docker-up      # Start all services
./dev.sh docker-down    # Stop all services
./dev.sh logs           # View Django logs
./dev.sh test           # Run tests
./dev.sh migrate        # Run database migrations
./dev.sh shell          # Django shell
./dev.sh superuser      # Create admin user
./dev.sh help           # Show all commands
```

## 🏗️ Architecture

### Tech Stack
- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Authentication**: Django Allauth with MFA support
- **API Docs**: DRF Spectacular (OpenAPI 3.0)
- **Deployment**: Google Cloud Run

### Key Features
- RESTful API with comprehensive documentation
- Multi-factor authentication
- Role-based access control
- File upload and storage
- Real-time notifications
- Comprehensive test suite

## 📱 API Endpoints

### Authentication
- `POST /auth/signup/` - User registration
- `POST /auth/login/` - User login
- `POST /auth/logout/` - User logout
- `GET /auth/user/` - Current user profile

### Core Resources
- `/api/campers/` - Camper management
- `/api/bunks/` - Bunk assignments
- `/api/orders/` - Order processing
- `/api/users/` - User management

### Documentation
- `/api/schema/` - OpenAPI schema
- `/api/schema/swagger-ui/` - Interactive API docs
- `/api/schema/redoc/` - ReDoc documentation

## 🔧 Configuration

### Environment Variables
See `DEVELOPMENT_GUIDE.md` for complete environment setup instructions.

### Docker Services
- **Django**: Main application server
- **PostgreSQL**: Primary database
- **Redis**: Caching and sessions
- **Mailpit**: Email testing (development only)

## 🧪 Testing

```bash
./dev.sh test              # Run all tests
./dev.sh test-coverage     # Run with coverage report
```

## 🚢 Deployment

### Production Deployment (Google Cloud Run)
Automatic deployment via GitHub Actions on push to main branch.

**Required GitHub Secrets:**
- `GCP_SA_KEY` - Service account credentials
- `DJANGO_SECRET_KEY` - Production secret key
- `POSTGRES_PASSWORD` - Database password

### Manual Deployment
See deployment scripts in the project root for manual deployment options.

## 📚 Documentation

- `DEVELOPMENT_GUIDE.md` - Complete development setup
- `API_DOCUMENTATION.md` - Detailed API reference
- `/api/schema/swagger-ui/` - Interactive API documentation

## 🤝 Development Workflow

1. **Setup**: Run `./setup-local-dev.sh` for initial setup
2. **Code**: Make changes with hot-reload via `./dev.sh docker-up`
3. **Test**: Ensure tests pass with `./dev.sh test`
4. **Deploy**: Push to main for automatic deployment

## 📞 Support

For development issues, refer to `DEVELOPMENT_GUIDE.md` or check the container logs with `./dev.sh logs`.

## Production URLs
- **API**: https://bunk-logs-backend-461994890254.us-central1.run.app
- **Admin**: https://bunk-logs-backend-461994890254.us-central1.run.app/admin/
- **Docs**: https://bunk-logs-backend-461994890254.us-central1.run.app/api/schema/swagger-ui/

Container mailpit will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally-docker.html) for more details how to start all containers.

With Mailpit running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).
