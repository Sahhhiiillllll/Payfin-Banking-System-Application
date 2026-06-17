"""Payment gateway routes."""

from flask import Blueprint, g, jsonify, request

from middleware.auth import api_login_required
from middleware.idempotency import require_idempotency
from utils import validate_amount

gateway_bp = Blueprint("gateway", __name__, url_prefix="/api/gateway")


@gateway_bp.route("/pay", methods=["POST"])
@api_login_required
@require_idempotency("gateway.pay")
def api_gateway_pay(user):
  data = request.get_json(silent=True) or {}
  account_id = data.get("account_id")
  payment_method = str(data.get("payment_method", "")).upper().strip()
  raw_amount = str(data.get("amount", ""))
  merchant = str(data.get("merchant", "Unknown Merchant")).strip()
  description = str(data.get("description", "Payment")).strip()
  card_last4 = str(data.get("card_last4", "")).strip() or None
  upi_vpa = str(data.get("upi_vpa", "")).strip() or None

  valid_methods = ["UPI", "CARD", "NETBANKING", "WALLET"]
  if payment_method not in valid_methods:
    return jsonify({"success": False, "error": f"Invalid payment method. Use: {', '.join(valid_methods)}"}), 400
  if not account_id:
    return jsonify({"success": False, "error": "account_id is required."}), 400

  acc = g.repo.get_account_by_id(int(account_id))
  if not acc or acc["user_id"] != user["id"]:
    return jsonify({"success": False, "error": "Account not found."}), 404

  ok, val, err = validate_amount(raw_amount)
  if not ok:
    return jsonify({"success": False, "error": err}), 400

  result = g.repo.process_payment(
    user["id"], acc["id"], payment_method, val, merchant, description, card_last4, upi_vpa,
  )
  return jsonify(result), (200 if result["success"] else 400)


@gateway_bp.route("/history", methods=["GET"])
@api_login_required
def api_gateway_history(user):
  limit = min(int(request.args.get("limit", 50)), 200)
  history = g.repo.get_gateway_transactions(user["id"], limit=limit)
  return jsonify({"success": True, "transactions": history})
