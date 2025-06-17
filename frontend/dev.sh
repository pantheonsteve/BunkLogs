#!/bin/bash

# Frontend Development Helper Script
# Usage: ./dev.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show help
show_help() {
    echo "BunkLogs Frontend Development Helper"
    echo "===================================="
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start           - Start development server (port 5173)"
    echo "  build           - Build for production"
    echo "  preview         - Preview production build"
    echo "  test            - Run tests"
    echo "  test:watch      - Run tests in watch mode"
    echo "  install         - Install dependencies"
    echo "  clean           - Clean node_modules and reinstall"
    echo "  env             - Show current environment variables"
    echo "  help            - Show this help message"
}

# Check if backend is running
check_backend() {
    print_status "Checking if backend is running on port 8000..."
    if curl -s http://localhost:8000/api/schema/ > /dev/null 2>&1; then
        print_success "Backend is running on http://localhost:8000"
    else
        print_warning "Backend doesn't seem to be running on port 8000"
        print_warning "Make sure to start your backend first:"
        print_warning "  cd ../backend && ./dev.sh start"
    fi
}

case "$1" in
    start)
        check_backend
        print_status "Starting frontend development server on port 5173..."
        print_status "Frontend will be available at: http://localhost:5173"
        print_status "Using local environment (.env.local)"
        npm run dev
        ;;
    
    build)
        print_status "Building frontend for production..."
        npm run build
        print_success "Build complete! Check the dist/ folder"
        ;;
    
    preview)
        print_status "Starting preview server..."
        npm run preview
        ;;
    
    test)
        print_status "Running tests..."
        npm run test
        ;;
    
    test:watch)
        print_status "Running tests in watch mode..."
        npm run test:watch
        ;;
    
    install)
        print_status "Installing dependencies..."
        npm install
        print_success "Dependencies installed!"
        ;;
    
    clean)
        print_status "Cleaning node_modules and package-lock.json..."
        rm -rf node_modules package-lock.json
        print_status "Reinstalling dependencies..."
        npm install
        print_success "Clean install complete!"
        ;;
    
    env)
        print_status "Current environment configuration:"
        echo ""
        echo "Environment files (in order of precedence):"
        if [ -f ".env.local" ]; then
            echo "  ✅ .env.local (local development - highest priority)"
            echo "     VITE_API_URL=$(grep VITE_API_URL .env.local | cut -d '=' -f2)"
        else
            echo "  ❌ .env.local (not found)"
        fi
        
        if [ -f ".env" ]; then
            echo "  ✅ .env (default)"
            echo "     VITE_API_URL=$(grep VITE_API_URL .env | cut -d '=' -f2)"
        else
            echo "  ❌ .env (not found)"
        fi
        
        if [ -f ".env.production" ]; then
            echo "  ✅ .env.production (production)"
            echo "     VITE_API_URL=$(grep VITE_API_URL .env.production | cut -d '=' -f2)"
        else
            echo "  ❌ .env.production (not found)"
        fi
        
        echo ""
        print_status "For local development, frontend will use: http://localhost:8000"
        print_status "For production builds, frontend will use the production API URL"
        ;;
    
    help|"")
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
