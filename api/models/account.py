"""Account models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _utcnow() -> datetime:
  return datetime.now(timezone.utc)


class Account(Base):
  __tablename__ = "accounts"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
  account_no: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
  account_type: Mapped[str] = mapped_column(String(30), default="Savings", nullable=False)
  balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
  is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

  user: Mapped["User"] = relationship("User", back_populates="accounts")
  transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="account")


class LinkedAccount(Base):
  __tablename__ = "linked_accounts"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
  bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
  account_holder: Mapped[str] = mapped_column(String(100), nullable=False)
  account_no: Mapped[str] = mapped_column(String(18), nullable=False)
  ifsc_code: Mapped[str] = mapped_column(String(11), nullable=False)
  account_type: Mapped[str] = mapped_column(String(30), default="Savings", nullable=False)
  is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


from models.user import User  # noqa: E402
from models.transaction import Transaction  # noqa: E402
