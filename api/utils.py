"""Shared validation helpers."""

from __future__ import annotations

import re
from typing import Tuple

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def validate_amount(raw: str) -> Tuple[bool, float, str]:
  raw = str(raw).strip()
  try:
    val = float(raw)
  except (ValueError, TypeError):
    return False, 0.0, "Enter a valid numeric amount."
  if val <= 0:
    return False, 0.0, "Amount must be greater than zero."
  if val > 10_000_000:
    return False, 0.0, "Amount exceeds single-transaction limit of ₹1,00,00,000."
  return True, round(val, 2), ""


def validate_password(pwd: str) -> Tuple[bool, str]:
  if len(pwd) < 8:
    return False, "Password must be at least 8 characters."
  if not re.search(r"[A-Z]", pwd):
    return False, "Password must contain at least one uppercase letter."
  if not re.search(r"[0-9]", pwd):
    return False, "Password must contain at least one digit."
  if not re.search(r"[^A-Za-z0-9]", pwd):
    return False, "Password must contain at least one special character."
  return True, ""


def validate_email(email: str) -> bool:
  return bool(EMAIL_RE.match(email))


def validate_ifsc(ifsc: str) -> bool:
  return bool(IFSC_RE.match(ifsc.upper()))
