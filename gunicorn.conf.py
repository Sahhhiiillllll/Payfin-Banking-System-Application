# Gunicorn production configuration
# Usage: gunicorn -c gunicorn.conf.py app:app

import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
threads = 2
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# Process name
proc_name = "payfin"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
