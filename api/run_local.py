#!/usr/bin/env python3
"""Local Flask dev server for Payfin API."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DATABASE_URL", "postgresql+pg8000://payfin:payfin@localhost:5432/payfin")
os.environ.setdefault("DATABASE_POOL_URL", os.environ["DATABASE_URL"])
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("INIT_DB_ON_STARTUP", "true")

from app_factory import create_app, init_db

app = create_app()

if __name__ == "__main__":
  try:
    init_db()
  except Exception as exc:
    print(f"DB init warning: {exc}")
  port = int(os.getenv("PORT", "5328"))
  print(f"Payfin API → http://127.0.0.1:{port}/api/health")
  app.run(host="0.0.0.0", port=port, debug=True)
