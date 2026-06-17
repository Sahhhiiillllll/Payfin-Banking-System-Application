"""VPA/UPI lookup — internal registry + optional NPCI verification."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from config import Config
from models.user import UpiHandle, User

VPA_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{2,256}@[a-zA-Z0-9]{2,64}$")


def validate_vpa_format(vpa: str) -> bool:
  return bool(VPA_PATTERN.match(vpa.strip()))


def lookup_vpa(session: Session, vpa: str) -> dict:
  vpa = vpa.strip().lower()
  if not validate_vpa_format(vpa):
    return {"success": False, "error": "Invalid UPI ID format."}

  row = session.execute(
    select(User.id, User.username, User.full_name, UpiHandle.upi_id)
    .join(UpiHandle, UpiHandle.user_id == User.id)
    .where(UpiHandle.upi_id == vpa, UpiHandle.is_active.is_(True), User.is_active.is_(True))
  ).first()

  if row:
    return {
      "success": True,
      "upi_id": row.upi_id,
      "name": row.full_name,
      "verified": True,
      "source": "payfin_registry",
    }

  handle_suffix = vpa.split("@")[-1] if "@" in vpa else ""
  if handle_suffix == Config.UPI_SUFFIX:
    return {"success": False, "error": f"UPI ID '{vpa}' not found."}

  return {
    "success": True,
    "upi_id": vpa,
    "name": "External Payee",
    "verified": False,
    "source": "external_unverified",
  }
