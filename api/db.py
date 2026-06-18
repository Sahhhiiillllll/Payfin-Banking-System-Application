"""SQLAlchemy engine + session factory — optimized for Vercel serverless + Neon/Supabase."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from config import Config

Base = declarative_base()

_is_serverless = bool(os.getenv("VERCEL")) or Config.FLASK_ENV == "production"

_engine_kwargs: dict = {
  "echo": Config.DEBUG,
  "pool_pre_ping": True,
}

if _is_serverless:
  # NullPool = no persistent connections across Lambda/Vercel invocations
  _engine_kwargs["poolclass"] = NullPool
else:
  _engine_kwargs.update(
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=20,
  )

# pg8000 does not support connect_args "options" — set statement_timeout via event
engine = create_engine(Config.DATABASE_POOL_URL, **_engine_kwargs)


@event.listens_for(engine, "connect")
def _set_pg_options(dbapi_connection, connection_record):
  """Apply session-level safety settings on each new connection."""
  try:
    cursor = dbapi_connection.cursor()
    cursor.execute("SET statement_timeout = '25s'")
    cursor.execute("SET lock_timeout = '5s'")
    cursor.close()
    dbapi_connection.commit()
  except Exception:
    pass  # Don't break startup if DB isn't ready yet


SessionLocal = sessionmaker(
  bind=engine,
  autocommit=False,
  autoflush=False,
  expire_on_commit=False,
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
  """Context manager providing a transactional DB session."""
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
  """Return a raw session — caller is responsible for commit/close."""
  return SessionLocal()


def health_check() -> bool:
  """Quick connectivity check used by /api/health."""
  try:
    with engine.connect() as conn:
      conn.execute(text("SELECT 1"))
    return True
  except Exception:
    return False
