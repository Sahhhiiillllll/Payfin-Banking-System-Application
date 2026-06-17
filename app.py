"""
Payfin
app.py — Main Flask application (Production-ready)

Routes:
  /                   Landing page
  /login              Login page
  /register           Register page
  /dashboard          Main dashboard (auth required)
  /transactions       Transaction history
  /upi                UPI payments
  /linked-accounts    Linked bank accounts
  /security           Security settings
  /payment-gateway    Payment gateway

  /api/auth/*         Authentication API
  /api/accounts/*     Account management API
  /api/transactions/* Transaction API
  /api/upi/*          UPI payment API
  /api/gateway/*      Payment gateway API
  /api/user/*         User profile API
"""

from __future__ import annotations
import os
import re
import jwt
import uuid
import functools
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, make_response
)
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database import DatabaseManager
from config import Config

# ── App factory ───────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

CORS(app, resources={r"/api/*": {"origins": "*"}})

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://",
)

db = DatabaseManager()


# ── JWT Helpers ───────────────────────────────────────────────────────────────

def create_jwt(user_id: int, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRY_HOURS),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user() -> Optional[dict]:
    """Extract and validate JWT from Authorization header or cookie."""
    token = None

    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # Fall back to cookie
    if not token:
        token = request.cookies.get("ve_token")

    if not token:
        return None

    payload = decode_jwt(token)
    if not payload:
        return None

    user = db.get_user_by_id(payload["user_id"])
    return user


def api_login_required(f):
    """Decorator for API routes requiring authentication."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required.", "code": 401}), 401
        return f(user, *args, **kwargs)
    return decorated


def web_login_required(f):
    """Decorator for web routes requiring authentication."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("login_page"))
        return f(user, *args, **kwargs)
    return decorated


# ── Validation Helpers ────────────────────────────────────────────────────────

def validate_amount(raw: str) -> Tuple[bool, float, str]:
    raw = str(raw).strip()
    try:
        val = float(raw)
    except (ValueError, TypeError):
        return False, 0.0, "Enter a valid numeric amount."
    if val <= 0:
        return False, 0.0, "Amount must be greater than zero."
    if val > 10_000_000:
        return False, 0.0, "Amount exceeds single-transaction limit of ₹1,00,00,000."
    return True, round(val, 2), ""


def validate_password(pwd: str) -> Tuple[bool, str]:
    if len(pwd) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", pwd):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", pwd):
        return False, "Password must contain at least one digit."
    if not re.search(r"[^A-Za-z0-9]", pwd):
        return False, "Password must contain at least one special character."
    return True, ""


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", email))


def validate_ifsc(ifsc: str) -> bool:
    return bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", ifsc.upper()))


# ── Web Routes (HTML Pages) ────────────────────────────────────────────────────

@app.route("/")
def index():
    user = get_current_user()
    if user:
        return redirect(url_for("dashboard_page"))
    return render_template("index.html", app_name=Config.APP_NAME, company=Config.COMPANY_NAME)


@app.route("/login")
def login_page():
    user = get_current_user()
    if user:
        return redirect(url_for("dashboard_page"))
    return render_template("login.html", app_name=Config.APP_NAME)


@app.route("/register")
def register_page():
    user = get_current_user()
    if user:
        return redirect(url_for("dashboard_page"))
    return render_template("register.html", app_name=Config.APP_NAME)


@app.route("/dashboard")
@web_login_required
def dashboard_page(user):
    return render_template("dashboard.html", user=user, app_name=Config.APP_NAME)


@app.route("/transactions")
@web_login_required
def transactions_page(user):
    return render_template("transactions.html", user=user, app_name=Config.APP_NAME)


@app.route("/upi")
@web_login_required
def upi_page(user):
    return render_template("upi.html", user=user, app_name=Config.APP_NAME)


@app.route("/linked-accounts")
@web_login_required
def linked_accounts_page(user):
    return render_template("linked_accounts.html", user=user, app_name=Config.APP_NAME)


@app.route("/security")
@web_login_required
def security_page(user):
    return render_template("security.html", user=user, app_name=Config.APP_NAME)


@app.route("/payment-gateway")
@web_login_required
def payment_gateway_page(user):
    return render_template("payment_gateway.html", user=user, app_name=Config.APP_NAME)


@app.route("/logout")
def logout():
    response = redirect(url_for("login_page"))
    response.delete_cookie("ve_token")
    return response


