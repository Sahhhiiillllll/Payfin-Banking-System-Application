"""Alembic migration environment — Payfin."""

from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# Load .env so DATABASE_URL is available when running locally
load_dotenv()

# Add api/ to sys.path so SQLAlchemy models and config resolve
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "api"))

from config import Config  # noqa: E402
from db import Base  # noqa: E402
import models  # noqa: F401, E402

alembic_config = context.config
if alembic_config.config_file_name is not None:
  fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata

# Use the normalized DATABASE_URL from Config (already has pg8000 injected)
alembic_config.set_main_option("sqlalchemy.url", Config.DATABASE_URL)


def run_migrations_offline() -> None:
  url = alembic_config.get_main_option("sqlalchemy.url")
  context.configure(
    url=url,
    target_metadata=target_metadata,
    literal_binds=True,
    dialect_opts={"paramstyle": "named"},
  )
  with context.begin_transaction():
    context.run_migrations()


def run_migrations_online() -> None:
  connectable = engine_from_config(
    alembic_config.get_section(alembic_config.config_ini_section, {}),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
  )
  with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
      context.run_migrations()


if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()
