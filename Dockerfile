# ──────────────────────────────────────────────────────────
# Payfin Financial Technologies — Production Dockerfile
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim

# Labels
LABEL maintainer="Payfin"
LABEL description="Payfin — Production Banking Web Application"
LABEL version="1.0.0"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

# Create non-root user
RUN groupadd -r payfin && useradd -r -g payfin payfin

# Work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=payfin:payfin . .

# Create data directory
RUN mkdir -p /app/data && chown -R payfin:payfin /app/data

# Switch to non-root user
USER payfin

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/auth/me')" || exit 1

# Start with Gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "sync", \
     "--timeout", "60", \
     "--keepalive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]
