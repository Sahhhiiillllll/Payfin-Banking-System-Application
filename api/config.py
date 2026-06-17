"""Payfin — centralized configuration for Vercel serverless deployment."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
  # Core
  SECRET_KEY = os.getenv("SECRET_KEY", "payfin-dev-secret-change-in-production-32chars")
  FLASK_ENV = os.getenv("FLASK_ENV", "development")
  DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
  PORT = int(os.getenv("PORT", "5000"))

  # JWT
  JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "payfin-jwt-dev-change-in-production-32chars")
  JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
  JWT_ALGORITHM = "HS256"

  # PostgreSQL — use pooled URL on Vercel (Neon/Supabase pgbouncer port 6543)
  DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+pg8000://payfin:payfin@localhost:5432/payfin",
  )
  DATABASE_POOL_URL = os.getenv("DATABASE_POOL_URL", DATABASE_URL)

  # Redis / Upstash (rate limiting + optional idempotency cache)
  REDIS_URL = os.getenv("REDIS_URL", "")
  RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", REDIS_URL or "memory://")

  # Branding
  COMPANY_NAME = os.getenv("COMPANY_NAME", "Payfin")
  APP_NAME = os.getenv("APP_NAME", "Payfin")
  UPI_SUFFIX = os.getenv("UPI_SUFFIX", "payfin")

  # CORS
  CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,https://*.vercel.app").split(",")
    if o.strip()
  ]

  # MFA
  MFA_ISSUER = os.getenv("MFA_ISSUER", "Payfin")

  # Webhooks
  WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "payfin-webhook-hmac-secret-change-me")

  # Payment aggregators
  RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
  RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
  CASHFREE_APP_ID = os.getenv("CASHFREE_APP_ID", "")
  CASHFREE_SECRET_KEY = os.getenv("CASHFREE_SECRET_KEY", "")
  STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
  PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "razorpay")  # razorpay | cashfree | stripe | internal

  # External verification
  RAZORPAY_IFSC_API = os.getenv("RAZORPAY_IFSC_API", "https://ifsc.razorpay.com")
  NPCI_VPA_VERIFY_URL = os.getenv("NPCI_VPA_VERIFY_URL", "")

  # Realtime (Pusher / Supabase)
  PUSHER_APP_ID = os.getenv("PUSHER_APP_ID", "")
  PUSHER_KEY = os.getenv("PUSHER_KEY", "")
  PUSHER_SECRET = os.getenv("PUSHER_SECRET", "")
  PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER", "ap2")
  SUPABASE_URL = os.getenv("SUPABASE_URL", "")
  SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

  # Security
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SAMESITE = "Lax"
  SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV", "development") == "production"
  MAX_CONTENT_LENGTH = 1 * 1024 * 1024
  IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))

  # Frontend URL (for redirects, CORS)
  FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
