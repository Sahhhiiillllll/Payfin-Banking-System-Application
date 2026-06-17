"""Live IFSC verification via Razorpay public API with regex fallback."""

from __future__ import annotations

import json
import re
from urllib import request as urlrequest

from config import Config

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def validate_ifsc_format(ifsc: str) -> bool:
  return bool(IFSC_PATTERN.match(ifsc.upper()))


def verify_ifsc(ifsc: str) -> dict:
  ifsc = ifsc.upper().strip()
  if not validate_ifsc_format(ifsc):
    return {"valid": False, "error": "Invalid IFSC format.", "ifsc": ifsc}

  url = f"{Config.RAZORPAY_IFSC_API}/{ifsc}"
  try:
    req = urlrequest.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urlrequest.urlopen(req, timeout=10) as resp:
      data = json.loads(resp.read().decode())
    return {
      "valid": True,
      "ifsc": ifsc,
      "bank": data.get("BANK"),
      "branch": data.get("BRANCH"),
      "city": data.get("CITY"),
      "state": data.get("STATE"),
      "address": data.get("ADDRESS"),
      "micr": data.get("MICR"),
    }
  except urlrequest.HTTPError as exc:
    if exc.code == 404:
      return {"valid": False, "error": "IFSC not found in RBI registry.", "ifsc": ifsc}
    return {"valid": False, "error": f"IFSC lookup failed: HTTP {exc.code}", "ifsc": ifsc}
  except Exception as exc:
    return {"valid": False, "error": str(exc), "ifsc": ifsc}
