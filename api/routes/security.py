"""Security & MFA routes."""

from flask import Blueprint, g, jsonify, request

from config import Config
from middleware.auth import api_login_required, create_jwt
from services import mfa_service
from services.ifsc_service import verify_ifsc

security_bp = Blueprint("security", __name__, url_prefix="/api/security")


@security_bp.route("/mfa/setup", methods=["POST"])
@api_login_required
def mfa_setup(user):
  return jsonify(mfa_service.setup_mfa(g.db, user["id"]))


@security_bp.route("/mfa/enable", methods=["POST"])
@api_login_required
def mfa_enable(user):
  data = request.get_json(silent=True) or {}
  secret = str(data.get("secret", "")).strip()
  code = str(data.get("code", "")).strip()
  if not secret or not code:
    return jsonify({"success": False, "error": "secret and code are required."}), 400
  return jsonify(mfa_service.enable_mfa(g.db, user["id"], secret, code))


@security_bp.route("/mfa/disable", methods=["POST"])
@api_login_required
def mfa_disable(user):
  data = request.get_json(silent=True) or {}
  code = str(data.get("code", "")).strip()
  if not code:
    return jsonify({"success": False, "error": "code is required."}), 400
  return jsonify(mfa_service.disable_mfa(g.db, user["id"], code))


@security_bp.route("/mfa/verify", methods=["POST"])
@api_login_required
def mfa_verify(user):
  from models.user import User

  data = request.get_json(silent=True) or {}
  code = str(data.get("code", "")).strip()
  db_user = g.db.get(User, user["id"])
  if not db_user or not mfa_service.verify_totp(db_user.totp_secret or "", code):
    return jsonify({"success": False, "error": "Invalid TOTP code."}), 401

  token = create_jwt(user["id"], user["username"], mfa_verified=True)
  resp = jsonify({"success": True, "token": token})
  resp.set_cookie("ve_token", token, httponly=True, samesite="Lax", secure=Config.SESSION_COOKIE_SECURE,
                  max_age=Config.JWT_EXPIRY_HOURS * 3600)
  return resp


@security_bp.route("/ifsc/<ifsc_code>", methods=["GET"])
@api_login_required
def ifsc_lookup(user, ifsc_code):
  return jsonify(verify_ifsc(ifsc_code))


@security_bp.route("/config", methods=["GET"])
def security_config():
  return jsonify({
    "pusher_key": Config.PUSHER_KEY or None,
    "pusher_cluster": Config.PUSHER_CLUSTER,
    "realtime_enabled": bool(Config.PUSHER_KEY),
  })
