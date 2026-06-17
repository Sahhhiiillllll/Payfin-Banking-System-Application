"""Monthly PDF statement generation — serverless-friendly in-memory stream."""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import Config


def generate_statement_pdf(
  user: dict[str, Any],
  account: dict[str, Any],
  transactions: list[dict[str, Any]],
  month: int,
  year: int,
) -> bytes:
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm)
  styles = getSampleStyleSheet()
  title_style = ParagraphStyle("Title", parent=styles["Heading1"], textColor=colors.HexColor("#00a8a0"))
  elements = []

  elements.append(Paragraph(f"{Config.APP_NAME} — Account Statement", title_style))
  elements.append(Spacer(1, 8))
  elements.append(Paragraph(f"<b>{user['full_name']}</b> ({user['email']})", styles["Normal"]))
  elements.append(Paragraph(f"Account: {account['account_no']} · {account['account_type']}", styles["Normal"]))
  elements.append(Paragraph(f"Period: {month:02d}/{year}", styles["Normal"]))
  elements.append(Spacer(1, 16))

  data = [["Date", "Type", "Description", "Amount (₹)", "Balance (₹)"]]
  for txn in transactions:
    data.append([
      str(txn.get("created_at", ""))[:10],
      txn.get("txn_type", ""),
      (txn.get("description") or "")[:40],
      f"{Decimal(str(txn.get('amount', 0))):,.2f}",
      f"{Decimal(str(txn.get('balance_after', 0))):,.2f}",
    ])

  table = Table(data, colWidths=[25 * mm, 18 * mm, 55 * mm, 30 * mm, 35 * mm])
  table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1526")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
  ]))
  elements.append(table)
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(
    f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · {Config.COMPANY_NAME}",
    styles["Italic"],
  ))

  doc.build(elements)
  buffer.seek(0)
  return buffer.read()
