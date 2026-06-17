"""DB-backed idempotency for payment endpoints."""

from __future__ import annotations

import functools
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from flask import g, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import Config
from models.security import IdempotencyKey


def _hash_key(raw: str) -> str:
  return hashlib.sha256(raw.encode()).hexdigest()


def require_idempotency(endpoint_name: str) -> Callable:
  """Decorator: Idempotency-Key header required; replays cached response on retry."""

  def decorator(f: Callable) -> Callable:
    @functools.wraps(f)
    def wrapped(user, *args, **kwargs):
      idem_key = request.headers.get("Idempotency-Key", "").strip()
      if not idem_key or len(idem_key) < 8 or len(idem_key) > 128:
        return jsonify({
          "success": False,
          "error": "Idempotency-Key header required (8–128 chars).",
        }), 400

      session: Session = g.db
      body = request.get_json(silent=True) or {}
      request_hash = _hash_key(json.dumps(body, sort_keys=True, default=str))
      key_hash = _hash_key(f"{user['id']}:{idem_key}")

      existing = session.execute(
        select(IdempotencyKey).where(
          IdempotencyKey.user_id == user["id"],
          IdempotencyKey.key_hash == key_hash,
          IdempotencyKey.expires_at > datetime.now(timezone.utc),
        )
      ).scalar_one_or_none()

      if existing:
        if existing.request_hash != request_hash:
          return jsonify({
            "success": False,
            "error": "Idempotency-Key reused with different request body.",
          }), 422
        return jsonify(existing.response_body), existing.response_status

      result = f(user, *args, **kwargs)

      if isinstance(result, tuple):
        response_body, status = result[0].get_json(), result[1]
      else:
        response_body, status = result.get_json(), 200

      record = IdempotencyKey(
        user_id=user["id"],
        key_hash=key_hash,
        endpoint=endpoint_name,
        request_hash=request_hash,
        response_status=status,
        response_body=response_body,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=Config.IDEMPOTENCY_TTL_SECONDS),
      )
      session.add(record)
      session.flush()

      return jsonify(response_body), status

    return wrapped

  return decorator
