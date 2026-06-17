"""UPI routes."""

from flask import Blueprint, g, jsonify, request

from middleware.auth import api_login_required
from middleware.idempotency import require_idempotency
from services.vpa_service import lookup_vpa
from utils import validate_amount

upi_bp = Blueprint("upi", __name__, url_prefix="/api/upi")


@upi_bp.route("/handle", methods=["GET"])
@api_login_required
def api_get_upi_handle(user):
  return jsonify({"success": True, "upi_id": user.get("upi_id")})


@upi_bp.route("/lookup/<path:upi_id>", methods=["GET"])
@api_login_required
def api_lookup_upi(user, upi_id):
  result = lookup_vpa(g.db, upi_id)
  if not result.get("success"):
    return jsonify(result), 404
  return jsonify(result)


@upi_bp.route("/send", methods=["POST"])
@api_login_required
@require_idempotency("upi.send")
def api_upi_send(user):
  data = request.get_json(silent=True) or {}
  from_account_id = data.get("from_account_id")
  to_upi_id = str(data.get("to_upi_id", "")).strip()
  raw_amount = str(data.get("amount", ""))
  note = str(data.get("note", "")).strip()

  if not from_account_id or not to_upi_id:
    return jsonify({"success": False, "error": "from_account_id and to_upi_id are required."}), 400
  if to_upi_id == user.get("upi_id"):
    return jsonify({"success": False, "error": "Cannot send UPI payment to yourself."}), 400

  acc = g.repo.get_account_by_id(int(from_account_id))
  if not acc or acc["user_id"] != user["id"]:
    return jsonify({"success": False, "error": "Source account not found."}), 404

  ok, val, err = validate_amount(raw_amount)
  if not ok:
    return jsonify({"success": False, "error": err}), 400

  result = g.repo.upi_transfer(acc["id"], to_upi_id, val, note)
  return jsonify(result), (200 if result["success"] else 400)
