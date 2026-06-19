"""Payfin — centralized configuration for Vercel serverless deployment."""

from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_db_url(url: str) -> str:
  """Inject pg8000 driver into any postgresql:// URL."""
  if not url:
    return url
  if url.startswith("postgres://"):
    return "postgresql+pg8000://" + url[len("postgres://"):]
  if url.startswith("postgresql://"):
    return "postgresql+pg8000://" + url[len("postgresql://"):]
  if url.startswith("postgresql+psycopg2://"):
    return "postgresql+pg8000://" + url[len("postgresql+psycopg2://"):]
  if url.startswith("postgresql+psycopg://"):
    return "postgresql+pg8000://" + url[len("postgresql+psycopg://"):]
  return url


def _get_db_url() -> str:
  """
  Try every env var name that Vercel + Neon integration might set.
  Vercel-Neon integration sets: POSTGRES_URL, POSTGRES_PRISMA_URL, POSTGRES_URL_NON_POOLING
  Manual setup sets: DATABASE_URL
  Also support individual PGHOST/PGUSER/PGPASSWORD/PGDATABASE vars.
  """
  # 1. Explicit DATABASE_URL (manual setup)
  url = os.environ.get("DATABASE_URL", "").strip()
  if url:
    return _normalize_db_url(url)

  # 2. Vercel-Neon native integration variable names
  for key in ("POSTGRES_URL", "POSTGRES_URL_NON_POOLING", "POSTGRES_PRISMA_URL"):
    url = os.environ.get(key, "").strip()
    if url:
      return _normalize_db_url(url)

  # 3. Individual PG* vars (Neon also sets these)
  host = os.environ.get("PGHOST", "").strip()
  user = os.environ.get("PGUSER", "").strip()
  password = os.environ.get("PGPASSWORD", "").strip()
  database = os.environ.get("PGDATABASE", "").strip()
  port = os.environ.get("PGPORT", "5432").strip()
  if host and user and password and database:
    return f"postgresql+pg8000://{user}:{password}@{host}:{port}/{database}?ssl=true"

  # 4. Fallback — local dev only
  import sys
  if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    print(
      "FATAL: No database URL found! Set DATABASE_URL or connect Neon in Vercel dashboard.",
      file=sys.stderr,
    )
  return "postgresql+pg8000://payfin:payfin@localhost:5432/payfin"


def _get_pool_url() -> str:
  """Pooled URL — prefer POSTGRES_URL (Neon pooler) over non-pooling URL."""
  # 1. Explicit pool URL
  url = os.environ.get("DATABASE_POOL_URL", "").strip()
  if url:
    return _normalize_db_url(url)

  # 2. Vercel-Neon pooler URL
  url = os.environ.get("POSTGRES_URL", "").strip()
  if url:
    return _normalize_db_url(url)

  # 3. Fall back to direct URL
  return _get_db_url()


class Config:
  SECRET_KEY: str = os.environ.get("SECRET_KEY", "payfin-dev-secret-change-in-production-32chars")
  FLASK_ENV: str = os.environ.get("FLASK_ENV", "development")
  DEBUG: bool = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
  PORT: int = int(os.environ.get("PORT", "5000"))

  JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "payfin-jwt-dev-change-in-production-32chars")
  JWT_EXPIRY_HOURS: int = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
  JWT_ALGORITHM: str = "HS256"

  # Resolved at import time — all os.environ reads happen inside the functions above
  DATABASE_URL: str = _get_db_url()
  DATABASE_POOL_URL: str = _get_pool_url()

  REDIS_URL: str = os.environ.get("REDIS_URL", "")
  RATELIMIT_STORAGE_URI: str = (
    os.environ.get("RATELIMIT_STORAGE_URI", "")
    or os.environ.get("REDIS_URL", "")
    or "memory://"
  )

  COMPANY_NAME: str = os.environ.get("COMPANY_NAME", "Payfin")
  APP_NAME: str = os.environ.get("APP_NAME", "Payfin")
  UPI_SUFFIX: str = os.environ.get("UPI_SUFFIX", "payfin")

  CORS_ORIGINS: list = [
    o.strip()
    for o in os.environ.get(
      "CORS_ORIGINS",
      "http://localhost:3000,https://*.vercel.app"
    ).split(",")
    if o.strip()
  ]

  MFA_ISSUER: str = os.environ.get("MFA_ISSUER", "Payfin")
  WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", "payfin-webhook-hmac-secret-change-me")

  RAZORPAY_KEY_ID: str = os.environ.get("RAZORPAY_KEY_ID", "")
  RAZORPAY_KEY_SECRET: str = os.environ.get("RAZORPAY_KEY_SECRET", "")
  CASHFREE_APP_ID: str = os.environ.get("CASHFREE_APP_ID", "")
  CASHFREE_SECRET_KEY: str = os.environ.get("CASHFREE_SECRET_KEY", "")
  STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
  PAYMENT_PROVIDER: str = os.environ.get("PAYMENT_PROVIDER", "razorpay")

  RAZORPAY_IFSC_API: str = os.environ.get("RAZORPAY_IFSC_API", "https://ifsc.razorpay.com")
  NPCI_VPA_VERIFY_URL: str = os.environ.get("NPCI_VPA_VERIFY_URL", "")

  PUSHER_APP_ID: str = os.environ.get("PUSHER_APP_ID", "")
  PUSHER_KEY: str = os.environ.get("PUSHER_KEY", "")
  PUSHER_SECRET: str = os.environ.get("PUSHER_SECRET", "")
  PUSHER_CLUSTER: str = os.environ.get("PUSHER_CLUSTER", "ap2")
  SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
  SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

  SESSION_COOKIE_HTTPONLY: bool = True
  SESSION_COOKIE_SAMESITE: str = "Lax"
  SESSION_COOKIE_SECURE: bool = os.environ.get("FLASK_ENV", "development") == "production"
  MAX_CONTENT_LENGTH: int = 1 * 1024 * 1024
  IDEMPOTENCY_TTL_SECONDS: int = int(os.environ.get("IDEMPOTENCY_TTL_SECONDS", "86400"))

  FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
