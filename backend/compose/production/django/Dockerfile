FROM python:3.12 AS python

# Python build stage
FROM python AS python-build-stage
ARG BUILD_ENVIRONMENT=production

# Install build dependencies and Datadog tracing library
RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/* \
  && pip install ddtrace

COPY requirements/ ./requirements/
RUN pip wheel --wheel-dir /usr/src/app/wheels -r requirements/${BUILD_ENVIRONMENT}.txt

# Python 'run' stage
FROM python AS python-run-stage
ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}
ENV PORT=8080

# Datadog environment variables (will be overridden by Cloud Run)
ENV DD_SERVICE="bunk-logs-backend"
ENV DD_ENV="production"
ENV DD_VERSION="1.0.0"
ENV DD_LOGS_INJECTION=true
ENV DD_TRACE_ENABLED=true
ENV DD_DJANGO_USE_HANDLER_RESOURCE_FORMAT=true
ENV DD_DJANGO_INSTRUMENT_TEMPLATES=true
ENV DD_DJANGO_USE_LEGACY_RESOURCE_FORMAT=false
ENV DD_SERVERLESS_LOG_PATH="/shared-volume/logs/*.log"

WORKDIR ${APP_HOME}

# Create user and install runtime dependencies in one layer
RUN addgroup --system django \
  && adduser --system --ingroup django django \
  && apt-get update \
  && apt-get install --no-install-recommends -y \
    libpq-dev \
    gettext \
    curl \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Install Cloud SQL Proxy
# ADD https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 /cloud_sql_proxy
# RUN chmod +x /cloud_sql_proxy

# Install Python packages
COPY --from=python-build-stage /usr/src/app/wheels /wheels/
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

# Copy entrypoint and start scripts
COPY ./compose/production/django/entrypoint /entrypoint
COPY ./compose/production/django/entrypoint.cloudrun /entrypoint.cloudrun
COPY ./compose/production/django/start-w-dd /start  # <-- Changed from 'start' to 'start-w-dd'
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint \
  && sed -i 's/\r$//g' /entrypoint.cloudrun && chmod +x /entrypoint.cloudrun \
  && sed -i 's/\r$//g' /start && chmod +x /start

# Copy application code
COPY --chown=django:django . ${APP_HOME}
RUN chown -R django:django ${APP_HOME}

# Create staticfiles directory and log directory for Datadog
RUN mkdir -p ${APP_HOME}/staticfiles && chown django:django ${APP_HOME}/staticfiles \
  && mkdir -p /shared-volume/logs && chown django:django /shared-volume/logs

USER django

EXPOSE 8080
ENTRYPOINT ["/entrypoint.cloudrun"]
CMD ["/start"]