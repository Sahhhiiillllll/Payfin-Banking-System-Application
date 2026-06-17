"""HMAC-SHA256 webhook signature verification."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Optional

from flask import Request
from sqlalchemy.orm import Session

from config import Config
from middleware.audit import audit_log
from models.security import WebhookEvent


def verify_hmac_sha256(payload: bytes, signature: str, secret: str) -> bool:
  if not signature or not secret:
    return False
  expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
  provided = signature.replace("sha256=", "").strip()
  return hmac.compare_digest(expected, provided)


def process_webhook(
  session: Session,
  provider: str,
  request: Request,
  event_id: str,
  event_type: str,
  signature_header: str = "X-Payfin-Signature",
) -> tuple[bool, dict[str, Any]]:
  raw = request.get_data()
  sig = request.headers.get(signature_header, "")
  valid = verify_hmac_sha256(raw, sig, Config.WEBHOOK_SECRET)

  payload = json.loads(raw.decode("utf-8")) if raw else {}

  existing = session.query(WebhookEvent).filter_by(event_id=event_id).first()
  if existing:
    return True, {"status": "duplicate", "event_id": event_id}

  event = WebhookEvent(
    provider=provider,
    event_id=event_id,
    event_type=event_type,
    payload=payload,
    signature_valid=valid,
    processed_at=datetime.now(timezone.utc) if valid else None,
  )
  session.add(event)
  session.flush()

  if not valid:
    audit_log(session, "webhook.signature.invalid", metadata={"provider": provider, "event_id": event_id})
    return False, {"error": "Invalid webhook signature."}

  audit_log(session, "webhook.received", metadata={"provider": provider, "event_type": event_type})
  return True, {"status": "accepted", "event_id": event_id}
