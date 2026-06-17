"""Webhook ingestion routes."""

import uuid

from flask import Blueprint, g, jsonify, request

from services.webhook_service import process_webhook

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")


@webhooks_bp.route("/ledger", methods=["POST"])
def ledger_webhook():
  event_id = request.headers.get("X-Payfin-Event-Id") or str(uuid.uuid4())
  event_type = request.headers.get("X-Payfin-Event-Type") or "ledger.update"
  ok, result = process_webhook(g.db, "payfin", request, event_id, event_type)
  return jsonify(result), (200 if ok else 401)


@webhooks_bp.route("/razorpay", methods=["POST"])
def razorpay_webhook():
  from services.payment_aggregator import PaymentAggregator

  sig = request.headers.get("X-Razorpay-Signature", "")
  if not PaymentAggregator.verify_razorpay_webhook(request.get_data(), sig):
    return jsonify({"error": "Invalid signature."}), 401

  payload = request.get_json(silent=True) or {}
  event_id = payload.get("event", str(uuid.uuid4()))
  ok, result = process_webhook(g.db, "razorpay", request, event_id, payload.get("event", "unknown"))
  return jsonify(result), (200 if ok else 401)
