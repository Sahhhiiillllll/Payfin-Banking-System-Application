"""JWT authentication middleware."""

from __future__ import annotations

import functools
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import jwt
from flask import g, jsonify, request

from config import Config
from repositories.banking import BankingRepository


def create_jwt(user_id: int, username: str, mfa_verified: bool = False) -> str:
  payload = {
    "user_id": user_id,
    "username": username,
    "mfa_verified": mfa_verified,
    "iat": datetime.now(timezone.utc),
    "exp": datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRY_HOURS),
    "jti": str(uuid.uuid4()),
  }
  return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[dict]:
  try:
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
  except jwt.PyJWTError:
    return None


def get_token_from_request() -> Optional[str]:
  auth = request.headers.get("Authorization", "")
  if auth.startswith("Bearer "):
    return auth[7:]
  return request.cookies.get("ve_token")


def get_current_user(repo: BankingRepository) -> Optional[dict[str, Any]]:
  token = get_token_from_request()
  if not token:
    return None
  payload = decode_jwt(token)
  if not payload:
    return None
  user = repo.get_user_by_id(payload["user_id"])
  if not user or not user.get("is_active"):
    return None
  user["mfa_verified"] = payload.get("mfa_verified", False)
  return user


def api_login_required(f: Callable) -> Callable:
  @functools.wraps(f)
  def decorated(*args, **kwargs):
    repo: BankingRepository = g.repo
    user = get_current_user(repo)
    if not user:
      return jsonify({"error": "Authentication required.", "code": 401}), 401
    if user.get("mfa_enabled") and not user.get("mfa_verified"):
      return jsonify({"error": "MFA verification required.", "code": 403, "mfa_required": True}), 403
    return f(user, *args, **kwargs)

  return decorated


def api_mfa_pending_ok(f: Callable) -> Callable:
  """Allow routes during MFA challenge (login step 2)."""

  @functools.wraps(f)
  def decorated(*args, **kwargs):
    repo: BankingRepository = g.repo
    user = get_current_user(repo)
    if not user:
      return jsonify({"error": "Authentication required.", "code": 401}), 401
    return f(user, *args, **kwargs)

  return decorated
