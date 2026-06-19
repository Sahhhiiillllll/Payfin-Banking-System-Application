"""Temporary debug endpoint — shows which env vars Vercel has set (no secrets)."""

from __future__ import annotations
import os
from flask import Blueprint, jsonify

debug_bp = Blueprint("debug", __name__, url_prefix="/api")


@debug_bp.route("/debug-env", methods=["GET"])
def debug_env():
  """Shows which database-related env vars are present (values masked)."""
  keys_to_check = [
    "DATABASE_URL", "DATABASE_POOL_URL",
    "POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING",
    "PGHOST", "PGUSER", "PGDATABASE", "PGPORT", "PGPASSWORD",
    "FLASK_ENV", "VERCEL", "VERCEL_ENV", "VERCEL_REGION",
    "SECRET_KEY", "JWT_SECRET_KEY",
  ]
  result = {}
  for key in keys_to_check:
    val = os.environ.get(key, "")
    if val:
      # Mask secrets but show first 10 chars so we can confirm it's set
      if any(s in key for s in ["PASSWORD", "SECRET", "KEY", "URL"]):
        result[key] = val[:15] + "..." if len(val) > 15 else "SET (short)"
      else:
        result[key] = val
    else:
      result[key] = "❌ NOT SET"

  from config import _get_db_url
  resolved = _get_db_url()
  result["_resolved_db_url"] = resolved[:30] + "..." if len(resolved) > 30 else resolved

  return jsonify(result), 200