# ── API: Authentication ────────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("10 per minute")
def api_register():
    data = request.get_json(silent=True) or {}

    username    = str(data.get("username", "")).strip()
    full_name   = str(data.get("full_name", "")).strip()
    email       = str(data.get("email", "")).strip().lower()
    phone       = str(data.get("phone", "")).strip() or None
    password    = str(data.get("password", ""))
    confirm     = str(data.get("confirm_password", ""))
    account_type = str(data.get("account_type", "Savings")).strip()

    # Validation
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

    result = db.register_user(username, full_name, email, password, phone, account_type)
    if not result["success"]:
        return jsonify(result), 409

    return jsonify({
        "success": True,
        "message": f"Account created! Your UPI ID is {result['upi_id']}",
        "account_no": result["account_no"],
        "upi_id": result["upi_id"],
    }), 201


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
def api_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400

    user = db.authenticate_user(
        username, password,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )
    if not user:
        return jsonify({"success": False, "error": "Invalid username or password."}), 401

    token = create_jwt(user["id"], user["username"])

    response = jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"],
            "upi_id": user.get("upi_id"),
        }
    })
    # Set httponly cookie as well
    response.set_cookie(
        "ve_token", token,
        httponly=True, samesite="Lax",
        max_age=Config.JWT_EXPIRY_HOURS * 3600
    )
    return response


@app.route("/api/auth/me", methods=["GET"])
@api_login_required
def api_me(user):
    return jsonify({"success": True, "user": user})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    response = jsonify({"success": True, "message": "Logged out."})
    response.delete_cookie("ve_token")
    return response


# ── API: Accounts ─────────────────────────────────────────────────────────────

@app.route("/api/accounts", methods=["GET"])
@api_login_required
def api_get_accounts(user):
    accounts = db.get_user_accounts(user["id"])
    return jsonify({"success": True, "accounts": accounts})


@app.route("/api/accounts/add", methods=["POST"])
@api_login_required
def api_add_account(user):
    data = request.get_json(silent=True) or {}
    account_type = str(data.get("account_type", "Savings")).strip()
    valid_types = ["Savings", "Checking", "Current", "Premium Savings"]
    if account_type not in valid_types:
        return jsonify({"success": False, "error": "Invalid account type."}), 400

    # Limit to 3 Payfin accounts
    existing = db.get_user_accounts(user["id"])
    if len(existing) >= 3:
        return jsonify({"success": False, "error": "Maximum 3 accounts allowed per user."}), 400

    result = db.add_account(user["id"], account_type)
    return jsonify(result), (201 if result["success"] else 400)


@app.route("/api/accounts/<int:account_id>/stats", methods=["GET"])
@api_login_required
def api_account_stats(user, account_id):
    acc = db.get_account_by_id(account_id)
    if not acc or acc["user_id"] != user["id"]:
        return jsonify({"error": "Account not found."}), 404

    txns = db.get_transactions(account_id, limit=50)
    credits = sum(t["amount"] for t in txns if t["txn_type"] == "CREDIT")
    debits  = sum(t["amount"] for t in txns if t["txn_type"] == "DEBIT")
    return jsonify({
        "success": True,
        "account": acc,
        "stats": {
            "total_credits": credits,
            "total_debits": debits,
            "transaction_count": len(txns),
        }
    })


# ── API: Transactions ─────────────────────────────────────────────────────────

@app.route("/api/transactions", methods=["GET"])
@api_login_required
def api_get_transactions(user):
    limit    = min(int(request.args.get("limit", 100)), 500)
    category = request.args.get("category")
    txns     = db.get_all_transactions(user["id"], limit=limit)
    return jsonify({"success": True, "transactions": txns})


@app.route("/api/transactions/account/<int:account_id>", methods=["GET"])
@api_login_required
def api_get_account_transactions(user, account_id):
    acc = db.get_account_by_id(account_id)
    if not acc or acc["user_id"] != user["id"]:
        return jsonify({"error": "Account not found."}), 404

    limit    = min(int(request.args.get("limit", 100)), 500)
    category = request.args.get("category")
    txns     = db.get_transactions(account_id, limit=limit, category=category)
    return jsonify({"success": True, "transactions": txns})


