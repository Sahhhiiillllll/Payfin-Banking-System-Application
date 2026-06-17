"""TOTP-based MFA service."""

from __future__ import annotations

import base64
import io
from typing import Optional

import pyotp
import qrcode
from sqlalchemy.orm import Session

from config import Config
from middleware.audit import audit_log
from models.user import User


def generate_totp_secret() -> str:
  return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
  return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=Config.MFA_ISSUER)


def generate_qr_base64(secret: str, email: str) -> str:
  uri = get_totp_uri(secret, email)
  img = qrcode.make(uri)
  buf = io.BytesIO()
  img.save(buf, format="PNG")
  return base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
  if not secret or not code:
    return False
  totp = pyotp.TOTP(secret)
  return totp.verify(code, valid_window=1)


def enable_mfa(session: Session, user_id: int, secret: str, code: str) -> dict:
  user = session.get(User, user_id)
  if not user:
    return {"success": False, "error": "User not found."}
  if not verify_totp(secret, code):
    return {"success": False, "error": "Invalid TOTP code."}
  user.totp_secret = secret
  user.mfa_enabled = True
  session.flush()
  audit_log(session, "auth.mfa.enabled", user_id=user_id)
  return {"success": True, "message": "MFA enabled."}


def disable_mfa(session: Session, user_id: int, code: str) -> dict:
  user = session.get(User, user_id)
  if not user or not user.totp_secret:
    return {"success": False, "error": "MFA not configured."}
  if not verify_totp(user.totp_secret, code):
    return {"success": False, "error": "Invalid TOTP code."}
  user.totp_secret = None
  user.mfa_enabled = False
  session.flush()
  audit_log(session, "auth.mfa.disabled", user_id=user_id)
  return {"success": True, "message": "MFA disabled."}


def setup_mfa(session: Session, user_id: int) -> dict:
  user = session.get(User, user_id)
  if not user:
    return {"success": False, "error": "User not found."}
  secret = generate_totp_secret()
  return {
    "success": True,
    "secret": secret,
    "qr_base64": generate_qr_base64(secret, user.email),
    "otpauth_uri": get_totp_uri(secret, user.email),
  }
