"""Pusher realtime events for balance/transaction updates."""

from __future__ import annotations

import json
from typing import Any, Optional
from urllib import parse, request as urlrequest

from config import Config


def _pusher_available() -> bool:
  return bool(Config.PUSHER_APP_ID and Config.PUSHER_KEY and Config.PUSHER_SECRET)


def publish_user_event(user_id: int, event: str, data: dict[str, Any]) -> bool:
  if not _pusher_available():
    return False
  channel = f"private-user-{user_id}"
  body = json.dumps({"name": event, "channel": channel, "data": json.dumps(data)}).encode()
  try:
    import hashlib
    import hmac
    import time

    path = f"/apps/{Config.PUSHER_APP_ID}/events"
    query = f"auth_key={Config.PUSHER_KEY}&auth_timestamp={int(time.time())}&auth_version=1.0&body_md5={hashlib.md5(body).hexdigest()}"
    sig = hmac.new(
      Config.PUSHER_SECRET.encode(),
      f"POST\n{path}\n{query}".encode(),
      hashlib.sha256,
    ).hexdigest()
    url = f"https://api-{Config.PUSHER_CLUSTER}.pusher.com{path}?{query}&auth_signature={sig}"
    req = urlrequest.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlrequest.urlopen(req, timeout=5) as resp:
      return resp.status == 200
  except Exception:
    return False


def notify_balance_update(user_id: int, account_id: int, balance: float, reference_id: str) -> None:
  publish_user_event(user_id, "balance.updated", {
    "account_id": account_id,
    "balance": balance,
    "reference_id": reference_id,
  })


def notify_transaction(user_id: int, transaction: dict[str, Any]) -> None:
  publish_user_event(user_id, "transaction.created", transaction)
