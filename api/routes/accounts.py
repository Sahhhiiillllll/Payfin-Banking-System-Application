"""Account routes."""

from flask import Blueprint, g, jsonify, request

from middleware.auth import api_login_required

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api")


@accounts_bp.route("/accounts", methods=["GET"])
@api_login_required
def api_get_accounts(user):
  return jsonify({"success": True, "accounts": g.repo.get_user_accounts(user["id"])})


@accounts_bp.route("/accounts/add", methods=["POST"])
@api_login_required
def api_add_account(user):
  data = request.get_json(silent=True) or {}
  account_type = str(data.get("account_type", "Savings")).strip()
  valid_types = ["Savings", "Checking", "Current", "Premium Savings"]
  if account_type not in valid_types:
    return jsonify({"success": False, "error": "Invalid account type."}), 400

  existing = g.repo.get_user_accounts(user["id"])
  if len(existing) >= 3:
    return jsonify({"success": False, "error": "Maximum 3 accounts allowed per user."}), 400

  result = g.repo.add_account(user["id"], account_type)
  return jsonify(result), (201 if result["success"] else 400)


@accounts_bp.route("/accounts/<int:account_id>/stats", methods=["GET"])
@api_login_required
def api_account_stats(user, account_id):
  acc = g.repo.get_account_by_id(account_id)
  if not acc or acc["user_id"] != user["id"]:
    return jsonify({"error": "Account not found."}), 404

  txns = g.repo.get_transactions(account_id, limit=50)
  credits = sum(t["amount"] for t in txns if t["txn_type"] == "CREDIT")
  debits = sum(t["amount"] for t in txns if t["txn_type"] == "DEBIT")
  return jsonify({
    "success": True,
    "account": acc,
    "stats": {"total_credits": credits, "total_debits": debits, "transaction_count": len(txns)},
  })


@accounts_bp.route("/linked-accounts", methods=["GET"])
@api_login_required
def api_get_linked_accounts(user):
  return jsonify({"success": True, "linked_accounts": g.repo.get_linked_accounts(user["id"])})


@accounts_bp.route("/linked-accounts/add", methods=["POST"])
@api_login_required
def api_add_linked_account(user):
  from services.ifsc_service import verify_ifsc

  data = request.get_json(silent=True) or {}
  bank_name = str(data.get("bank_name", "")).strip()
  account_holder = str(data.get("account_holder", "")).strip()
  account_no = str(data.get("account_no", "")).strip()
  ifsc_code = str(data.get("ifsc_code", "")).strip().upper()
  account_type = str(data.get("account_type", "Savings")).strip()

  if not all([bank_name, account_holder, account_no, ifsc_code]):
    return jsonify({"success": False, "error": "All fields are required."}), 400
  if len(account_no) < 9 or len(account_no) > 18 or not account_no.isdigit():
    return jsonify({"success": False, "error": "Account number must be 9–18 digits."}), 400

  ifsc_result = verify_ifsc(ifsc_code)
  if not ifsc_result.get("valid"):
    return jsonify({"success": False, "error": ifsc_result.get("error", "Invalid IFSC.")}), 400

  result = g.repo.add_linked_account(
    user["id"], bank_name or ifsc_result.get("bank", ""), account_holder,
    account_no, ifsc_code, account_type, verified=True,
  )
  return jsonify({**result, "ifsc_details": ifsc_result}), (201 if result["success"] else 400)


@accounts_bp.route("/linked-accounts/<int:linked_id>", methods=["DELETE"])
@api_login_required
def api_remove_linked_account(user, linked_id):
  return jsonify(g.repo.remove_linked_account(user["id"], linked_id))


@accounts_bp.route("/dashboard/stats", methods=["GET"])
@api_login_required
def api_dashboard_stats(user):
  return jsonify({"success": True, "stats": g.repo.get_dashboard_stats(user["id"])})


@accounts_bp.route("/user/profile", methods=["PUT"])
@api_login_required
def api_update_profile(user):
  data = request.get_json(silent=True) or {}
  full_name = str(data.get("full_name", "")).strip()
  phone = str(data.get("phone", "")).strip() or None
  if not full_name or len(full_name) < 2 or len(full_name) > 100:
    return jsonify({"success": False, "error": "Full name must be 2–100 characters."}), 400
  return jsonify(g.repo.update_profile(user["id"], full_name, phone))


@accounts_bp.route("/user/change-password", methods=["POST"])
@api_login_required
def api_change_password(user):
  data = request.get_json(silent=True) or {}
  old_password = str(data.get("old_password", ""))
  new_password = str(data.get("new_password", ""))
  confirm = str(data.get("confirm_password", ""))

  if not old_password or not new_password or not confirm:
    return jsonify({"success": False, "error": "All password fields are required."}), 400
  if new_password != confirm:
    return jsonify({"success": False, "error": "New passwords do not match."}), 400

  from utils import validate_password
  ok, err = validate_password(new_password)
  if not ok:
    return jsonify({"success": False, "error": err}), 400

  result = g.repo.change_password(user["id"], old_password, new_password)
  if result["success"]:
    resp = jsonify({"success": True, "message": "Password changed. Please log in again."})
    resp.delete_cookie("ve_token")
    return resp
  return jsonify(result), 400