@app.route("/api/transactions/deposit", methods=["POST"])
@api_login_required
@limiter.limit("30 per minute")
def api_deposit(user):
    data       = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    raw_amount = str(data.get("amount", ""))
    description = str(data.get("description", "Deposit")).strip() or "Deposit"

    if not account_id:
        return jsonify({"success": False, "error": "account_id is required."}), 400

    acc = db.get_account_by_id(int(account_id))
    if not acc or acc["user_id"] != user["id"]:
        return jsonify({"success": False, "error": "Account not found."}), 404

    ok, val, err = validate_amount(raw_amount)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    result = db.deposit(acc["id"], val, description)
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/transactions/withdraw", methods=["POST"])
@api_login_required
@limiter.limit("30 per minute")
def api_withdraw(user):
    data       = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    raw_amount = str(data.get("amount", ""))
    description = str(data.get("description", "Withdrawal")).strip() or "Withdrawal"

    if not account_id:
        return jsonify({"success": False, "error": "account_id is required."}), 400

    acc = db.get_account_by_id(int(account_id))
    if not acc or acc["user_id"] != user["id"]:
        return jsonify({"success": False, "error": "Account not found."}), 404

    ok, val, err = validate_amount(raw_amount)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    result = db.withdraw(acc["id"], val, description)
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/transactions/transfer", methods=["POST"])
@api_login_required
@limiter.limit("20 per minute")
def api_transfer(user):
    data           = request.get_json(silent=True) or {}
    from_account_id = data.get("from_account_id")
    to_account_no  = str(data.get("to_account_no", "")).strip()
    raw_amount     = str(data.get("amount", ""))
    note           = str(data.get("note", "")).strip()

    if not from_account_id or not to_account_no:
        return jsonify({"success": False, "error": "from_account_id and to_account_no are required."}), 400

    acc = db.get_account_by_id(int(from_account_id))
    if not acc or acc["user_id"] != user["id"]:
        return jsonify({"success": False, "error": "Source account not found."}), 404

    ok, val, err = validate_amount(raw_amount)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    result = db.transfer(acc["id"], to_account_no, val, note)
    return jsonify(result), (200 if result["success"] else 400)


# ── API: UPI ──────────────────────────────────────────────────────────────────

@app.route("/api/upi/handle", methods=["GET"])
@api_login_required
def api_get_upi_handle(user):
    return jsonify({"success": True, "upi_id": user.get("upi_id")})


@app.route("/api/upi/lookup/<upi_id>", methods=["GET"])
@api_login_required
def api_lookup_upi(user, upi_id):
    target = db.get_user_by_upi(upi_id)
    if not target:
        return jsonify({"success": False, "error": f"UPI ID '{upi_id}' not found."}), 404
    return jsonify({
        "success": True,
        "upi_id": upi_id,
        "name": target["full_name"],
    })


@app.route("/api/upi/send", methods=["POST"])
@api_login_required
@limiter.limit("20 per minute")
def api_upi_send(user):
    data           = request.get_json(silent=True) or {}
    from_account_id = data.get("from_account_id")
    to_upi_id      = str(data.get("to_upi_id", "")).strip()
    raw_amount     = str(data.get("amount", ""))
    note           = str(data.get("note", "")).strip()

    if not from_account_id or not to_upi_id:
        return jsonify({"success": False, "error": "from_account_id and to_upi_id are required."}), 400

    # Don't allow sending to yourself
    if to_upi_id == user.get("upi_id"):
        return jsonify({"success": False, "error": "Cannot send UPI payment to yourself."}), 400

    acc = db.get_account_by_id(int(from_account_id))
    if not acc or acc["user_id"] != user["id"]:
        return jsonify({"success": False, "error": "Source account not found."}), 404

    ok, val, err = validate_amount(raw_amount)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    result = db.upi_transfer(acc["id"], to_upi_id, val, note)
    return jsonify(result), (200 if result["success"] else 400)


# ── API: Linked Accounts ──────────────────────────────────────────────────────

@app.route("/api/linked-accounts", methods=["GET"])
@api_login_required
def api_get_linked_accounts(user):
    accounts = db.get_linked_accounts(user["id"])
    return jsonify({"success": True, "linked_accounts": accounts})


@app.route("/api/linked-accounts/add", methods=["POST"])
@api_login_required
def api_add_linked_account(user):
    data           = request.get_json(silent=True) or {}
    bank_name      = str(data.get("bank_name", "")).strip()
    account_holder = str(data.get("account_holder", "")).strip()
    account_no     = str(data.get("account_no", "")).strip()
    ifsc_code      = str(data.get("ifsc_code", "")).strip().upper()
    account_type   = str(data.get("account_type", "Savings")).strip()

    if not all([bank_name, account_holder, account_no, ifsc_code]):
        return jsonify({"success": False, "error": "All fields are required."}), 400

    if len(account_no) < 9 or len(account_no) > 18:
        return jsonify({"success": False, "error": "Account number must be 9–18 digits."}), 400

    if not account_no.isdigit():
        return jsonify({"success": False, "error": "Account number must contain only digits."}), 400

    if not validate_ifsc(ifsc_code):
        return jsonify({"success": False, "error": "Invalid IFSC code format (e.g. SBIN0001234)."}), 400

    result = db.add_linked_account(
        user["id"], bank_name, account_holder, account_no, ifsc_code, account_type
    )
    return jsonify(result), (201 if result["success"] else 400)


