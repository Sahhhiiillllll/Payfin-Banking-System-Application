"""
Payfin API — Vercel Serverless entry point.

Vercel auto-detects Flask `app` and routes /api/* via vercel.json rewrites.
"""

import os
import sys

# Ensure api/ modules resolve when Vercel loads this file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_factory import create_app, init_db

app = create_app()

# Initialize schema + demo seed on cold start (idempotent)
if os.getenv("VERCEL") or os.getenv("INIT_DB_ON_STARTUP", "true").lower() == "true":
  try:
    init_db()
  except Exception:
    pass
