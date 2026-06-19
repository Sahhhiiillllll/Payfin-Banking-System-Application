"""Transaction models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _utcnow() -> datetime:
  return datetime.now(timezone.utc)


class Transaction(Base):
  __tablename__ = "transactions"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
  txn_type: Mapped[str] = mapped_column(String(10), nullable=False)
  txn_category: Mapped[str] = mapped_column(String(20), default="BANK", nullable=False)
  amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
  balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
  description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  counterparty: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
  reference_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
  status: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

  account: Mapped["Account"] = relationship("Account", back_populates="transactions")


class GatewayTransaction(Base):
  __tablename__ = "gateway_transactions"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
  account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
  payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
  amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
  status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
  reference_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
  external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
  merchant: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
  description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  card_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
  upi_vpa: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


from models.account import Account  # noqa: E402
