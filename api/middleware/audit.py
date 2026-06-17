"""Immutable audit logging."""

from __future__ import annotations

from typing import Any, Optional

from flask import request
from sqlalchemy.orm import Session

from models.security import AuditLog


SENSITIVE_ACTIONS = frozenset({
  "auth.login.success",
  "auth.login.failure",
  "auth.logout",
  "auth.mfa.enabled",
  "auth.mfa.disabled",
  "auth.password.changed",
  "balance.deposit",
  "balance.withdraw",
  "balance.transfer",
  "balance.upi.send",
  "balance.gateway.pay",
  "account.linked.add",
  "account.linked.remove",
  "webhook.received",
  "webhook.signature.invalid",
})


def audit_log(
  session: Session,
  action: str,
  user_id: Optional[int] = None,
  resource_type: Optional[str] = None,
  resource_id: Optional[str] = None,
  metadata: Optional[dict[str, Any]] = None,
) -> None:
  entry = AuditLog(
    user_id=user_id,
    action=action,
    resource_type=resource_type,
    resource_id=resource_id,
    ip_address=request.remote_addr if request else None,
    user_agent=request.headers.get("User-Agent") if request else None,
    metadata_json=metadata or {},
  )
  session.add(entry)
  session.flush()
