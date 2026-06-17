"""Authentication routes."""

from __future__ import annotations

import re

from flask import Blueprint, g, jsonify, request

from config import Config
from middleware.auth import api_login_required, api_mfa_pending_ok, create_jwt, get_current_user
from middleware.audit import audit_log
from services.mfa_service import verify_totp
from utils import validate_email, validate_password

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def api_register():
  data = request.get_json(silent=True) or {}
  username = str(data.get("username", "")).strip()
  full_name = str(data.get("full_name", "")).strip()
  email = str(data.get("email", "")).strip().lower()
  phone = str(data.get("phone", "")).strip() or None
  password = str(data.get("password", ""))
  confirm = str(data.get("confirm_password", ""))
  account_type = str(data.get("account_type", "Savings")).strip()

  if not all([username, full_name, email, password, confirm]):
    return jsonify({"success": False, "error": "All required fields must be filled."}), 400
  if len(username) < 3 or len(username) > 30:
    return jsonify({"success": False, "error": "Username must be 3–30 characters."}), 400
  if not re.match(r"^[a-zA-Z0-9_]+$", username):
    return jsonify({"success": False, "error": "Username can only contain letters, digits, underscores."}), 400
  if not validate_email(email):
    return jsonify({"success": False, "error": "Invalid email address format."}), 400
  if password != confirm:
    return jsonify({"success": False, "error": "Passwords do not match."}), 400

  ok, err = validate_password(password)
  if not ok:
    return jsonify({"success": False, "error": err}), 400

  valid_types = ["Savings", "Checking", "Current", "Premium Savings"]
  if account_type not in valid_types:
    account_type = "Savings"

  result = g.repo.register_user(username, full_name, email, password, phone, account_type)
  if not result["success"]:
    return jsonify(result), 409

  return jsonify({
    "success": True,
    "message": f"Account created! Your UPI ID is {result['upi_id']}",
    "account_no": result["account_no"],
    "upi_id": result["upi_id"],
  }), 201


@auth_bp.route("/login", methods=["POST"])
def api_login():
  data = request.get_json(silent=True) or {}
  username = str(data.get("username", "")).strip()
  password = str(data.get("password", ""))
  mfa_code = str(data.get("mfa_code", "")).strip()

  if not username or not password:
    return jsonify({"success": False, "error": "Username and password are required."}), 400

  user = g.repo.authenticate_user(username, password, request.remote_addr, request.headers.get("User-Agent"))
  if not user:
    return jsonify({"success": False, "error": "Invalid username or password."}), 401

  mfa_verified = True
  if user.get("mfa_enabled"):
    from models.user import User

    db_user = g.db.get(User, user["id"])
    if not mfa_code or not verify_totp(db_user.totp_secret or "", mfa_code):
      token = create_jwt(user["id"], user["username"], mfa_verified=False)
      resp = jsonify({
        "success": True,
        "mfa_required": True,
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "full_name": user["full_name"]},
      })
      resp.set_cookie("ve_token", token, httponly=True, samesite="Lax", secure=Config.SESSION_COOKIE_SECURE,
                      max_age=Config.JWT_EXPIRY_HOURS * 3600)
      return resp

  token = create_jwt(user["id"], user["username"], mfa_verified=mfa_verified)
  response = jsonify({
    "success": True,
    "token": token,
    "user": {
      "id": user["id"], "username": user["username"], "full_name": user["full_name"],
      "email": user["email"], "upi_id": user.get("upi_id"), "mfa_enabled": user.get("mfa_enabled"),
    },
  })
  response.set_cookie("ve_token", token, httponly=True, samesite="Lax", secure=Config.SESSION_COOKIE_SECURE,
                      max_age=Config.JWT_EXPIRY_HOURS * 3600)
  return response


@auth_bp.route("/me", methods=["GET"])
@api_login_required
def api_me(user):
  return jsonify({"success": True, "user": user})


@auth_bp.route("/logout", methods=["POST"])
def api_logout():
  user = get_current_user(g.repo)
  if user:
    audit_log(g.db, "auth.logout", user_id=user["id"])
  response = jsonify({"success": True, "message": "Logged out."})
  response.delete_cookie("ve_token")
  return response
