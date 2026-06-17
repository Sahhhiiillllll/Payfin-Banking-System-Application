"""SQLAlchemy engine + session factory optimized for Vercel serverless."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from config import Config

Base = declarative_base()

_is_serverless = Config.FLASK_ENV == "production" or bool(os.getenv("VERCEL"))

_engine_kwargs: dict = {
  "echo": Config.DEBUG,
  "pool_pre_ping": True,
}

if _is_serverless:
  # Serverless: no persistent pool — one connection per invocation
  _engine_kwargs["poolclass"] = NullPool
else:
  _engine_kwargs.update(
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
  )

engine = create_engine(Config.DATABASE_POOL_URL, **_engine_kwargs)

# Neon/Supabase: set statement timeout for serverless safety
@event.listens_for(engine, "connect")
def _set_pg_options(dbapi_connection, connection_record):
  cursor = dbapi_connection.cursor()
  cursor.execute("SET statement_timeout = '25s'")
  cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


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
  """For Flask request-scoped usage via g."""
  return SessionLocal()
