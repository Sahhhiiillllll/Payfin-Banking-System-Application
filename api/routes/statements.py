"""PDF statement routes."""

from datetime import datetime

from flask import Blueprint, Response, g, jsonify, request

from middleware.auth import api_login_required
from services.statement_service import generate_statement_pdf

statements_bp = Blueprint("statements", __name__, url_prefix="/api/statements")


@statements_bp.route("/monthly", methods=["GET"])
@api_login_required
def monthly_statement(user):
  month = int(request.args.get("month", datetime.utcnow().month))
  year = int(request.args.get("year", datetime.utcnow().year))
  account_id = request.args.get("account_id")

  accounts = g.repo.get_user_accounts(user["id"])
  if not accounts:
    return jsonify({"error": "No accounts found."}), 404

  account = None
  if account_id:
    account = g.repo.get_account_by_id(int(account_id))
    if not account or account["user_id"] != user["id"]:
      return jsonify({"error": "Account not found."}), 404
  else:
    account = next((a for a in accounts if a["is_primary"]), accounts[0])

  txns = [t for t in g.repo.get_transactions_for_statement(user["id"], month, year)
          if t.get("account_no") == account["account_no"]]

  pdf_bytes = generate_statement_pdf(user, account, txns, month, year)
  filename = f"payfin-statement-{account['account_no']}-{year}{month:02d}.pdf"
  return Response(
    pdf_bytes,
    mimetype="application/pdf",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )
