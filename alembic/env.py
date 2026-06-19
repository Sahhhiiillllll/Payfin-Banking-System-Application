"""Alembic migration environment — Payfin."""

from logging.config import fileConfig
import os
import sys
import ssl

from alembic import context
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "api"))

from config import Config  # noqa: E402
from db import Base  # noqa: E402
import models  # noqa: F401, E402

alembic_config = context.config
if alembic_config.config_file_name is not None:
  fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


def _make_engine():
  """Build engine with SSL via connect_args (works with all pg8000 versions)."""
  url = Config.DATABASE_URL

  # Strip ALL SSL/channel params from URL — we pass SSL via connect_args instead
  if "?" in url:
    base, query = url.split("?", 1)
    blocked = {"sslmode", "ssl", "channel_binding", "options",
               "sslcert", "sslkey", "sslrootcert", "sslpassword"}
    kept = [p for p in query.split("&")
            if p and p.split("=", 1)[0].lower() not in blocked]
    url = base + ("?" + "&".join(kept) if kept else "")

  # Use SSL context via connect_args — works with old and new pg8000
  connect_args = {}
  is_cloud = any(h in url for h in ["neon.tech", "supabase", "amazonaws", "rds."])
  if is_cloud:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connect_args["ssl_context"] = ssl_ctx

  return create_engine(url, connect_args=connect_args, poolclass=NullPool)


def run_migrations_offline() -> None:
  url = Config.DATABASE_URL
  context.configure(
    url=url,
    target_metadata=target_metadata,
    literal_binds=True,
    dialect_opts={"paramstyle": "named"},
  )
  with context.begin_transaction():
    context.run_migrations()


def run_migrations_online() -> None:
  connectable = _make_engine()
  with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
      context.run_migrations()


if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()
