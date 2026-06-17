"""Initial Payfin schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
    "users",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("username", sa.String(30), nullable=False),
    sa.Column("full_name", sa.String(100), nullable=False),
    sa.Column("email", sa.String(255), nullable=False),
    sa.Column("phone", sa.String(20), nullable=True),
    sa.Column("pwd_hash", sa.Text(), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
    sa.Column("totp_secret", sa.String(64), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("username"),
    sa.UniqueConstraint("email"),
  )
  op.create_index("ix_users_username", "users", ["username"])
  op.create_index("ix_users_email", "users", ["email"])

  op.create_table(
    "accounts",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("account_no", sa.String(12), nullable=False),
    sa.Column("account_type", sa.String(30), nullable=False),
    sa.Column("balance", sa.Numeric(18, 2), nullable=False),
    sa.Column("is_primary", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("account_no"),
  )

  op.create_table(
    "upi_handles",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("upi_id", sa.String(100), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("user_id"),
    sa.UniqueConstraint("upi_id"),
  )

  op.create_table(
    "transactions",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("account_id", sa.Integer(), nullable=False),
    sa.Column("txn_type", sa.String(10), nullable=False),
    sa.Column("txn_category", sa.String(20), nullable=False),
    sa.Column("amount", sa.Numeric(18, 2), nullable=False),
    sa.Column("balance_after", sa.Numeric(18, 2), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("counterparty", sa.String(200), nullable=True),
    sa.Column("reference_id", sa.String(32), nullable=False),
    sa.Column("status", sa.String(20), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("reference_id"),
  )

  op.create_table(
    "linked_accounts",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("bank_name", sa.String(100), nullable=False),
    sa.Column("account_holder", sa.String(100), nullable=False),
    sa.Column("account_no", sa.String(18), nullable=False),
    sa.Column("ifsc_code", sa.String(11), nullable=False),
    sa.Column("account_type", sa.String(30), nullable=False),
    sa.Column("is_verified", sa.Boolean(), nullable=False),
    sa.Column("is_primary", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )

  op.create_table(
    "gateway_transactions",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("account_id", sa.Integer(), nullable=True),
    sa.Column("payment_method", sa.String(20), nullable=False),
    sa.Column("amount", sa.Numeric(18, 2), nullable=False),
    sa.Column("status", sa.String(20), nullable=False),
    sa.Column("reference_id", sa.String(32), nullable=False),
    sa.Column("external_id", sa.String(100), nullable=True),
    sa.Column("merchant", sa.String(200), nullable=True),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("card_last4", sa.String(4), nullable=True),
    sa.Column("upi_vpa", sa.String(100), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("reference_id"),
  )

  op.create_table(
    "sessions",
    sa.Column("id", sa.String(36), nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("ip_address", sa.String(45), nullable=True),
    sa.Column("user_agent", sa.Text(), nullable=True),
    sa.Column("is_revoked", sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
  )

  op.create_table(
    "audit_logs",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=True),
    sa.Column("action", sa.String(80), nullable=False),
    sa.Column("resource_type", sa.String(50), nullable=True),
    sa.Column("resource_id", sa.String(50), nullable=True),
    sa.Column("ip_address", sa.String(45), nullable=True),
    sa.Column("user_agent", sa.Text(), nullable=True),
    sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    sa.PrimaryKeyConstraint("id"),
  )

  op.create_table(
    "idempotency_keys",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("key_hash", sa.String(64), nullable=False),
    sa.Column("endpoint", sa.String(120), nullable=False),
    sa.Column("request_hash", sa.String(64), nullable=False),
    sa.Column("response_status", sa.Integer(), nullable=False),
    sa.Column("response_body", postgresql.JSONB(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("user_id", "key_hash", name="uq_idempotency_user_key"),
  )

  op.create_table(
    "webhook_events",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("provider", sa.String(30), nullable=False),
    sa.Column("event_id", sa.String(100), nullable=False),
    sa.Column("event_type", sa.String(80), nullable=False),
    sa.Column("payload", postgresql.JSONB(), nullable=False),
    sa.Column("signature_valid", sa.Boolean(), nullable=False),
    sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("event_id"),
  )


def downgrade() -> None:
  for table in [
    "webhook_events", "idempotency_keys", "audit_logs", "sessions",
    "gateway_transactions", "linked_accounts", "transactions",
    "upi_handles", "accounts", "users",
  ]:
    op.drop_table(table)
