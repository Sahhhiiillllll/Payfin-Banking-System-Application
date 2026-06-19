"""SQLAlchemy engine + session — optimized for Vercel serverless + Neon/Supabase."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

Base = declarative_base()

# ── resolve DATABASE_URL fresh at module load (after Vercel injects env vars) ──
def _get_url() -> str:
  from config import _get_pool_url
  url = _get_pool_url()
  if "localhost" in url and os.environ.get("VERCEL"):
    print("ERROR: DATABASE_URL resolves to localhost on Vercel — check env vars!", file=sys.stderr)
  return url


_db_url = _get_url()
_is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV")) or \
                 os.environ.get("FLASK_ENV") == "production"

_engine_kwargs: dict = {
  "echo": os.environ.get("FLASK_DEBUG", "False").lower() == "true",
  "pool_pre_ping": True,
}

if _is_serverless:
  _engine_kwargs["poolclass"] = NullPool
else:
  _engine_kwargs.update(
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=20,
  )

engine = create_engine(_db_url, **_engine_kwargs)


@event.listens_for(engine, "connect")
def _set_pg_options(dbapi_connection, connection_record):
  try:
    cursor = dbapi_connection.cursor()
    cursor.execute("SET statement_timeout = '25s'")
    cursor.execute("SET lock_timeout = '5s'")
    cursor.close()
    dbapi_connection.commit()
  except Exception:
    pass


SessionLocal = sessionmaker(
  bind=engine,
  autocommit=False,
  autoflush=False,
  expire_on_commit=False,
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
  session = SessionLocal()
  try:
    yield session
    session.commit()
  except Exception:
    session.rollback()
    raise
  finally:
    session.close()


def get_db_session() -> Session:
  return SessionLocal()


def health_check() -> bool:
  try:
    with engine.connect() as conn:
      conn.execute(text("SELECT 1"))
    return True
  except Exception:
    return False
