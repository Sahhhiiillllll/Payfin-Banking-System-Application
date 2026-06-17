"""PostgreSQL banking repository — ACID transactions via SQLAlchemy."""

from __future__ import annotations

import random
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import bcrypt
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from config import Config
from middleware.audit import audit_log
from models.account import Account, LinkedAccount
from models.transaction import GatewayTransaction, Transaction
from models.user import UpiHandle, User
from services.payment_aggregator import PaymentAggregator
from services.realtime_service import notify_balance_update, notify_transaction


class BankingRepository:
  def __init__(self, session: Session):
    self.session = session

  @staticmethod
  def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

  @staticmethod
  def _check_password(password: str, pwd_hash: str) -> bool:
    try:
      return bcrypt.checkpw(password.encode(), pwd_hash.encode())
    except Exception:
      return False

  @staticmethod
  def _gen_account_no() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(12))

  @staticmethod
  def _gen_reference_id() -> str:
    return "VE" + secrets.token_hex(8).upper()

  @staticmethod
  def _gen_upi_id(username: str) -> str:
    clean = "".join(c.lower() for c in username if c.isalnum())
    return f"{clean}@{Config.UPI_SUFFIX}"

  def _user_dict(self, user: User) -> dict[str, Any]:
    upi = user.upi_handle.upi_id if user.upi_handle else None
    return {
      "id": user.id,
      "username": user.username,
      "full_name": user.full_name,
      "email": user.email,
      "phone": user.phone,
      "is_active": user.is_active,
      "mfa_enabled": user.mfa_enabled,
      "created_at": user.created_at.isoformat() if user.created_at else None,
      "last_login": user.last_login.isoformat() if user.last_login else None,
      "upi_id": upi,
    }

  def _account_dict(self, acc: Account) -> dict[str, Any]:
    return {
      "id": acc.id,
      "user_id": acc.user_id,
      "account_no": acc.account_no,
      "account_type": acc.account_type,
      "balance": float(acc.balance),
      "is_primary": acc.is_primary,
      "created_at": acc.created_at.isoformat() if acc.created_at else None,
    }

  def _txn_dict(self, txn: Transaction, account_no: str | None = None) -> dict[str, Any]:
    d = {
      "id": txn.id,
      "account_id": txn.account_id,
      "txn_type": txn.txn_type,
      "txn_category": txn.txn_category,
      "amount": float(txn.amount),
      "balance_after": float(txn.balance_after),
      "description": txn.description,
      "counterparty": txn.counterparty,
      "reference_id": txn.reference_id,
      "status": txn.status,
      "created_at": txn.created_at.isoformat() if txn.created_at else None,
    }
    if account_no:
      d["account_no"] = account_no
    return d

  def register_user(
    self, username: str, full_name: str, email: str, password: str,
    phone: str | None = None, account_type: str = "Savings",
  ) -> dict:
    try:
      user = User(
        username=username,
        full_name=full_name,
        email=email.lower(),
        phone=phone,
        pwd_hash=self._hash_password(password),
      )
      self.session.add(user)
      self.session.flush()

      acc = Account(
        user_id=user.id,
        account_no=self._gen_account_no(),
        account_type=account_type,
        balance=Decimal("0.00"),
        is_primary=True,
      )
      upi = UpiHandle(user_id=user.id, upi_id=self._gen_upi_id(username))
      self.session.add_all([acc, upi])
      self.session.flush()
      audit_log(self.session, "auth.register", user_id=user.id)
      return {"success": True, "account_no": acc.account_no, "upi_id": upi.upi_id}
    except IntegrityError as exc:
      self.session.rollback()
      msg = str(exc.orig).lower()
      if "username" in msg:
        return {"success": False, "error": "Username already taken."}
      if "email" in msg:
        return {"success": False, "error": "Email already registered."}
      return {"success": False, "error": "Registration failed."}

  def authenticate_user(
    self, username: str, password: str, ip_address: str | None = None, user_agent: str | None = None,
  ) -> Optional[dict]:
    user = self.session.execute(
      select(User).options(joinedload(User.upi_handle)).where(
        func.lower(User.username) == username.lower()
      )
    ).scalar_one_or_none()

    if not user or not user.is_active:
      audit_log(self.session, "auth.login.failure", metadata={"username": username, "reason": "invalid"})
      return None
    if not self._check_password(password, user.pwd_hash):
      audit_log(self.session, "auth.login.failure", user_id=user.id, metadata={"reason": "bad_password"})
      return None

    user.last_login = datetime.now(timezone.utc)
    self.session.flush()
    audit_log(self.session, "auth.login.success", user_id=user.id, metadata={"ip": ip_address})
    return self._user_dict(user)

  def get_user_by_id(self, user_id: int) -> Optional[dict]:
    user = self.session.execute(
      select(User).options(joinedload(User.upi_handle)).where(User.id == user_id)
    ).scalar_one_or_none()
    return self._user_dict(user) if user else None

  def get_user_by_upi(self, upi_id: str) -> Optional[dict]:
    row = self.session.execute(
      select(User).join(UpiHandle).where(UpiHandle.upi_id == upi_id.lower(), UpiHandle.is_active.is_(True))
    ).scalar_one_or_none()
    if not row:
      return None
    return {"id": row.id, "username": row.username, "full_name": row.full_name}

  def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
    user = self.session.get(User, user_id)
    if not user:
      return {"success": False, "error": "User not found."}
    if not self._check_password(old_password, user.pwd_hash):
      return {"success": False, "error": "Current password is incorrect."}
    user.pwd_hash = self._hash_password(new_password)
    self.session.flush()
    audit_log(self.session, "auth.password.changed", user_id=user_id)
    return {"success": True}

  def update_profile(self, user_id: int, full_name: str, phone: str | None) -> dict:
    user = self.session.get(User, user_id)
    if not user:
      return {"success": False, "error": "User not found."}
    user.full_name = full_name
    user.phone = phone
    self.session.flush()
    return {"success": True}

  def get_user_accounts(self, user_id: int) -> list[dict]:
    rows = self.session.execute(
      select(Account).where(Account.user_id == user_id).order_by(Account.is_primary.desc(), Account.id)
    ).scalars().all()
    return [self._account_dict(a) for a in rows]

  def get_account_by_id(self, account_id: int) -> Optional[dict]:
    acc = self.session.get(Account, account_id)
    return self._account_dict(acc) if acc else None

  def get_account_by_no(self, account_no: str) -> Optional[dict]:
    acc = self.session.execute(select(Account).where(Account.account_no == account_no)).scalar_one_or_none()
    return self._account_dict(acc) if acc else None

  def add_account(self, user_id: int, account_type: str = "Savings") -> dict:
    acc = Account(user_id=user_id, account_no=self._gen_account_no(), account_type=account_type)
    self.session.add(acc)
    self.session.flush()
    return {"success": True, "account_no": acc.account_no}

  def deposit(self, account_id: int, amount: float, description: str = "Deposit", category: str = "BANK") -> dict:
    ref = self._gen_reference_id()
    acc = self.session.get(Account, account_id, with_for_update=True)
    if not acc:
      return {"success": False, "error": "Account not found."}
    amt = Decimal(str(amount)).quantize(Decimal("0.01"))
    new_balance = (acc.balance + amt).quantize(Decimal("0.01"))
    acc.balance = new_balance
    txn = Transaction(
      account_id=account_id, txn_type="CREDIT", txn_category=category,
      amount=amt, balance_after=new_balance, description=description, reference_id=ref,
    )
    self.session.add(txn)
    self.session.flush()
    audit_log(self.session, "balance.deposit", user_id=acc.user_id, resource_id=ref, metadata={"amount": float(amt)})
    notify_balance_update(acc.user_id, account_id, float(new_balance), ref)
    notify_transaction(acc.user_id, self._txn_dict(txn))
    return {"success": True, "new_balance": float(new_balance), "reference_id": ref}

  def withdraw(self, account_id: int, amount: float, description: str = "Withdrawal", category: str = "BANK") -> dict:
    ref = self._gen_reference_id()
    acc = self.session.get(Account, account_id, with_for_update=True)
    if not acc:
      return {"success": False, "error": "Account not found."}
    amt = Decimal(str(amount)).quantize(Decimal("0.01"))
    if acc.balance < amt:
      return {"success": False, "error": "Insufficient funds."}
    new_balance = (acc.balance - amt).quantize(Decimal("0.01"))
    acc.balance = new_balance
    txn = Transaction(
      account_id=account_id, txn_type="DEBIT", txn_category=category,
      amount=amt, balance_after=new_balance, description=description, reference_id=ref,
    )
    self.session.add(txn)
    self.session.flush()
    audit_log(self.session, "balance.withdraw", user_id=acc.user_id, resource_id=ref, metadata={"amount": float(amt)})
    notify_balance_update(acc.user_id, account_id, float(new_balance), ref)
    notify_transaction(acc.user_id, self._txn_dict(txn))
    return {"success": True, "new_balance": float(new_balance), "reference_id": ref}

  def transfer(self, from_account_id: int, to_account_no: str, amount: float, note: str = "", category: str = "TRANSFER") -> dict:
    ref = self._gen_reference_id()
    src = self.session.get(Account, from_account_id, with_for_update=True)
    dst = self.session.execute(
      select(Account).where(Account.account_no == to_account_no).with_for_update()
    ).scalar_one_or_none()

    if not src:
      return {"success": False, "error": "Source account not found."}
    if not dst:
      return {"success": False, "error": f"Destination account '{to_account_no}' not found."}
    if src.id == dst.id:
      return {"success": False, "error": "Cannot transfer to the same account."}

    amt = Decimal(str(amount)).quantize(Decimal("0.01"))
    if src.balance < amt:
      return {"success": False, "error": "Insufficient funds for this transfer."}

    src_new = (src.balance - amt).quantize(Decimal("0.01"))
    dst_new = (dst.balance + amt).quantize(Decimal("0.01"))
    src.balance = src_new
    dst.balance = dst_new

    desc_src = f"Transfer to ****{to_account_no[-4:]}. {note}".strip(". ")
    desc_dst = f"Transfer from ****{src.account_no[-4:]}. {note}".strip(". ")

    self.session.add_all([
      Transaction(account_id=src.id, txn_type="DEBIT", txn_category=category, amount=amt,
                  balance_after=src_new, description=desc_src, counterparty=to_account_no, reference_id=ref),
      Transaction(account_id=dst.id, txn_type="CREDIT", txn_category=category, amount=amt,
                  balance_after=dst_new, description=desc_dst, counterparty=src.account_no, reference_id=ref + "R"),
    ])
    self.session.flush()
    audit_log(self.session, "balance.transfer", user_id=src.user_id, resource_id=ref, metadata={"amount": float(amt)})
    notify_balance_update(src.user_id, src.id, float(src_new), ref)
    notify_balance_update(dst.user_id, dst.id, float(dst_new), ref + "R")
    return {"success": True, "new_balance": float(src_new), "reference_id": ref}

  def upi_transfer(self, from_account_id: int, to_upi_id: str, amount: float, note: str = "") -> dict:
    dst_user = self.get_user_by_upi(to_upi_id)
    if not dst_user:
      return {"success": False, "error": f"UPI ID '{to_upi_id}' not found."}
    dst_accounts = self.get_user_accounts(dst_user["id"])
    if not dst_accounts:
      return {"success": False, "error": "Recipient has no active account."}
    dst_account = next((a for a in dst_accounts if a["is_primary"]), dst_accounts[0])
    result = self.transfer(from_account_id, dst_account["account_no"], amount, note=note or f"UPI to {to_upi_id}", category="UPI")
    if result.get("success"):
      acc = self.session.get(Account, from_account_id)
      if acc:
        audit_log(self.session, "balance.upi.send", user_id=acc.user_id, resource_id=result["reference_id"])
    return result

  def get_transactions(self, account_id: int, limit: int = 100, category: str | None = None) -> list[dict]:
    q = select(Transaction).where(Transaction.account_id == account_id)
    if category:
      q = q.where(Transaction.txn_category == category)
    q = q.order_by(Transaction.created_at.desc()).limit(limit)
    return [self._txn_dict(t) for t in self.session.execute(q).scalars().all()]

  def get_all_transactions(self, user_id: int, limit: int = 200) -> list[dict]:
    rows = self.session.execute(
      select(Transaction, Account.account_no)
      .join(Account, Account.id == Transaction.account_id)
      .where(Account.user_id == user_id)
      .order_by(Transaction.created_at.desc())
      .limit(limit)
    ).all()
    return [self._txn_dict(t, account_no=no) for t, no in rows]

  def get_transactions_for_statement(self, user_id: int, month: int, year: int) -> list[dict]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    rows = self.session.execute(
      select(Transaction, Account)
      .join(Account, Account.id == Transaction.account_id)
      .where(Account.user_id == user_id, Transaction.created_at >= start, Transaction.created_at < end)
      .order_by(Transaction.created_at)
    ).all()
    return [self._txn_dict(t, account_no=acc.account_no) for t, acc in rows]

  def add_linked_account(self, user_id: int, bank_name: str, account_holder: str,
                         account_no: str, ifsc_code: str, account_type: str = "Savings", verified: bool = False) -> dict:
    count = self.session.execute(
      select(func.count()).select_from(LinkedAccount).where(LinkedAccount.user_id == user_id)
    ).scalar() or 0
    if count >= 5:
      return {"success": False, "error": "Maximum 5 linked accounts allowed."}
    existing = self.session.execute(
      select(LinkedAccount).where(LinkedAccount.user_id == user_id, LinkedAccount.account_no == account_no)
    ).scalar_one_or_none()
    if existing:
      return {"success": False, "error": "This account is already linked."}

    linked = LinkedAccount(
      user_id=user_id, bank_name=bank_name, account_holder=account_holder,
      account_no=account_no, ifsc_code=ifsc_code.upper(), account_type=account_type,
      is_verified=verified, is_primary=(count == 0),
    )
    self.session.add(linked)
    self.session.flush()
    audit_log(self.session, "account.linked.add", user_id=user_id, resource_id=str(linked.id))
    return {"success": True, "message": "Bank account linked successfully."}

  def get_linked_accounts(self, user_id: int) -> list[dict]:
    rows = self.session.execute(
      select(LinkedAccount).where(LinkedAccount.user_id == user_id).order_by(LinkedAccount.is_primary.desc())
    ).scalars().all()
    return [{
      "id": r.id, "bank_name": r.bank_name, "account_holder": r.account_holder,
      "account_no": r.account_no, "ifsc_code": r.ifsc_code, "account_type": r.account_type,
      "is_verified": r.is_verified, "is_primary": r.is_primary,
      "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]

  def remove_linked_account(self, user_id: int, linked_id: int) -> dict:
    row = self.session.execute(
      select(LinkedAccount).where(LinkedAccount.id == linked_id, LinkedAccount.user_id == user_id)
    ).scalar_one_or_none()
    if row:
      self.session.delete(row)
      audit_log(self.session, "account.linked.remove", user_id=user_id, resource_id=str(linked_id))
    return {"success": True}

  def process_payment(
    self, user_id: int, account_id: int, payment_method: str, amount: float,
    merchant: str, description: str, card_last4: str | None = None, upi_vpa: str | None = None,
  ) -> dict:
    ref = self._gen_reference_id()
    acc = self.session.get(Account, account_id, with_for_update=True)
    if not acc or acc.user_id != user_id:
      return {"success": False, "error": "Account not found."}

    amt = Decimal(str(amount)).quantize(Decimal("0.01"))
    if acc.balance < amt:
      return {"success": False, "error": "Insufficient balance for this payment."}

    aggregator = PaymentAggregator()
    user = self.get_user_by_id(user_id) or {}
    ext = aggregator.create_payment(
      amt, "INR", ref,
      {"customer_id": str(user_id), "customer_email": user.get("email", "")},
      payment_method,
      {"merchant": merchant},
    )

    gw = GatewayTransaction(
      user_id=user_id, account_id=account_id, payment_method=payment_method,
      amount=amt, status="PENDING", reference_id=ref, external_id=ext.get("external_id"),
      merchant=merchant, description=description, card_last4=card_last4, upi_vpa=upi_vpa,
    )
    self.session.add(gw)

    if not ext.get("success", True):
      gw.status = "FAILED"
      self.session.flush()
      return {"success": False, "error": ext.get("error", "Payment provider error.")}

    new_balance = (acc.balance - amt).quantize(Decimal("0.01"))
    acc.balance = new_balance
    gw.status = "SUCCESS"
    desc = f"Payment to {merchant} via {payment_method}"
    txn = Transaction(
      account_id=account_id, txn_type="DEBIT", txn_category="PAYMENT",
      amount=amt, balance_after=new_balance, description=desc, reference_id=ref,
    )
    self.session.add(txn)
    self.session.flush()
    audit_log(self.session, "balance.gateway.pay", user_id=user_id, resource_id=ref, metadata={"amount": float(amt)})
    notify_balance_update(user_id, account_id, float(new_balance), ref)
    notify_transaction(user_id, self._txn_dict(txn))
    return {"success": True, "reference_id": ref, "new_balance": float(new_balance), "provider": ext.get("provider")}

  def get_gateway_transactions(self, user_id: int, limit: int = 50) -> list[dict]:
    rows = self.session.execute(
      select(GatewayTransaction).where(GatewayTransaction.user_id == user_id)
      .order_by(GatewayTransaction.created_at.desc()).limit(limit)
    ).scalars().all()
    return [{
      "id": r.id, "payment_method": r.payment_method, "amount": float(r.amount),
      "status": r.status, "reference_id": r.reference_id, "merchant": r.merchant,
      "description": r.description, "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]

  def get_dashboard_stats(self, user_id: int) -> dict:
    accounts = self.get_user_accounts(user_id)
    total_balance = sum(a["balance"] for a in accounts)
    since = datetime.now(timezone.utc) - timedelta(days=30)

    rows = self.session.execute(
      select(Transaction.txn_type, func.sum(Transaction.amount))
      .join(Account, Account.id == Transaction.account_id)
      .where(Account.user_id == user_id, Transaction.created_at >= since)
      .group_by(Transaction.txn_type)
    ).all()

    credits = debits = 0.0
    for txn_type, total in rows:
      if txn_type == "CREDIT":
        credits = float(total or 0)
      else:
        debits = float(total or 0)

    txn_count = self.session.execute(
      select(func.count()).select_from(Transaction)
      .join(Account, Account.id == Transaction.account_id)
      .where(Account.user_id == user_id, Transaction.created_at >= since)
    ).scalar() or 0

    user = self.get_user_by_id(user_id)
    return {
      "total_balance": total_balance,
      "monthly_credits": credits,
      "monthly_debits": debits,
      "txn_count_30d": txn_count,
      "account_count": len(accounts),
      "upi_id": user.get("upi_id") if user else None,
    }

  def seed_demo_data(self) -> None:
    existing = self.session.execute(
      select(User).where(func.lower(User.username) == "demo")
    ).scalar_one_or_none()
    if existing:
      return

    result = self.register_user(
      username="demo", full_name="Demo User", email="demo@payfin.fin",
      password="Demo@12345", phone="+91 98765 43210", account_type="Premium Savings",
    )
    if not result.get("success"):
      return

    acc = self.get_account_by_no(result["account_no"])
    if not acc:
      return

    for amount in [50000.0, 75000.0]:
      self.deposit(acc["id"], amount, "Seed balance")

    self.add_linked_account(
      acc["user_id"], "State Bank of India", "Demo User",
      "123456789012", "SBIN0001234", verified=True,
    )
    self.session.commit()
