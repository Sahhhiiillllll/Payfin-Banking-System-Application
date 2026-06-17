"""Flask application factory — API-only for Vercel serverless."""

from __future__ import annotations

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from db import SessionLocal, engine
from db import Base
from repositories.banking import BankingRepository
from routes import register_routes


def create_app() -> Flask:
  app = Flask(__name__)
  app.config.from_object(Config)
  app.secret_key = Config.SECRET_KEY

  CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}}, supports_credentials=True)

  limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri=Config.RATELIMIT_STORAGE_URI,
  )

  @app.before_request
  def open_db():
    g.db = SessionLocal()
    g.repo = BankingRepository(g.db)

  @app.teardown_request
  def close_db(exc):
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
    try:
      with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("SELECT 1"))
      db_ok = True
    except Exception as exc:
      db_ok = False
      db_err = str(exc)
    else:
      db_err = None

    return jsonify({
      "status": "ok" if db_ok else "degraded",
      "service": Config.APP_NAME,
      "database": "connected" if db_ok else "error",
      "error": db_err,
    }), (200 if db_ok else 503)

  @app.errorhandler(404)
  def not_found(e):
    if request.path.startswith("/api/"):
      return jsonify({"error": "Endpoint not found.", "code": 404}), 404
    return jsonify({"error": "Not found."}), 404

  @app.errorhandler(429)
  def rate_limited(e):
    return jsonify({"error": "Too many requests.", "code": 429}), 429

  @app.errorhandler(500)
  def server_error(e):
    return jsonify({"error": "Internal server error.", "code": 500}), 500

  @app.after_request
  def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if Config.FLASK_ENV == "production":
      response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

  return app


def init_db():
  Base.metadata.create_all(bind=engine)
  from db import SessionLocal
  session = SessionLocal()
  try:
    repo = BankingRepository(session)
    repo.seed_demo_data()
    session.commit()
  finally:
    session.close()