@app.route("/api/linked-accounts/<int:linked_id>", methods=["DELETE"])
@api_login_required
def api_remove_linked_account(user, linked_id):
    result = db.remove_linked_account(user["id"], linked_id)
    return jsonify(result)


# ── API: Payment Gateway ──────────────────────────────────────────────────────

@app.route("/api/gateway/pay", methods=["POST"])
@api_login_required
@limiter.limit("20 per minute")
def api_gateway_pay(user):
    data           = request.get_json(silent=True) or {}
    account_id     = data.get("account_id")
    payment_method = str(data.get("payment_method", "")).upper().strip()
    raw_amount     = str(data.get("amount", ""))
    merchant       = str(data.get("merchant", "Unknown Merchant")).strip()
    description    = str(data.get("description", "Payment")).strip()
    card_last4     = str(data.get("card_last4", "")).strip() or None
    upi_vpa        = str(data.get("upi_vpa", "")).strip() or None

    valid_methods = ["UPI", "CARD", "NETBANKING", "WALLET"]
    if payment_method not in valid_methods:
        return jsonify({"success": False, "error": f"Invalid payment method. Use: {', '.join(valid_methods)}"}), 400

    if not account_id:
        return jsonify({"success": False, "error": "account_id is required."}), 400

    acc = db.get_account_by_id(int(account_id))
    if not acc or acc["user_id"] != user["id"]:
        return jsonify({"success": False, "error": "Account not found."}), 404

    ok, val, err = validate_amount(raw_amount)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    result = db.process_payment(
        user["id"], acc["id"],
        payment_method, val,
        merchant, description,
        card_last4, upi_vpa
    )
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/gateway/history", methods=["GET"])
@api_login_required
def api_gateway_history(user):
    limit = min(int(request.args.get("limit", 50)), 200)
    history = db.get_gateway_transactions(user["id"], limit=limit)
    return jsonify({"success": True, "transactions": history})


# ── API: Dashboard ────────────────────────────────────────────────────────────

@app.route("/api/dashboard/stats", methods=["GET"])
@api_login_required
def api_dashboard_stats(user):
    stats = db.get_dashboard_stats(user["id"])
    return jsonify({"success": True, "stats": stats})


# ── API: User Profile ─────────────────────────────────────────────────────────

@app.route("/api/user/profile", methods=["PUT"])
@api_login_required
def api_update_profile(user):
    data      = request.get_json(silent=True) or {}
    full_name = str(data.get("full_name", "")).strip()
    phone     = str(data.get("phone", "")).strip() or None

    if not full_name:
        return jsonify({"success": False, "error": "Full name is required."}), 400
    if len(full_name) < 2 or len(full_name) > 100:
        return jsonify({"success": False, "error": "Full name must be 2–100 characters."}), 400

    result = db.update_profile(user["id"], full_name, phone)
    return jsonify(result)


@app.route("/api/user/change-password", methods=["POST"])
@api_login_required
@limiter.limit("5 per minute")
def api_change_password(user):
    data         = request.get_json(silent=True) or {}
    old_password = str(data.get("old_password", ""))
    new_password = str(data.get("new_password", ""))
    confirm      = str(data.get("confirm_password", ""))

    if not old_password or not new_password or not confirm:
        return jsonify({"success": False, "error": "All password fields are required."}), 400
    if new_password != confirm:
        return jsonify({"success": False, "error": "New passwords do not match."}), 400

    ok, err = validate_password(new_password)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    result = db.change_password(user["id"], old_password, new_password)
    if result["success"]:
        # Revoke all existing sessions
        resp = jsonify({"success": True, "message": "Password changed. Please log in again."})
        resp.delete_cookie("ve_token")
        return resp
    return jsonify(result), 400


# ── Error Handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found.", "code": 404}), 404
    return render_template("404.html", app_name=Config.APP_NAME), 404


@app.errorhandler(429)
def rate_limited(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Too many requests. Please slow down.", "code": 429}), 429
    return render_template("429.html", app_name=Config.APP_NAME), 429


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error.", "code": 500}), 500
    return render_template("500.html", app_name=Config.APP_NAME), 500


# ── Security Headers ──────────────────────────────────────────────────────────

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = Config.PORT
    debug = Config.DEBUG
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          Payfin          ║
║          Bank Smarter. Move Faster.                          ║
╠══════════════════════════════════════════════════════════════╣
║  Server  : http://127.0.0.1:{port}                           ║
║  Demo    : username=demo  password=Demo@12345                ║
║  Mode    : {'Development' if debug else 'Production'}        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=debug)
