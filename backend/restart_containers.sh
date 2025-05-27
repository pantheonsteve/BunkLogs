#!/bin/bash

# Script to fix the order app references and restart Docker containers
# Created by GitHub Copilot to fix the app_label and model reference issues

echo "Fixing app references and restarting containers..."

# Navigate to project directory
cd /Users/stevebresnick/Projects/BunkLogs/backend

# Restart Docker containers
echo "Stopping Docker containers..."
docker-compose down

echo "Starting Docker containers..."
docker-compose up -d

echo "Done! Check the container logs with 'docker-compose logs -f' to verify everything starts correctly."
