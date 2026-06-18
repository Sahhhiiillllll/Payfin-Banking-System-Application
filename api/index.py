"""
Payfin API — Vercel Serverless entry point.

Vercel auto-detects Flask `app` and routes /api/* via vercel.json rewrites.
This file MUST export `app` at module level for Vercel Python runtime.
"""

import os
import sys

# Ensure api/ directory is on the path so sibling modules resolve
_api_dir = os.path.dirname(os.path.abspath(__file__))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from app_factory import create_app, init_db

app = create_app()

# Initialize schema on first cold start only when explicitly enabled.
# Default is FALSE on Vercel (run migrations separately via Alembic/Neon console).
_should_init = os.getenv("INIT_DB_ON_STARTUP", "false").lower() == "true"
if _should_init:
    try:
        init_db()
    except Exception as _e:
        import logging
        logging.getLogger(__name__).warning("init_db skipped: %s", _e)

# Vercel expects the WSGI callable to be named `app` — do not rename.
