"""Payment aggregator abstraction — Razorpay, Cashfree, Stripe, internal fallback."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from decimal import Decimal
from typing import Any, Optional
from urllib import request as urlrequest

from config import Config


class PaymentAggregator:
  def __init__(self, provider: Optional[str] = None):
    self.provider = (provider or Config.PAYMENT_PROVIDER).lower()

  def create_payment(
    self,
    amount: Decimal,
    currency: str,
    reference_id: str,
    customer: dict[str, Any],
    method: str,
    metadata: Optional[dict] = None,
  ) -> dict[str, Any]:
    if self.provider == "razorpay" and Config.RAZORPAY_KEY_ID:
      return self._razorpay_create(amount, currency, reference_id, customer, method, metadata)
    if self.provider == "cashfree" and Config.CASHFREE_APP_ID:
      return self._cashfree_create(amount, currency, reference_id, customer, method, metadata)
    if self.provider == "stripe" and Config.STRIPE_SECRET_KEY:
      return self._stripe_create(amount, currency, reference_id, customer, method, metadata)
    return self._internal_create(amount, reference_id, method)

  def _internal_create(self, amount: Decimal, reference_id: str, method: str) -> dict:
    return {
      "success": True,
      "provider": "internal",
      "external_id": f"INT_{reference_id}",
      "status": "SUCCESS",
      "amount": float(amount),
      "method": method,
    }

  def _razorpay_create(
    self, amount, currency, reference_id, customer, method, metadata
  ) -> dict:
    payload = {
      "amount": int(amount * 100),
      "currency": currency,
      "receipt": reference_id,
      "notes": metadata or {},
    }
    try:
      data = json.dumps(payload).encode()
      req = urlrequest.Request(
        "https://api.razorpay.com/v1/orders",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
      )
      import base64

      creds = base64.b64encode(
        f"{Config.RAZORPAY_KEY_ID}:{Config.RAZORPAY_KEY_SECRET}".encode()
      ).decode()
      req.add_header("Authorization", f"Basic {creds}")
      with urlrequest.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode())
      return {
        "success": True,
        "provider": "razorpay",
        "external_id": body.get("id"),
        "status": body.get("status", "created").upper(),
        "amount": float(amount),
        "method": method,
        "raw": body,
      }
    except Exception as exc:
      return {"success": False, "provider": "razorpay", "error": str(exc)}

  def _cashfree_create(self, amount, currency, reference_id, customer, method, metadata) -> dict:
    payload = {
      "order_id": reference_id,
      "order_amount": float(amount),
      "order_currency": currency,
      "customer_details": customer,
    }
    try:
      data = json.dumps(payload).encode()
      req = urlrequest.Request(
        "https://api.cashfree.com/pg/orders",
        data=data,
        headers={
          "Content-Type": "application/json",
          "x-client-id": Config.CASHFREE_APP_ID,
          "x-client-secret": Config.CASHFREE_SECRET_KEY,
          "x-api-version": "2023-08-01",
        },
        method="POST",
      )
      with urlrequest.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode())
      return {
        "success": True,
        "provider": "cashfree",
        "external_id": body.get("cf_order_id") or body.get("order_id"),
        "status": str(body.get("order_status", "ACTIVE")).upper(),
        "amount": float(amount),
        "method": method,
        "raw": body,
      }
    except Exception as exc:
      return {"success": False, "provider": "cashfree", "error": str(exc)}

  def _stripe_create(self, amount, currency, reference_id, customer, method, metadata) -> dict:
    try:
      import stripe

      stripe.api_key = Config.STRIPE_SECRET_KEY
      intent = stripe.PaymentIntent.create(
        amount=int(amount * 100),
        currency=currency.lower(),
        metadata={"reference_id": reference_id, **(metadata or {})},
      )
      return {
        "success": True,
        "provider": "stripe",
        "external_id": intent.id,
        "status": intent.status.upper(),
        "amount": float(amount),
        "method": method,
        "client_secret": intent.client_secret,
      }
    except Exception as exc:
      return {"success": False, "provider": "stripe", "error": str(exc)}

  @staticmethod
  def verify_razorpay_webhook(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
      Config.RAZORPAY_KEY_SECRET.encode(),
      payload,
      hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
