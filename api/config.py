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
    url = "postgresql+pg8000://" + url[len("postgres://"):]
  elif url.startswith("postgresql://"):
    url = "postgresql+pg8000://" + url[len("postgresql://"):]
  elif url.startswith("postgresql+psycopg2://"):
    url = "postgresql+pg8000://" + url[len("postgresql+psycopg2://"):]
  elif url.startswith("postgresql+psycopg://"):
    url = "postgresql+pg8000://" + url[len("postgresql+psycopg://"):]
  return url


def _get_db_url() -> str:
  """Read DATABASE_URL at call time (not import time) so Vercel env vars are available."""
  raw = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
  if not raw:
    # Only fall back to localhost in local dev — crash loudly on Vercel if not set
    import sys
    is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
    if is_vercel:
      print("FATAL: DATABASE_URL environment variable is not set!", file=sys.stderr)
    return "postgresql+pg8000://payfin:payfin@localhost:5432/payfin"
  return _normalize_db_url(raw)


def _get_pool_url() -> str:
  raw = os.environ.get("DATABASE_POOL_URL") or os.environ.get("POSTGRES_PRISMA_URL") or ""
  if raw:
    return _normalize_db_url(raw)
  return _get_db_url()


class Config:
  # Core
  SECRET_KEY: str = os.environ.get("SECRET_KEY", "payfin-dev-secret-change-in-production-32chars")
  FLASK_ENV: str = os.environ.get("FLASK_ENV", "development")
  DEBUG: bool = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
  PORT: int = int(os.environ.get("PORT", "5000"))

  # JWT
  JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "payfin-jwt-dev-change-in-production-32chars")
  JWT_EXPIRY_HOURS: int = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
  JWT_ALGORITHM: str = "HS256"

  # PostgreSQL — resolved at call time via functions above
  DATABASE_URL: str = _get_db_url()
  DATABASE_POOL_URL: str = _get_pool_url()

  # Redis
  REDIS_URL: str = os.environ.get("REDIS_URL", "")
  RATELIMIT_STORAGE_URI: str = os.environ.get("RATELIMIT_STORAGE_URI", "") or os.environ.get("REDIS_URL", "") or "memory://"

  # Branding
  COMPANY_NAME: str = os.environ.get("COMPANY_NAME", "Payfin")
  APP_NAME: str = os.environ.get("APP_NAME", "Payfin")
  UPI_SUFFIX: str = os.environ.get("UPI_SUFFIX", "payfin")

  # CORS
  CORS_ORIGINS: list = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000,https://*.vercel.app").split(",")
    if o.strip()
  ]

  # MFA
  MFA_ISSUER: str = os.environ.get("MFA_ISSUER", "Payfin")

  # Webhooks
  WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", "payfin-webhook-hmac-secret-change-me")

  # Payment aggregators
  RAZORPAY_KEY_ID: str = os.environ.get("RAZORPAY_KEY_ID", "")
  RAZORPAY_KEY_SECRET: str = os.environ.get("RAZORPAY_KEY_SECRET", "")
  CASHFREE_APP_ID: str = os.environ.get("CASHFREE_APP_ID", "")
  CASHFREE_SECRET_KEY: str = os.environ.get("CASHFREE_SECRET_KEY", "")
  STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
  PAYMENT_PROVIDER: str = os.environ.get("PAYMENT_PROVIDER", "razorpay")

  # External verification
  RAZORPAY_IFSC_API: str = os.environ.get("RAZORPAY_IFSC_API", "https://ifsc.razorpay.com")
  NPCI_VPA_VERIFY_URL: str = os.environ.get("NPCI_VPA_VERIFY_URL", "")

  # Realtime
  PUSHER_APP_ID: str = os.environ.get("PUSHER_APP_ID", "")
  PUSHER_KEY: str = os.environ.get("PUSHER_KEY", "")
  PUSHER_SECRET: str = os.environ.get("PUSHER_SECRET", "")
  PUSHER_CLUSTER: str = os.environ.get("PUSHER_CLUSTER", "ap2")
  SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
  SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

  # Security
  SESSION_COOKIE_HTTPONLY: bool = True
  SESSION_COOKIE_SAMESITE: str = "Lax"
  SESSION_COOKIE_SECURE: bool = os.environ.get("FLASK_ENV", "development") == "production"
  MAX_CONTENT_LENGTH: int = 1 * 1024 * 1024
  IDEMPOTENCY_TTL_SECONDS: int = int(os.environ.get("IDEMPOTENCY_TTL_SECONDS", "86400"))

  # Frontend URL
  FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
