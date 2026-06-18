"""Flask application factory — API-only for Vercel serverless."""

from __future__ import annotations

import logging

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from db import Base, SessionLocal, engine, health_check
from repositories.banking import BankingRepository
from routes import register_routes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def create_app() -> Flask:
  app = Flask(__name__)
  app.config.from_object(Config)
  app.secret_key = Config.SECRET_KEY

  # CORS — allow configured origins; also allow *.vercel.app pattern
  CORS(
    app,
    resources={r"/api/*": {"origins": Config.CORS_ORIGINS}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
  )

  # Rate limiter — gracefully fall back to in-memory if Redis is unavailable
  _storage = Config.RATELIMIT_STORAGE_URI or "memory://"
  limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri=_storage,
    on_breach=lambda: None,  # don't raise on storage error
  )
  app.extensions["limiter"] = limiter

  @app.before_request
  def open_db():
    g.db = SessionLocal()
    g.repo = BankingRepository(g.db)

  @app.teardown_request
  def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
      if exc:
        db.rollback()
      else:
        try:
          db.commit()
        except Exception:
          db.rollback()
          raise
      db.close()

  register_routes(app)

  @app.route("/api/health", methods=["GET"])
  def health():
    db_ok = health_check()
    return jsonify({
      "status": "ok" if db_ok else "degraded",
      "service": Config.APP_NAME,
      "version": "1.0.0",
      "database": "connected" if db_ok else "unreachable",
      "environment": Config.FLASK_ENV,
    }), (200 if db_ok else 503)

  @app.errorhandler(400)
  def bad_request(e):
    return jsonify({"error": "Bad request.", "code": 400}), 400

  @app.errorhandler(401)
  def unauthorized(e):
    return jsonify({"error": "Unauthorized.", "code": 401}), 401

  @app.errorhandler(403)
  def forbidden(e):
    return jsonify({"error": "Forbidden.", "code": 403}), 403

  @app.errorhandler(404)
  def not_found(e):
    if request.path.startswith("/api/"):
      return jsonify({"error": "Endpoint not found.", "code": 404}), 404
    return jsonify({"error": "Not found."}), 404

  @app.errorhandler(405)
  def method_not_allowed(e):
    return jsonify({"error": "Method not allowed.", "code": 405}), 405

  @app.errorhandler(429)
  def rate_limited(e):
    return jsonify({"error": "Too many requests. Slow down.", "code": 429, "retry_after": 60}), 429

  @app.errorhandler(500)
  def server_error(e):
    log.exception("Unhandled server error: %s", e)
    return jsonify({"error": "Internal server error.", "code": 500}), 500

  @app.after_request
  def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if Config.FLASK_ENV == "production":
      response.headers.setdefault(
        "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
      )
    return response

  return app


def init_db():
  """Create all tables and optionally seed demo data."""
  Base.metadata.create_all(bind=engine)
  session = SessionLocal()
  try:
    repo = BankingRepository(session)
    if hasattr(repo, "seed_demo_data"):
      repo.seed_demo_data()
    session.commit()
  except Exception as e:
    session.rollback()
    log.warning("seed_demo_data failed (non-fatal): %s", e)
  finally:
    session.close()
