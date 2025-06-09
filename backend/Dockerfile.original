# Dockerfile for Elastic Beanstalk deployment
# Place this file at: backend/Dockerfile

FROM python:3.12.9-slim-bookworm AS python

# Python build stage
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=production

# Install build dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential \
  libpq-dev \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and create wheels
COPY ./requirements .
RUN pip wheel --wheel-dir /usr/src/app/wheels -r ${BUILD_ENVIRONMENT}.txt

# Python run stage  
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

# Create non-root user for security
RUN addgroup --system django \
  && adduser --system --ingroup django django

# Install only runtime dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  libpq-dev \
  gettext \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Install Python packages from wheels
COPY --from=python-build-stage /usr/src/app/wheels /wheels/
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

# Copy application code with proper ownership
COPY --chown=django:django . ${APP_HOME}

# Ensure django user owns everything
RUN chown -R django:django ${APP_HOME}

# Switch to non-root user
USER django

# Pre-compile translations and collect static files
# Using dummy values so it doesn't try to connect during build
RUN DATABASE_URL="" \
  DJANGO_SECRET_KEY="build-time-secret-key-not-used-in-production" \
  DJANGO_DEBUG="False" \
  DJANGO_ALLOWED_HOSTS="localhost" \
  DJANGO_SETTINGS_MODULE="config.settings.production" \
  python manage.py compilemessages

RUN DATABASE_URL="" \
  DJANGO_SECRET_KEY="build-time-secret-key-not-used-in-production" \
  DJANGO_DEBUG="False" \
  DJANGO_ALLOWED_HOSTS="localhost" \
  DJANGO_SETTINGS_MODULE="config.settings.production" \
  python manage.py collectstatic --noinput

# Expose port 8000 (EB requirement)
EXPOSE 8000

# Start gunicorn with optimized settings for EB
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "config.wsgi:application"]