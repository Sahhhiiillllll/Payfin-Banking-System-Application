"""Security, audit, and idempotency models."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


def _utcnow() -> datetime:
  return datetime.now(timezone.utc)


class AuditLog(Base):
  """Append-only immutable audit trail."""

  __tablename__ = "audit_logs"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
  action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
  resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
  resource_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
  ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
  user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
  metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class IdempotencyKey(Base):
  __tablename__ = "idempotency_keys"
  __table_args__ = (UniqueConstraint("user_id", "key_hash", name="uq_idempotency_user_key"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
  key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
  endpoint: Mapped[str] = mapped_column(String(120), nullable=False)
  request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
  response_status: Mapped[int] = mapped_column(Integer, nullable=False)
  response_body: Mapped[dict] = mapped_column(JSONB, nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
  expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WebhookEvent(Base):
  __tablename__ = "webhook_events"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  provider: Mapped[str] = mapped_column(String(30), nullable=False)
  event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
  event_type: Mapped[str] = mapped_column(String(80), nullable=False)
  payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
  signature_valid: Mapped[bool] = mapped_column(default=False, nullable=False)
  processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
