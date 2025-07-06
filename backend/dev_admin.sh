#!/bin/bash

# Local Development Admin Helper
# Provides admin functionality while the browser login issue is being resolved

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}🛠️  LOCAL DEVELOPMENT ADMIN HELPER${NC}"
    echo -e "${BLUE}=================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}💡 $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

show_admin_options() {
    print_header
    echo ""
    echo "Since browser admin login has session issues, here are your options:"
    echo ""
    echo "1. 🌐 Production Admin (Recommended)"
    echo "   URL: https://admin.bunklogs.net/admin/"
    echo "   This always works and has your real data"
    echo ""
    echo "2. 🐍 Django Shell (Local Development)"
    echo "   Command: ./dev_admin.sh shell"
    echo "   Direct access to Django ORM and admin functions"
    echo ""
    echo "3. 👥 User Management"
    echo "   List users: ./dev_admin.sh users"
    echo "   Create user: ./dev_admin.sh create"
    echo ""
    echo "4. 🧪 Test Admin Backend"
    echo "   Command: ./dev_admin.sh test"
    echo "   Verify Django admin is working internally"
    echo ""
    echo "5. 📦 Database Operations"
    echo "   Migrate: ./dev_admin.sh migrate"
    echo "   Shell: ./dev_admin.sh shell"
    echo ""
}

case "${1:-help}" in
    "users")
        print_info "Listing admin users..."
        podman exec -it bunk_logs_local_django python dev_admin.py users
        ;;
    
    "create")
        print_info "Creating new admin user..."
        podman exec -it bunk_logs_local_django python dev_admin.py create
        ;;
    
    "test")
        print_info "Testing admin functionality..."
        podman exec -it bunk_logs_local_django python dev_admin.py test
        ;;
    
    "shell")
        print_info "Launching Django shell..."
        echo "💡 Use this for admin tasks:"
        echo "   from django.contrib.auth import get_user_model"
        echo "   User = get_user_model()"
        echo "   # List all users: User.objects.all()"
        echo "   # Create user: User.objects.create_user(...)"
        echo ""
        podman exec -it bunk_logs_local_django python manage.py shell
        ;;
    
    "migrate")
        print_info "Running database migrations..."
        podman exec -it bunk_logs_local_django python manage.py migrate
        ;;
    
    "superuser")
        print_info "Creating superuser..."
        podman exec -it bunk_logs_local_django python manage.py createsuperuser
        ;;
    
    "browser")
        print_info "Opening local admin in browser..."
        print_warning "Note: This may not work due to session issues"
        if command -v open &> /dev/null; then
            open http://localhost:8000/admin/
        else
            echo "🌐 Open this URL: http://localhost:8000/admin/"
        fi
        ;;
    
    "production")
        print_info "Opening production admin..."
        if command -v open &> /dev/null; then
            open https://admin.bunklogs.net/admin/
        else
            echo "🌐 Open this URL: https://admin.bunklogs.net/admin/"
        fi
        ;;
    
    "help"|*)
        show_admin_options
        ;;
esac
