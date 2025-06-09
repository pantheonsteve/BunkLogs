# Fast Dockerfile optimized for development cycles
# Uses multi-stage build with aggressive caching
FROM python:3.12.9-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (this layer rarely changes)
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Create wheels cache stage
FROM base AS wheels
WORKDIR /wheels
# Copy requirements first (for better caching)
COPY requirements/base.txt requirements/production.txt ./
# Build wheels (this is cached unless requirements change)
RUN pip wheel --wheel-dir /wheels -r production.txt

# Production stage
FROM base AS production
WORKDIR /app

# Install from wheels (super fast)
COPY --from=wheels /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# Copy app code (only this layer changes with code updates)
COPY . /app/

# Create directories
RUN mkdir -p /app/staticfiles /app/media

# Runtime startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting Django application..."\n\
echo "📊 Running migrations..."\n\
python manage.py migrate --noinput || echo "⚠️  Migration failed, continuing..."\n\
echo "📁 Collecting static files..."\n\
python manage.py collectstatic --noinput --clear || echo "⚠️  Static collection failed, continuing..."\n\
echo "🌐 Starting Gunicorn..."\n\
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 60 config.wsgi:application\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000
CMD ["/app/start.sh"]
