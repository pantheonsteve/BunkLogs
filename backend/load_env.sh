#!/bin/bash

# Load environment variables from .envs directory
set -o allexport

# Load Django environment variables
if [ -f ".envs/.local/.django" ]; then
    source .envs/.local/.django
fi

# Load Postgres environment variables  
if [ -f ".envs/.local/.postgres" ]; then
    source .envs/.local/.postgres
fi

set +o allexport

# Override Docker-specific settings for local development
export USE_DOCKER=no
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
export DJANGO_SETTINGS_MODULE=config.settings.local

echo "Environment variables loaded:"
echo "DATABASE_URL: $DATABASE_URL"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "DJANGO_DEBUG: $DJANGO_DEBUG"

# Execute the command passed as arguments
exec "$@"
