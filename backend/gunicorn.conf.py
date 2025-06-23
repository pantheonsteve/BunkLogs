"""
Gunicorn configuration for production deployment.
Optimized for bulk operations and long-running requests.
"""
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes - optimized for Render.com and bulk operations
workers = int(os.getenv('WEB_CONCURRENCY', '1'))  # Single worker for bulk ops
worker_class = "sync"
worker_connections = 1000
timeout = 600  # 10 minutes for bulk operations (Render.com allows up to 15 min)
keepalive = 2
graceful_timeout = 120  # Allow graceful shutdown for long-running requests

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "bunklogs"

# Server mechanics
preload_app = True
sendfile = True

# Security
limit_request_line = 0  # Unlimited for file uploads
limit_request_fields = 100
limit_request_field_size = 8192

# Performance tuning for bulk operations
worker_tmp_dir = "/dev/shm"  # Use tmpfs for better performance
