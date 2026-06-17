"""
Payfin
database.py — Production-grade SQLite database layer

Security:
  - All queries use parameterised placeholders (SQL-injection immune)
  - Passwords stored as bcrypt hashes (cost factor 12)
  - Transfers wrapped in ACID transactions (BEGIN IMMEDIATE / COMMIT / ROLLBACK)
  - WAL journal mode + foreign keys enforced
"""

from __future__ import annotations

import sqlite3
import bcrypt
import os
import secrets
import random
import string
import threading
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from config import Config


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), Config.DATABASE_PATH)
UPI_SUFFIX = Config.UPI_SUFFIX


class DatabaseManager:
    """Thread-safe SQLite manager. One connection per thread via threading.local()."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()
        self._seed_demo_data()

    # ── Connection ─────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return self._local.conn

    # ── Schema ─────────────────────────────────────────────────────────────────

    def _init_schema(self):
        c = self._conn()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                full_name   TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                phone       TEXT,
                pwd_hash    TEXT    NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                last_login  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS accounts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id),
                account_no   TEXT    NOT NULL UNIQUE,
                account_type TEXT    NOT NULL DEFAULT 'Savings',
                balance      REAL    NOT NULL DEFAULT 0.0,
                is_primary   INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                CHECK (balance >= 0)
            );
            CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id);
            CREATE INDEX IF NOT EXISTS idx_accounts_no   ON accounts(account_no);

            CREATE TABLE IF NOT EXISTS transactions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id    INTEGER NOT NULL REFERENCES accounts(id),
                txn_type      TEXT    NOT NULL,
                txn_category  TEXT    NOT NULL DEFAULT 'BANK',
                amount        REAL    NOT NULL,
                balance_after REAL    NOT NULL,
                description   TEXT,
                counterparty  TEXT,
                reference_id  TEXT    UNIQUE,
                status        TEXT    NOT NULL DEFAULT 'SUCCESS',
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_txn_date    ON transactions(created_at DESC);

            CREATE TABLE IF NOT EXISTS upi_handles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL UNIQUE REFERENCES users(id),
                upi_id     TEXT    NOT NULL UNIQUE,
                is_active  INTEGER NOT NULL DEFAULT 1,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_upi_handle ON upi_handles(upi_id);

            CREATE TABLE IF NOT EXISTS linked_accounts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                bank_name       TEXT    NOT NULL,
                account_holder  TEXT    NOT NULL,
                account_no      TEXT    NOT NULL,
                ifsc_code       TEXT    NOT NULL,
                account_type    TEXT    NOT NULL DEFAULT 'Savings',
                is_verified     INTEGER NOT NULL DEFAULT 0,
                is_primary      INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_linked_user ON linked_accounts(user_id);

            CREATE TABLE IF NOT EXISTS gateway_transactions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(id),
                account_id     INTEGER REFERENCES accounts(id),
                payment_method TEXT    NOT NULL,
                amount         REAL    NOT NULL,
                status         TEXT    NOT NULL DEFAULT 'PENDING',
                reference_id   TEXT    NOT NULL UNIQUE,
                merchant       TEXT,
                description    TEXT,
                card_last4     TEXT,
                upi_vpa        TEXT,
                created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT    PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT    NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                is_revoked INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        """)
        c.commit()

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    @staticmethod
    def _check_password(password: str, pwd_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), pwd_hash.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def _gen_account_no() -> str:
        return "".join([str(random.randint(0, 9)) for _ in range(12)])

    @staticmethod
    def _gen_reference_id() -> str:
        return "VE" + secrets.token_hex(8).upper()

    @staticmethod
    def _gen_upi_id(username: str) -> str:
        clean = "".join(c.lower() for c in username if c.isalnum())
        return f"{clean}@{UPI_SUFFIX}"

    # ── User operations ────────────────────────────────────────────────────────

    def register_user(self, username: str, full_name: str, email: str,
                      password: str, phone: str = None,
                      account_type: str = "Savings") -> dict:
        pwd_hash = self._hash_password(password)
        acc_no   = self._gen_account_no()
        upi_id   = self._gen_upi_id(username)
        c        = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                "INSERT INTO users (username, full_name, email, phone, pwd_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, full_name, email, phone, pwd_hash)
            )
            user_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]

            c.execute(
                "INSERT INTO accounts (user_id, account_no, account_type, balance, is_primary) "
                "VALUES (?, ?, ?, 0.0, 1)",
                (user_id, acc_no, account_type)
            )

            c.execute(
                "INSERT INTO upi_handles (user_id, upi_id) VALUES (?, ?)",
                (user_id, upi_id)
            )

            c.execute("COMMIT")
            return {"success": True, "account_no": acc_no, "upi_id": upi_id}
        except sqlite3.IntegrityError as e:
            c.execute("ROLLBACK")
            msg = str(e).lower()
            if "username" in msg:
                return {"success": False, "error": "Username already taken."}
            if "email" in msg:
                return {"success": False, "error": "Email already registered."}
            if "upi" in msg:
                return {"success": False, "error": "UPI handle conflict, try different username."}
            return {"success": False, "error": str(e)}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def authenticate_user(self, username: str, password: str,
                          ip_address: str = None, user_agent: str = None) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT id, username, full_name, email, phone, pwd_hash, is_active, created_at "
            "FROM users WHERE username = ? COLLATE NOCASE",
            (username,)
        ).fetchone()
        if row is None:
            return None
        if not row["is_active"]:
            return None
        if not self._check_password(password, row["pwd_hash"]):
            return None

        # Update last_login
        self._conn().execute(
            "UPDATE users SET last_login = datetime('now') WHERE id = ?",
            (row["id"],)
        )
        self._conn().commit()

        user = dict(row)
        user.pop("pwd_hash", None)

        # Get UPI handle
        upi = self._conn().execute(
            "SELECT upi_id FROM upi_handles WHERE user_id = ? AND is_active = 1",
            (user["id"],)
        ).fetchone()
        user["upi_id"] = upi["upi_id"] if upi else None

        return user

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT id, username, full_name, email, phone, is_active, created_at, last_login "
            "FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        user = dict(row)
        upi = self._conn().execute(
            "SELECT upi_id FROM upi_handles WHERE user_id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()
        user["upi_id"] = upi["upi_id"] if upi else None
        return user

    def get_user_by_upi(self, upi_id: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT u.id, u.username, u.full_name FROM users u "
            "JOIN upi_handles h ON h.user_id = u.id "
            "WHERE h.upi_id = ? AND h.is_active = 1 AND u.is_active = 1",
            (upi_id,)
        ).fetchone()
        return dict(row) if row else None

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        row = self._conn().execute(
            "SELECT pwd_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return {"success": False, "error": "User not found."}
        if not self._check_password(old_password, row["pwd_hash"]):
            return {"success": False, "error": "Current password is incorrect."}
        new_hash = self._hash_password(new_password)
        self._conn().execute(
            "UPDATE users SET pwd_hash = ? WHERE id = ?", (new_hash, user_id)
        )
        self._conn().commit()
        return {"success": True}

    def update_profile(self, user_id: int, full_name: str, phone: str) -> dict:
        self._conn().execute(
            "UPDATE users SET full_name = ?, phone = ? WHERE id = ?",
            (full_name, phone, user_id)
        )
        self._conn().commit()
        return {"success": True}

    # ── Account operations ─────────────────────────────────────────────────────

    def get_user_accounts(self, user_id: int) -> list:
        rows = self._conn().execute(
            "SELECT * FROM accounts WHERE user_id = ? ORDER BY is_primary DESC, id",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_account_by_no(self, account_no: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM accounts WHERE account_no = ?", (account_no,)
        ).fetchone()
        return dict(row) if row else None

    def get_account_by_id(self, account_id: int) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        return dict(row) if row else None

    def add_account(self, user_id: int, account_type: str = "Savings") -> dict:
        acc_no = self._gen_account_no()
        c = self._conn()
        try:
            c.execute(
                "INSERT INTO accounts (user_id, account_no, account_type, balance) "
                "VALUES (?, ?, ?, 0.0)",
                (user_id, acc_no, account_type)
            )
            c.commit()
            return {"success": True, "account_no": acc_no}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Transaction operations ─────────────────────────────────────────────────

    def deposit(self, account_id: int, amount: float,
                description: str = "Deposit", category: str = "BANK",
                reference_id: str = None) -> dict:
        if not reference_id:
            reference_id = self._gen_reference_id()
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            acc = c.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if not acc:
                raise ValueError("Account not found.")
            new_balance = round(acc["balance"] + amount, 2)
            c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, txn_category, amount, "
                "balance_after, description, reference_id) VALUES (?, 'CREDIT', ?, ?, ?, ?, ?)",
                (account_id, category, amount, new_balance, description, reference_id)
            )
            c.execute("COMMIT")
            return {"success": True, "new_balance": new_balance, "reference_id": reference_id}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def withdraw(self, account_id: int, amount: float,
                 description: str = "Withdrawal", category: str = "BANK",
                 reference_id: str = None) -> dict:
        if not reference_id:
            reference_id = self._gen_reference_id()
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            acc = c.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if not acc:
                raise ValueError("Account not found.")
            if acc["balance"] < amount:
                raise ValueError("Insufficient funds.")
            new_balance = round(acc["balance"] - amount, 2)
            c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, txn_category, amount, "
                "balance_after, description, reference_id) VALUES (?, 'DEBIT', ?, ?, ?, ?, ?)",
                (account_id, category, amount, new_balance, description, reference_id)
            )
            c.execute("COMMIT")
            return {"success": True, "new_balance": new_balance, "reference_id": reference_id}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def transfer(self, from_account_id: int, to_account_no: str,
                 amount: float, note: str = "", category: str = "TRANSFER") -> dict:
        reference_id = self._gen_reference_id()
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            src = c.execute("SELECT * FROM accounts WHERE id = ?", (from_account_id,)).fetchone()
            dst = c.execute("SELECT * FROM accounts WHERE account_no = ?", (to_account_no,)).fetchone()
            if not src:
                raise ValueError("Source account not found.")
            if not dst:
                raise ValueError(f"Destination account '{to_account_no}' not found.")
            if src["id"] == dst["id"]:
                raise ValueError("Cannot transfer to the same account.")
            if src["balance"] < amount:
                raise ValueError("Insufficient funds for this transfer.")

            src_new = round(src["balance"] - amount, 2)
            dst_new = round(dst["balance"] + amount, 2)

            c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (src_new, src["id"]))
            c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (dst_new, dst["id"]))

            desc_src = f"Transfer to ****{to_account_no[-4:]}. {note}".strip(". ")
            desc_dst = f"Transfer from ****{src['account_no'][-4:]}. {note}".strip(". ")

            c.execute(
                "INSERT INTO transactions (account_id, txn_type, txn_category, amount, "
                "balance_after, description, counterparty, reference_id) "
                "VALUES (?, 'DEBIT', ?, ?, ?, ?, ?, ?)",
                (src["id"], category, amount, src_new, desc_src, to_account_no, reference_id)
            )
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, txn_category, amount, "
                "balance_after, description, counterparty, reference_id) "
                "VALUES (?, 'CREDIT', ?, ?, ?, ?, ?, ?)",
                (dst["id"], category, amount, dst_new, desc_dst, src["account_no"], reference_id + "R")
            )
            c.execute("COMMIT")
            return {"success": True, "new_balance": src_new, "reference_id": reference_id}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def upi_transfer(self, from_account_id: int, to_upi_id: str,
                     amount: float, note: str = "") -> dict:
        """Send money via UPI VPA."""
        # Resolve UPI to account
        dst_user = self.get_user_by_upi(to_upi_id)
        if not dst_user:
            return {"success": False, "error": f"UPI ID '{to_upi_id}' not found."}

        dst_accounts = self.get_user_accounts(dst_user["id"])
        if not dst_accounts:
            return {"success": False, "error": "Recipient has no active account."}

        dst_account = next((a for a in dst_accounts if a["is_primary"]), dst_accounts[0])
        return self.transfer(
            from_account_id, dst_account["account_no"],
            amount, note=note or f"UPI to {to_upi_id}",
            category="UPI"
        )

    def get_transactions(self, account_id: int, limit: int = 100,
                         category: str = None) -> list:
        query = "SELECT * FROM transactions WHERE account_id = ?"
        params = [account_id]
        if category:
            query += " AND txn_category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn().execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_all_transactions(self, user_id: int, limit: int = 200) -> list:
        rows = self._conn().execute(
            "SELECT t.*, a.account_no, a.account_type FROM transactions t "
            "JOIN accounts a ON a.id = t.account_id "
            "WHERE a.user_id = ? ORDER BY t.created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Linked accounts ────────────────────────────────────────────────────────

    def add_linked_account(self, user_id: int, bank_name: str, account_holder: str,
                           account_no: str, ifsc_code: str,
                           account_type: str = "Savings") -> dict:
        c = self._conn()
        try:
            # Check if already linked
            existing = c.execute(
                "SELECT id FROM linked_accounts WHERE user_id = ? AND account_no = ?",
                (user_id, account_no)
            ).fetchone()
            if existing:
                return {"success": False, "error": "This account is already linked."}

            # Check how many linked accounts user has (limit 5)
            count = c.execute(
                "SELECT COUNT(*) FROM linked_accounts WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            if count >= 5:
                return {"success": False, "error": "Maximum 5 linked accounts allowed."}

            # First linked account is primary
            is_primary = 1 if count == 0 else 0
            c.execute(
                "INSERT INTO linked_accounts (user_id, bank_name, account_holder, "
                "account_no, ifsc_code, account_type, is_verified, is_primary) "
                "VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
                (user_id, bank_name, account_holder, account_no, ifsc_code, account_type, is_primary)
            )
            c.commit()
            return {"success": True, "message": "Bank account linked successfully."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_linked_accounts(self, user_id: int) -> list:
        rows = self._conn().execute(
            "SELECT * FROM linked_accounts WHERE user_id = ? ORDER BY is_primary DESC, id",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def remove_linked_account(self, user_id: int, linked_id: int) -> dict:
        c = self._conn()
        c.execute(
            "DELETE FROM linked_accounts WHERE id = ? AND user_id = ?",
            (linked_id, user_id)
        )
        c.commit()
        return {"success": True}

    # ── Payment Gateway ────────────────────────────────────────────────────────

    def process_payment(self, user_id: int, account_id: int,
                        payment_method: str, amount: float,
                        merchant: str, description: str,
                        card_last4: str = None, upi_vpa: str = None) -> dict:
        reference_id = self._gen_reference_id()
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")

            # Record gateway transaction first
            c.execute(
                "INSERT INTO gateway_transactions (user_id, account_id, payment_method, "
                "amount, status, reference_id, merchant, description, card_last4, upi_vpa) "
                "VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)",
                (user_id, account_id, payment_method, amount, reference_id,
                 merchant, description, card_last4, upi_vpa)
            )

            # Deduct from account
            acc = c.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if not acc:
                raise ValueError("Account not found.")
            if acc["balance"] < amount:
                raise ValueError("Insufficient balance for this payment.")

            new_balance = round(acc["balance"] - amount, 2)
            c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))

            desc = f"Payment to {merchant} via {payment_method}"
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, txn_category, amount, "
                "balance_after, description, reference_id) "
                "VALUES (?, 'DEBIT', 'PAYMENT', ?, ?, ?, ?)",
                (account_id, amount, new_balance, desc, reference_id)
            )

            c.execute(
                "UPDATE gateway_transactions SET status = 'SUCCESS' WHERE reference_id = ?",
                (reference_id,)
            )

            c.execute("COMMIT")
            return {
                "success": True,
                "reference_id": reference_id,
                "new_balance": new_balance
            }
        except Exception as e:
            c.execute("ROLLBACK")
            # Update gateway record as FAILED
            try:
                self._conn().execute(
                    "UPDATE gateway_transactions SET status = 'FAILED' WHERE reference_id = ?",
                    (reference_id,)
                )
                self._conn().commit()
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    def get_gateway_transactions(self, user_id: int, limit: int = 50) -> list:
        rows = self._conn().execute(
            "SELECT * FROM gateway_transactions WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Session management ─────────────────────────────────────────────────────

    def create_session(self, user_id: int, expires_hours: int = 24,
                       ip_address: str = None, user_agent: str = None) -> str:
        session_id = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).strftime("%Y-%m-%d %H:%M:%S")
        c = self._conn()
        c.execute(
            "INSERT INTO sessions (id, user_id, expires_at, ip_address, user_agent) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, expires_at, ip_address, user_agent)
        )
        c.commit()
        return session_id

    def revoke_session(self, session_id: str) -> None:
        c = self._conn()
        c.execute("UPDATE sessions SET is_revoked = 1 WHERE id = ?", (session_id,))
        c.commit()

    def revoke_all_sessions(self, user_id: int) -> None:
        c = self._conn()
        c.execute("UPDATE sessions SET is_revoked = 1 WHERE user_id = ?", (user_id,))
        c.commit()

    # ── Dashboard stats ────────────────────────────────────────────────────────

    def get_dashboard_stats(self, user_id: int) -> dict:
        accounts = self.get_user_accounts(user_id)
        total_balance = sum(a["balance"] for a in accounts)

        # Last 30 days stats
        rows = self._conn().execute(
            "SELECT txn_type, SUM(amount) as total FROM transactions t "
            "JOIN accounts a ON a.id = t.account_id "
            "WHERE a.user_id = ? AND t.created_at >= datetime('now', '-30 days') "
            "GROUP BY txn_type",
            (user_id,)
        ).fetchall()

        credits = 0.0
        debits  = 0.0
        for r in rows:
            if r["txn_type"] == "CREDIT":
                credits = r["total"]
            else:
                debits = r["total"]

        txn_count = self._conn().execute(
            "SELECT COUNT(*) FROM transactions t JOIN accounts a ON a.id = t.account_id "
            "WHERE a.user_id = ? AND t.created_at >= datetime('now', '-30 days')",
            (user_id,)
        ).fetchone()[0]

        upi = self._conn().execute(
            "SELECT upi_id FROM upi_handles WHERE user_id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()

        return {
            "total_balance": total_balance,
            "monthly_credits": credits,
            "monthly_debits": debits,
            "txn_count_30d": txn_count,
            "account_count": len(accounts),
            "upi_id": upi["upi_id"] if upi else None,
        }

    # ── Seed demo data ─────────────────────────────────────────────────────────

    def _seed_demo_data(self):
        existing = self._conn().execute(
            "SELECT id FROM users WHERE username = 'demo' COLLATE NOCASE"
        ).fetchone()
        if existing:
            return

        result = self.register_user(
            username="demo",
            full_name="Demo User",
            email="demo@payfin.fin",
            password="Demo@12345",
            phone="+91 98765 43210",
            account_type="Premium Savings",
        )
        if not result["success"]:
            return

        acc = self.get_account_by_no(result["account_no"])
        if not acc:
            return
        aid = acc["id"]

        seed_txns = [
            ("CREDIT", 50000.00, "Opening Balance — Welcome to Payfin", "BANK"),
            ("CREDIT", 75000.00, "Salary — Payfin Technologies",        "BANK"),
            ("DEBIT",  18000.00, "Rent — Green Valley Apartments",         "PAYMENT"),
            ("DEBIT",   4500.00, "Monthly Groceries — BigBasket",          "PAYMENT"),
            ("CREDIT",  8500.00, "Freelance — WebDev Project",             "BANK"),
            ("DEBIT",   1200.00, "Electricity Bill — BESCOM",              "PAYMENT"),
            ("DEBIT",    850.50, "Internet — ACT Fibernet",                "PAYMENT"),
            ("CREDIT", 75000.00, "Salary — Payfin Technologies",        "BANK"),
            ("DEBIT",  18000.00, "Rent — Green Valley Apartments",         "PAYMENT"),
            ("DEBIT",   3900.00, "Weekend Shopping — Amazon",              "PAYMENT"),
            ("CREDIT",  5000.00, "Cashback Reward — Payfin Card",       "BANK"),
            ("DEBIT",   2500.00, "Gym Membership — Cult.fit Annual",       "PAYMENT"),
            ("DEBIT",    600.00, "OTT Subscriptions",                      "PAYMENT"),
            ("CREDIT",  2000.00, "UPI Received — Rohit Sharma",            "UPI"),
            ("DEBIT",   8000.00, "Flight Tickets — IndiGo",                "PAYMENT"),
            ("CREDIT", 75000.00, "Salary — Payfin Technologies",        "BANK"),
            ("DEBIT",  18000.00, "Rent — Green Valley Apartments",         "PAYMENT"),
            ("DEBIT",   1750.00, "Restaurant — The Fatty Bao",             "PAYMENT"),
            ("CREDIT", 10000.00, "UPI Transfer — Priya Patel",             "UPI"),
            ("DEBIT",   3000.00, "Online Shopping — Flipkart",             "PAYMENT"),
        ]

        balance = 0.0
        base_dt = datetime.now() - timedelta(days=60)
        c = self._conn()
        c.execute("BEGIN IMMEDIATE")
        for i, (txn_type, amount, desc, category) in enumerate(seed_txns):
            ref = self._gen_reference_id()
            if txn_type == "CREDIT":
                balance = round(balance + amount, 2)
            else:
                if balance < amount:
                    amount = round(balance * 0.5, 2)
                balance = max(round(balance - amount, 2), 0.0)

            dt = (base_dt + timedelta(days=i * 3)).strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, txn_category, amount, "
                "balance_after, description, reference_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, txn_type, category, amount, balance, desc, ref, dt)
            )

        c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (balance, aid))
        c.execute("COMMIT")

        # Add linked bank accounts for demo
        self.add_linked_account(
            user_id=acc["user_id"],
            bank_name="State Bank of India",
            account_holder="Demo User",
            account_no="31234567890",
            ifsc_code="SBIN0001234",
            account_type="Savings"
        )
        self.add_linked_account(
            user_id=acc["user_id"],
            bank_name="HDFC Bank",
            account_holder="Demo User",
            account_no="50100123456789",
            ifsc_code="HDFC0001234",
            account_type="Current"
        )
