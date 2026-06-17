"""User and authentication models."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _utcnow() -> datetime:
  return datetime.now(timezone.utc)


class User(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
  full_name: Mapped[str] = mapped_column(String(100), nullable=False)
  email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
  phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
  pwd_hash: Mapped[str] = mapped_column(Text, nullable=False)
  is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
  mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
  last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

  accounts: Mapped[list["Account"]] = relationship("Account", back_populates="user")
  upi_handle: Mapped["UpiHandle | None"] = relationship("UpiHandle", back_populates="user", uselist=False)


class UpiHandle(Base):
  __tablename__ = "upi_handles"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
  upi_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
  is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

  user: Mapped["User"] = relationship("User", back_populates="upi_handle")


class SessionRecord(Base):
  __tablename__ = "sessions"

  id: Mapped[str] = mapped_column(String(36), primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
  expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
  user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
  is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


from models.account import Account  # noqa: E402
