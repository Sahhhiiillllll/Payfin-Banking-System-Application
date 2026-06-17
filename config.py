"""
Payfin
config.py — Centralized configuration management
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Core Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "payfin-fallback-secret-key-2025")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "payfin-jwt-fallback-2025")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))

    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "payfin.db")

    # Branding
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Payfin")
    APP_NAME = os.getenv("APP_NAME", "Payfin")
    UPI_SUFFIX = os.getenv("UPI_SUFFIX", "payfin")

    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB max request body


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    DEBUG = True


config = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
    "default": DevelopmentConfig,
}
