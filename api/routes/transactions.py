"""Transaction routes."""

from flask import Blueprint, g, jsonify, request

from middleware.auth import api_login_required
from utils import validate_amount

transactions_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")


@transactions_bp.route("", methods=["GET"])
@api_login_required
def api_get_transactions(user):
  limit = min(int(request.args.get("limit", 100)), 500)
  txns = g.repo.get_all_transactions(user["id"], limit=limit)
  return jsonify({"success": True, "transactions": txns})


@transactions_bp.route("/account/<int:account_id>", methods=["GET"])
@api_login_required
def api_get_account_transactions(user, account_id):
  acc = g.repo.get_account_by_id(account_id)
  if not acc or acc["user_id"] != user["id"]:
    return jsonify({"error": "Account not found."}), 404
  limit = min(int(request.args.get("limit", 100)), 500)
  category = request.args.get("category")
  txns = g.repo.get_transactions(account_id, limit=limit, category=category)
  return jsonify({"success": True, "transactions": txns})


@transactions_bp.route("/deposit", methods=["POST"])
@api_login_required
def api_deposit(user):
  data = request.get_json(silent=True) or {}
  account_id = data.get("account_id")
  raw_amount = str(data.get("amount", ""))
  description = str(data.get("description", "Deposit")).strip() or "Deposit"

  if not account_id:
    return jsonify({"success": False, "error": "account_id is required."}), 400
  acc = g.repo.get_account_by_id(int(account_id))
  if not acc or acc["user_id"] != user["id"]:
    return jsonify({"success": False, "error": "Account not found."}), 404

  ok, val, err = validate_amount(raw_amount)
  if not ok:
    return jsonify({"success": False, "error": err}), 400

  result = g.repo.deposit(acc["id"], val, description)
  return jsonify(result), (200 if result["success"] else 400)


@transactions_bp.route("/withdraw", methods=["POST"])
@api_login_required
def api_withdraw(user):
  data = request.get_json(silent=True) or {}
  account_id = data.get("account_id")
  raw_amount = str(data.get("amount", ""))
  description = str(data.get("description", "Withdrawal")).strip() or "Withdrawal"

  if not account_id:
    return jsonify({"success": False, "error": "account_id is required."}), 400
  acc = g.repo.get_account_by_id(int(account_id))
  if not acc or acc["user_id"] != user["id"]:
    return jsonify({"success": False, "error": "Account not found."}), 404

  ok, val, err = validate_amount(raw_amount)
  if not ok:
    return jsonify({"success": False, "error": err}), 400

  result = g.repo.withdraw(acc["id"], val, description)
  return jsonify(result), (200 if result["success"] else 400)


@transactions_bp.route("/transfer", methods=["POST"])
@api_login_required
def api_transfer(user):
  data = request.get_json(silent=True) or {}
  from_account_id = data.get("from_account_id")
  to_account_no = str(data.get("to_account_no", "")).strip()
  raw_amount = str(data.get("amount", ""))
  note = str(data.get("note", "")).strip()

  if not from_account_id or not to_account_no:
    return jsonify({"success": False, "error": "from_account_id and to_account_no are required."}), 400

  acc = g.repo.get_account_by_id(int(from_account_id))
  if not acc or acc["user_id"] != user["id"]:
    return jsonify({"success": False, "error": "Source account not found."}), 404

  ok, val, err = validate_amount(raw_amount)
  if not ok:
    return jsonify({"success": False, "error": err}), 400

  result = g.repo.transfer(acc["id"], to_account_no, val, note)
  return jsonify(result), (200 if result["success"] else 400)
