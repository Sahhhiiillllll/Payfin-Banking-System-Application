"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           NEXUS BANK — Production-Grade Online Banking System (GUI)          ║
║           Architecture: 3-Layer (DB | Business Logic | UI)                   ║
║           Security: PBKDF2-HMAC SHA-256, Salted Hashes, Parameterized SQL    ║
╚══════════════════════════════════════════════════════════════════════════════╝

Requirements: Python 3.8+  (only stdlib — tkinter, sqlite3, hashlib, etc.)
Run:  python banking_system.py

Test Account (pre-seeded):
  Username : alice
  Password : SecurePass@123
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
import os
import secrets
import string
import re
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import random


# ══════════════════════════════════════════════════════════════════
#  SECTION 1 — DESIGN TOKENS (Single Source of Truth)
# ══════════════════════════════════════════════════════════════════

class Theme:
    # Backgrounds
    BG_DARKEST   = "#0A0F1C"   # Near-black navy — app root
    BG_DARK      = "#0F1729"   # Primary panel bg
    BG_PANEL     = "#141E35"   # Card / sidebar bg
    BG_SURFACE   = "#1C2847"   # Input fields, table rows
    BG_ELEVATED  = "#233059"   # Hover states, selected rows

    # Accents
    GREEN        = "#00D17A"   # Credits / success
    GREEN_DIM    = "#00A35E"   # Hover green
    GREEN_FAINT  = "#003D25"   # Green tint bg
    CRIMSON      = "#FF4C6A"   # Debits / errors
    CRIMSON_FAINT= "#3D0014"   # Red tint bg
    GOLD         = "#F5C542"   # Highlight / star
    BLUE_ACCENT  = "#4A9EFF"   # Links / info

    # Text
    TEXT_PRIMARY = "#E8EEFF"
    TEXT_SECOND  = "#8A9CC8"
    TEXT_MUTED   = "#4A5680"
    TEXT_ON_GREEN= "#001A0F"

    # Borders
    BORDER       = "#1E2D52"
    BORDER_FOCUS = "#4A9EFF"

    # Fonts
    FONT_DISPLAY = ("Helvetica Neue", 28, "bold")
    FONT_HEADING = ("Helvetica Neue", 16, "bold")
    FONT_SUBHEAD = ("Helvetica Neue", 12, "bold")
    FONT_BODY    = ("Helvetica Neue", 11)
    FONT_SMALL   = ("Helvetica Neue", 9)
    FONT_MONO    = ("Courier New",    11)
    FONT_MONO_LG = ("Courier New",    14, "bold")

    # Sizing
    CORNER       = 12
    PAD          = 20
    PAD_SM       = 10


# ══════════════════════════════════════════════════════════════════
#  SECTION 2 — DATABASE LAYER
# ══════════════════════════════════════════════════════════════════

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nexus_bank.db")

class DatabaseManager:
    """
    Manages all SQLite interactions.
    - All queries use parameterised placeholders (SQL-injection immune).
    - Transfers use BEGIN IMMEDIATE … COMMIT / ROLLBACK for ACID compliance.
    - Passwords stored as PBKDF2-HMAC-SHA256 with a unique per-user salt.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()   # one connection per thread
        self._init_schema()
        self._seed_demo_data()

    # ── Connection helpers ──────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    # ── Schema ─────────────────────────────────────────────────────

    def _init_schema(self):
        c = self._conn()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                full_name   TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                pwd_hash    TEXT    NOT NULL,
                pwd_salt    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS accounts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                account_no  TEXT    NOT NULL UNIQUE,
                account_type TEXT   NOT NULL DEFAULT 'Checking',
                balance     REAL    NOT NULL DEFAULT 0.0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                CHECK (balance >= 0)
            );
            CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id);
            CREATE INDEX IF NOT EXISTS idx_accounts_no   ON accounts(account_no);

            CREATE TABLE IF NOT EXISTS transactions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id      INTEGER NOT NULL REFERENCES accounts(id),
                txn_type        TEXT    NOT NULL,
                amount          REAL    NOT NULL,
                balance_after   REAL    NOT NULL,
                description     TEXT,
                counterparty    TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_txn_date    ON transactions(created_at DESC);
        """)
        c.commit()

    # ── Security helpers ────────────────────────────────────────────

    @staticmethod
    def _gen_salt() -> str:
        return secrets.token_hex(32)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=260_000,
            dklen=32,
        )
        return dk.hex()

    @staticmethod
    def _gen_account_no() -> str:
        digits = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        return digits

    # ── User operations ─────────────────────────────────────────────

    def register_user(self, username: str, full_name: str, email: str,
                      password: str, account_type: str = "Checking") -> dict:
        salt     = self._gen_salt()
        pwd_hash = self._hash_password(password, salt)
        acc_no   = self._gen_account_no()
        c        = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                "INSERT INTO users (username, full_name, email, pwd_hash, pwd_salt) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, full_name, email, pwd_hash, salt)
            )
            user_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute(
                "INSERT INTO accounts (user_id, account_no, account_type, balance) "
                "VALUES (?, ?, ?, 0.0)",
                (user_id, acc_no, account_type)
            )
            c.execute("COMMIT")
            return {"success": True, "account_no": acc_no}
        except sqlite3.IntegrityError as e:
            c.execute("ROLLBACK")
            if "username" in str(e).lower():
                return {"success": False, "error": "Username already taken."}
            if "email" in str(e).lower():
                return {"success": False, "error": "Email already registered."}
            return {"success": False, "error": str(e)}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def authenticate_user(self, username: str, password: str) -> dict | None:
        row = self._conn().execute(
            "SELECT id, username, full_name, email, pwd_hash, pwd_salt "
            "FROM users WHERE username = ? COLLATE NOCASE",
            (username,)
        ).fetchone()
        if row is None:
            return None
        computed = self._hash_password(password, row["pwd_salt"])
        if not secrets.compare_digest(computed, row["pwd_hash"]):
            return None
        return dict(row)

    def get_user_accounts(self, user_id: int) -> list:
        rows = self._conn().execute(
            "SELECT * FROM accounts WHERE user_id = ? ORDER BY id",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_account_by_no(self, account_no: str) -> dict | None:
        row = self._conn().execute(
            "SELECT * FROM accounts WHERE account_no = ?",
            (account_no,)
        ).fetchone()
        return dict(row) if row else None

    # ── Transaction operations ──────────────────────────────────────

    def deposit(self, account_id: int, amount: float, description: str = "Deposit") -> dict:
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            acc = c.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if not acc:
                raise ValueError("Account not found.")
            new_balance = round(acc["balance"] + amount, 2)
            c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, amount, balance_after, description) "
                "VALUES (?, 'CREDIT', ?, ?, ?)",
                (account_id, amount, new_balance, description)
            )
            c.execute("COMMIT")
            return {"success": True, "new_balance": new_balance}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def withdraw(self, account_id: int, amount: float, description: str = "Withdrawal") -> dict:
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
                "INSERT INTO transactions (account_id, txn_type, amount, balance_after, description) "
                "VALUES (?, 'DEBIT', ?, ?, ?)",
                (account_id, amount, new_balance, description)
            )
            c.execute("COMMIT")
            return {"success": True, "new_balance": new_balance}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def transfer(self, from_account_id: int, to_account_no: str,
                 amount: float, note: str = "") -> dict:
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            src = c.execute("SELECT * FROM accounts WHERE id = ?", (from_account_id,)).fetchone()
            dst = c.execute("SELECT * FROM accounts WHERE account_no = ?", (to_account_no,)).fetchone()
            if not src:
                raise ValueError("Source account not found.")
            if not dst:
                raise ValueError(f"Destination account {to_account_no} not found.")
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
                "INSERT INTO transactions (account_id, txn_type, amount, balance_after, "
                "description, counterparty) VALUES (?, 'DEBIT', ?, ?, ?, ?)",
                (src["id"], amount, src_new, desc_src, to_account_no)
            )
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, amount, balance_after, "
                "description, counterparty) VALUES (?, 'CREDIT', ?, ?, ?, ?)",
                (dst["id"], amount, dst_new, desc_dst, src["account_no"])
            )
            c.execute("COMMIT")
            return {"success": True, "new_balance": src_new}
        except Exception as e:
            c.execute("ROLLBACK")
            return {"success": False, "error": str(e)}

    def get_transactions(self, account_id: int, limit: int = 100) -> list:
        rows = self._conn().execute(
            "SELECT * FROM transactions WHERE account_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (account_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        c = self._conn()
        row = c.execute(
            "SELECT pwd_hash, pwd_salt FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return {"success": False, "error": "User not found."}
        computed = self._hash_password(old_password, row["pwd_salt"])
        if not secrets.compare_digest(computed, row["pwd_hash"]):
            return {"success": False, "error": "Current password is incorrect."}
        new_salt = self._gen_salt()
        new_hash = self._hash_password(new_password, new_salt)
        c.execute(
            "UPDATE users SET pwd_hash = ?, pwd_salt = ? WHERE id = ?",
            (new_hash, new_salt, user_id)
        )
        c.commit()
        return {"success": True}

    # ── Seed demo data ──────────────────────────────────────────────

    def _seed_demo_data(self):
        existing = self._conn().execute(
            "SELECT id FROM users WHERE username = 'alice' COLLATE NOCASE"
        ).fetchone()
        if existing:
            return   # already seeded

        # Create demo user
        result = self.register_user(
            username     = "alice",
            full_name    = "Alice Reynolds",
            email        = "alice@nexusbank.demo",
            password     = "SecurePass@123",
            account_type = "Premium Checking",
        )
        if not result["success"]:
            return

        acc = self.get_account_by_no(result["account_no"])
        if not acc:
            return
        aid = acc["id"]

        # Inject rich transaction history (walk backwards 60 days)
        c    = self._conn()
        seed_txns = [
            ("CREDIT", 8500.00, "Initial Deposit — Welcome Bonus"),
            ("CREDIT", 3200.00, "Salary — NexusTech Inc."),
            ("DEBIT",  1200.00, "Rent — Greenwood Apartments"),
            ("DEBIT",   450.00, "Monthly Groceries"),
            ("CREDIT",  750.00, "Freelance Payment — ClientCo"),
            ("DEBIT",   120.00, "Electricity Bill"),
            ("DEBIT",    85.50, "Internet — FiberNet"),
            ("CREDIT", 3200.00, "Salary — NexusTech Inc."),
            ("DEBIT",  1200.00, "Rent — Greenwood Apartments"),
            ("DEBIT",   390.00, "Weekend Groceries"),
            ("CREDIT",  500.00, "Refund — Online Store"),
            ("DEBIT",   250.00, "Gym Membership — Annual"),
            ("DEBIT",    60.00, "Streaming Services"),
            ("CREDIT",  200.00, "Cash Back Reward"),
            ("DEBIT",   800.00, "Flight Tickets — MumbaiAir"),
            ("CREDIT", 3200.00, "Salary — NexusTech Inc."),
            ("DEBIT",  1200.00, "Rent — Greenwood Apartments"),
            ("DEBIT",   175.00, "Restaurant — Le Petite Bistro"),
            ("CREDIT", 1000.00, "Transfer Received — Rohan Mehta"),
            ("DEBIT",   300.00, "Online Shopping — Nexus Store"),
        ]

        balance = 0.0
        base_dt = datetime.now() - timedelta(days=60)
        c.execute("BEGIN IMMEDIATE")
        for i, (txn_type, amount, desc) in enumerate(seed_txns):
            if txn_type == "CREDIT":
                balance = round(balance + amount, 2)
            else:
                if balance < amount:
                    amount = round(balance * 0.5, 2)
                balance = round(balance - amount, 2)
                if balance < 0:
                    balance = 0.0

            dt = (base_dt + timedelta(days=i * 3)).strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT INTO transactions (account_id, txn_type, amount, balance_after, "
                "description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (aid, txn_type, amount, balance, desc, dt)
            )

        c.execute("UPDATE accounts SET balance = ? WHERE id = ?", (balance, aid))
        c.execute("COMMIT")

        # Create a second demo account for transfer testing
        result2 = self.register_user(
            username="bob",
            full_name="Bob Kumar",
            email="bob@nexusbank.demo",
            password="TestPass@456",
            account_type="Savings",
        )


# ══════════════════════════════════════════════════════════════════
#  SECTION 3 — BUSINESS LOGIC LAYER (Validation + Service calls)
# ══════════════════════════════════════════════════════════════════

class BankingService:
    """Intermediary between UI and DB. Handles validation and formatting."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ── Validators ──────────────────────────────────────────────────

    @staticmethod
    def validate_amount(raw: str) -> tuple[bool, float, str]:
        raw = raw.strip()
        try:
            val = float(Decimal(raw))
        except (InvalidOperation, ValueError):
            return False, 0.0, "Enter a valid numeric amount."
        if val <= 0:
            return False, 0.0, "Amount must be greater than zero."
        if val > 10_000_000:
            return False, 0.0, "Amount exceeds single-transaction limit."
        if round(val, 2) != val:
            val = round(val, 2)
        return True, val, ""

    @staticmethod
    def validate_password_strength(pwd: str) -> tuple[int, str]:
        """Returns (score 0-4, label)."""
        score = 0
        if len(pwd) >= 8:  score += 1
        if re.search(r"[A-Z]", pwd): score += 1
        if re.search(r"[0-9]", pwd): score += 1
        if re.search(r"[^A-Za-z0-9]", pwd): score += 1
        labels = {0: "Too weak", 1: "Weak", 2: "Fair", 3: "Good", 4: "Strong"}
        return score, labels[score]

    @staticmethod
    def fmt_currency(amount: float) -> str:
        return f"₹{amount:,.2f}"

    @staticmethod
    def mask_account(acc_no: str) -> str:
        return f"**** **** {acc_no[-4:]}"

    # ── Auth ────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict | None:
        if not username or not password:
            return None
        return self.db.authenticate_user(username.strip(), password)

    def register(self, username, full_name, email, password, confirm, acc_type) -> dict:
        if not all([username, full_name, email, password, confirm]):
            return {"success": False, "error": "All fields are required."}
        if password != confirm:
            return {"success": False, "error": "Passwords do not match."}
        score, _ = self.validate_password_strength(password)
        if score < 2:
            return {"success": False, "error": "Password is too weak. Use uppercase, numbers & symbols."}
        if not re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", email):
            return {"success": False, "error": "Invalid email format."}
        if len(username) < 3:
            return {"success": False, "error": "Username must be at least 3 characters."}
        return self.db.register_user(username.strip(), full_name.strip(), email.strip(), password, acc_type)

    # ── Banking actions ─────────────────────────────────────────────

    def deposit(self, account_id, raw_amount, description="Deposit") -> dict:
        ok, val, err = self.validate_amount(raw_amount)
        if not ok:
            return {"success": False, "error": err}
        return self.db.deposit(account_id, val, description)

    def withdraw(self, account_id, raw_amount, description="Withdrawal") -> dict:
        ok, val, err = self.validate_amount(raw_amount)
        if not ok:
            return {"success": False, "error": err}
        return self.db.withdraw(account_id, val, description)

    def transfer(self, from_account_id, to_account_no, raw_amount, note="") -> dict:
        ok, val, err = self.validate_amount(raw_amount)
        if not ok:
            return {"success": False, "error": err}
        to_account_no = to_account_no.strip()
        if not to_account_no:
            return {"success": False, "error": "Destination account number required."}
        return self.db.transfer(from_account_id, to_account_no, val, note)


# ══════════════════════════════════════════════════════════════════
#  SECTION 4 — UI HELPER WIDGETS
# ══════════════════════════════════════════════════════════════════

def styled_button(parent, text, command, style="primary", **kwargs):
    """Returns a tk.Button with theme styling."""
    styles = {
        "primary": dict(bg=Theme.GREEN,    fg=Theme.TEXT_ON_GREEN, activebackground=Theme.GREEN_DIM),
        "danger":  dict(bg=Theme.CRIMSON,  fg="#FFFFFF",           activebackground="#C0002E"),
        "ghost":   dict(bg=Theme.BG_SURFACE, fg=Theme.TEXT_SECOND, activebackground=Theme.BG_ELEVATED),
        "outline": dict(bg=Theme.BG_PANEL,   fg=Theme.GREEN,       activebackground=Theme.BG_SURFACE),
    }
    s = styles.get(style, styles["ghost"])
    return tk.Button(
        parent, text=text, command=command,
        font=Theme.FONT_SUBHEAD,
        relief="flat", cursor="hand2",
        padx=18, pady=8,
        **s, **kwargs
    )


def styled_entry(parent, show=None, **kwargs):
    e = tk.Entry(
        parent,
        bg=Theme.BG_SURFACE,
        fg=Theme.TEXT_PRIMARY,
        insertbackground=Theme.TEXT_PRIMARY,
        relief="flat",
        font=Theme.FONT_BODY,
        show=show or "",
        **kwargs
    )
    return e


def section_label(parent, text, **kwargs):
    return tk.Label(
        parent, text=text,
        bg=Theme.BG_PANEL,
        fg=Theme.TEXT_MUTED,
        font=("Helvetica Neue", 9, "bold"),
        **kwargs
    )


def card_frame(parent, **kwargs):
    return tk.Frame(parent, bg=Theme.BG_SURFACE,
                    highlightbackground=Theme.BORDER,
                    highlightthickness=1, **kwargs)


# ══════════════════════════════════════════════════════════════════
#  SECTION 5 — SPLASH SCREEN
# ══════════════════════════════════════════════════════════════════

class SplashScreen:
    PHASES = [
        (0.10, "⬡  Initializing Secure Core..."),
        (0.30, "⬡  Loading Encrypted Handshake..."),
        (0.55, "⬡  Verifying Certificate Chain..."),
        (0.75, "⬡  Connecting to Vault Engine..."),
        (0.92, "⬡  Ready."),
        (1.00, ""),
    ]

    def __init__(self, on_complete):
        self.on_complete = on_complete
        self.win = tk.Tk()
        self._setup_window()
        self._build_ui()
        self._progress = 0.0
        self._phase_idx = 0
        self._animate()
        self.win.mainloop()

    def _setup_window(self):
        w, h = 620, 360
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.overrideredirect(True)
        self.win.configure(bg=Theme.BG_DARKEST)
        self.win.lift()
        self.win.attributes("-topmost", True)

    def _build_ui(self):
        root = self.win

        # Outer border effect (1-px green frame)
        border = tk.Frame(root, bg=Theme.GREEN, padx=1, pady=1)
        border.place(relx=0.5, rely=0.5, anchor="center",
                     relwidth=0.96, relheight=0.92)
        inner = tk.Frame(border, bg=Theme.BG_DARKEST)
        inner.pack(fill="both", expand=True)

        # Logo / wordmark
        tk.Label(inner, text="N E X U S",
                 bg=Theme.BG_DARKEST, fg=Theme.GREEN,
                 font=("Helvetica Neue", 38, "bold"),
                 letterSpacing=8).pack(pady=(30, 0))
        tk.Label(inner, text="B A N K",
                 bg=Theme.BG_DARKEST, fg=Theme.TEXT_SECOND,
                 font=("Helvetica Neue", 13, "bold")).pack()
        tk.Label(inner, text="Secure · Scalable · Sophisticated",
                 bg=Theme.BG_DARKEST, fg=Theme.TEXT_MUTED,
                 font=("Helvetica Neue", 9)).pack(pady=(4, 20))

        # Status label
        self.status_var = tk.StringVar(value="")
        tk.Label(inner, textvariable=self.status_var,
                 bg=Theme.BG_DARKEST, fg=Theme.TEXT_SECOND,
                 font=("Helvetica Neue", 10)).pack(pady=(0, 10))

        # Progress bar track
        track = tk.Frame(inner, bg=Theme.BG_SURFACE, height=4)
        track.pack(fill="x", padx=60, pady=(0, 30))
        track.pack_propagate(False)
        self.bar = tk.Frame(track, bg=Theme.GREEN, height=4, width=0)
        self.bar.place(x=0, y=0, height=4)
        self._track_frame = track

        # Version tag
        tk.Label(inner, text="v2.5.1  ·  © 2025 Nexus Financial Technologies",
                 bg=Theme.BG_DARKEST, fg=Theme.TEXT_MUTED,
                 font=("Helvetica Neue", 8)).pack(side="bottom", pady=8)

        self._inner = inner
        self._track = track

    def _animate(self, step: int = 0):
        TOTAL_STEPS = 80
        if step > TOTAL_STEPS:
            self.win.after(200, self._finish)
            return

        frac = step / TOTAL_STEPS
        self._progress = frac

        # Update phase text
        for phase_frac, phase_text in self.PHASES:
            if frac >= phase_frac and phase_text:
                self.status_var.set(phase_text)

        # Resize progress bar
        self.win.update_idletasks()
        track_w = self._track_frame.winfo_width()
        bar_w = int(track_w * frac)
        self.bar.place(x=0, y=0, height=4, width=max(bar_w, 2))

        delay = 30 + int(20 * abs(0.5 - frac))  # easing
        self.win.after(delay, self._animate, step + 1)

    def _finish(self):
        # Fade out (reduce opacity if supported, else just destroy)
        try:
            for alpha in [0.9, 0.7, 0.5, 0.3, 0.1, 0.0]:
                self.win.attributes("-alpha", alpha)
                self.win.update()
                time.sleep(0.04)
        except Exception:
            pass
        self.win.destroy()
        self.on_complete()


# ══════════════════════════════════════════════════════════════════
#  SECTION 6 — AUTH VIEWS (Login + Registration)
# ══════════════════════════════════════════════════════════════════

class AuthWindow:
    def __init__(self, db: DatabaseManager, service: BankingService, on_login):
        self.db        = db
        self.service   = service
        self.on_login  = on_login

        self.root = tk.Tk()
        self.root.title("Nexus Bank — Sign In")
        self.root.configure(bg=Theme.BG_DARKEST)
        self.root.resizable(False, False)

        w, h = 480, 580
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._show_login()
        self.root.mainloop()

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    # ── Login view ──────────────────────────────────────────────────

    def _show_login(self):
        self._clear()
        root = self.root

        outer = tk.Frame(root, bg=Theme.BG_DARKEST)
        outer.pack(fill="both", expand=True, padx=40, pady=40)

        # Header
        tk.Label(outer, text="N", bg=Theme.BG_DARKEST, fg=Theme.GREEN,
                 font=("Helvetica Neue", 32, "bold")).pack()
        tk.Label(outer, text="NEXUS BANK", bg=Theme.BG_DARKEST, fg=Theme.TEXT_PRIMARY,
                 font=("Helvetica Neue", 14, "bold")).pack()
        tk.Label(outer, text="Sign in to your account",
                 bg=Theme.BG_DARKEST, fg=Theme.TEXT_SECOND,
                 font=Theme.FONT_BODY).pack(pady=(4, 28))

        # Card
        card = card_frame(outer)
        card.pack(fill="x", pady=(0, 16))
        inner = tk.Frame(card, bg=Theme.BG_SURFACE)
        inner.pack(fill="x", padx=2, pady=2)

        def field_block(parent, label_text, show=None):
            tk.Label(parent, text=label_text, bg=Theme.BG_SURFACE,
                     fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL,
                     anchor="w").pack(fill="x", padx=20, pady=(14, 2))
            e = styled_entry(parent, show=show)
            e.pack(fill="x", padx=20, ipady=7)
            sep = tk.Frame(parent, bg=Theme.BORDER, height=1)
            sep.pack(fill="x", padx=20)
            return e

        self.login_user = field_block(inner, "USERNAME")
        self.login_pass = field_block(inner, "PASSWORD", show="●")
        tk.Frame(inner, bg=Theme.BG_SURFACE, height=16).pack()

        self.login_err = tk.Label(inner, text="", bg=Theme.BG_SURFACE,
                                  fg=Theme.CRIMSON, font=Theme.FONT_SMALL)
        self.login_err.pack()

        btn = styled_button(inner, "SIGN IN", self._do_login)
        btn.pack(fill="x", padx=20, pady=(8, 20), ipady=4)

        # Hint
        hint = tk.Frame(outer, bg=Theme.BG_DARKEST)
        hint.pack()
        tk.Label(hint, text="Demo: alice / SecurePass@123",
                 bg=Theme.BG_DARKEST, fg=Theme.TEXT_MUTED,
                 font=("Helvetica Neue", 9)).pack()

        # Switch to register
        sw = tk.Frame(outer, bg=Theme.BG_DARKEST)
        sw.pack(pady=12)
        tk.Label(sw, text="No account? ", bg=Theme.BG_DARKEST,
                 fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL).pack(side="left")
        lnk = tk.Label(sw, text="Register now", bg=Theme.BG_DARKEST,
                       fg=Theme.GREEN, font=("Helvetica Neue", 9, "underline"),
                       cursor="hand2")
        lnk.pack(side="left")
        lnk.bind("<Button-1>", lambda _: self._show_register())

        # Enter key binding
        self.root.bind("<Return>", lambda _: self._do_login())
        self.login_user.focus_set()

    def _do_login(self):
        user = self.service.login(
            self.login_user.get(),
            self.login_pass.get()
        )
        if user:
            self.root.destroy()
            self.on_login(user)
        else:
            self.login_err.config(text="Invalid username or password.")

    # ── Register view ───────────────────────────────────────────────

    def _show_register(self):
        self._clear()
        root = self.root
        root.geometry(f"480x700+{(root.winfo_screenwidth()-480)//2}+{(root.winfo_screenheight()-700)//2}")

        outer = tk.Frame(root, bg=Theme.BG_DARKEST)
        outer.pack(fill="both", expand=True, padx=40, pady=30)

        tk.Label(outer, text="Create Your Account",
                 bg=Theme.BG_DARKEST, fg=Theme.TEXT_PRIMARY,
                 font=Theme.FONT_HEADING).pack(pady=(0, 20))

        card = card_frame(outer)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=Theme.BG_SURFACE)
        inner.pack(fill="x", padx=2, pady=2)

        entries = {}
        fields = [
            ("full_name", "FULL NAME", None),
            ("username",  "USERNAME",  None),
            ("email",     "EMAIL",     None),
            ("password",  "PASSWORD",  "●"),
            ("confirm",   "CONFIRM PASSWORD", "●"),
        ]
        for key, label, show in fields:
            tk.Label(inner, text=label, bg=Theme.BG_SURFACE,
                     fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL,
                     anchor="w").pack(fill="x", padx=20, pady=(12, 2))
            e = styled_entry(inner, show=show)
            e.pack(fill="x", padx=20, ipady=6)
            tk.Frame(inner, bg=Theme.BORDER, height=1).pack(fill="x", padx=20)
            entries[key] = e

        # Password strength meter
        self.strength_var = tk.StringVar(value="")
        tk.Label(inner, textvariable=self.strength_var,
                 bg=Theme.BG_SURFACE, fg=Theme.TEXT_SECOND,
                 font=Theme.FONT_SMALL, anchor="w").pack(fill="x", padx=20, pady=(4, 0))
        entries["password"].bind("<KeyRelease>", self._on_pwd_key)
        self._pwd_entry = entries["password"]

        # Account type
        tk.Label(inner, text="ACCOUNT TYPE", bg=Theme.BG_SURFACE,
                 fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL,
                 anchor="w").pack(fill="x", padx=20, pady=(12, 2))
        self.acc_type_var = tk.StringVar(value="Checking")
        type_frame = tk.Frame(inner, bg=Theme.BG_SURFACE)
        type_frame.pack(fill="x", padx=20, pady=(0, 4))
        for t in ["Checking", "Savings", "Premium"]:
            tk.Radiobutton(type_frame, text=t, variable=self.acc_type_var, value=t,
                           bg=Theme.BG_SURFACE, fg=Theme.TEXT_SECOND,
                           selectcolor=Theme.BG_ELEVATED,
                           activebackground=Theme.BG_SURFACE,
                           font=Theme.FONT_SMALL).pack(side="left", padx=(0, 12))

        self.reg_err = tk.Label(inner, text="", bg=Theme.BG_SURFACE,
                                fg=Theme.CRIMSON, font=Theme.FONT_SMALL,
                                wraplength=380, justify="left")
        self.reg_err.pack(padx=20, pady=(4, 0))

        def do_register():
            result = self.service.register(
                entries["username"].get(),
                entries["full_name"].get(),
                entries["email"].get(),
                entries["password"].get(),
                entries["confirm"].get(),
                self.acc_type_var.get(),
            )
            if result["success"]:
                messagebox.showinfo(
                    "Account Created",
                    f"Welcome! Your account number is:\n{result['account_no']}\n\nPlease sign in."
                )
                self._show_login()
            else:
                self.reg_err.config(text=result["error"])

        styled_button(inner, "CREATE ACCOUNT", do_register).pack(
            fill="x", padx=20, pady=(10, 20), ipady=4)

        sw = tk.Frame(outer, bg=Theme.BG_DARKEST)
        sw.pack(pady=10)
        tk.Label(sw, text="Already have an account? ", bg=Theme.BG_DARKEST,
                 fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL).pack(side="left")
        lnk = tk.Label(sw, text="Sign in", bg=Theme.BG_DARKEST, fg=Theme.GREEN,
                        font=("Helvetica Neue", 9, "underline"), cursor="hand2")
        lnk.pack(side="left")
        lnk.bind("<Button-1>", lambda _: self._show_login())

    def _on_pwd_key(self, _=None):
        pwd = self._pwd_entry.get()
        score, label = self.service.validate_password_strength(pwd)
        colors = ["", Theme.CRIMSON, Theme.CRIMSON, Theme.GOLD, Theme.GREEN, Theme.GREEN]
        bar = "█" * score + "░" * (4 - score)
        color = colors[score] if score < len(colors) else Theme.GREEN
        self.strength_var.set(f"Strength: {bar}  {label}")
        self._strength_label_widget = None


# ══════════════════════════════════════════════════════════════════
#  SECTION 7 — MAIN BANKING APPLICATION (Post-login)
# ══════════════════════════════════════════════════════════════════

class BankingApp:
    SIDEBAR_W = 220

    NAV_ITEMS = [
        ("🏠", "Dashboard",    "dashboard"),
        ("💸", "Transactions", "transfer"),
        ("📋", "Ledger",       "ledger"),
        ("🔐", "Security",     "security"),
    ]

    def __init__(self, user: dict, db: DatabaseManager, service: BankingService):
        self.user    = user
        self.db      = db
        self.service = service

        self.root = tk.Tk()
        self.root.title(f"Nexus Bank — {user['full_name']}")
        self.root.configure(bg=Theme.BG_DARKEST)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = min(1200, sw - 80), min(780, sh - 80)
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.root.minsize(900, 600)

        self._load_accounts()
        self._build_layout()
        self._navigate("dashboard")
        self.root.mainloop()

    def _load_accounts(self):
        self.accounts = self.db.get_user_accounts(self.user["id"])
        self.active_account = self.accounts[0] if self.accounts else None

    # ── Layout skeleton ─────────────────────────────────────────────

    def _build_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=Theme.BG_PANEL,
                                width=self.SIDEBAR_W)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Main content
        self.content_area = tk.Frame(self.root, bg=Theme.BG_DARK)
        self.content_area.pack(side="left", fill="both", expand=True)

        self._build_sidebar()

    def _build_sidebar(self):
        sb = self.sidebar

        # Bank logo
        logo_frame = tk.Frame(sb, bg=Theme.BG_PANEL, pady=20)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="⬡ NEXUS", bg=Theme.BG_PANEL, fg=Theme.GREEN,
                 font=("Helvetica Neue", 16, "bold")).pack()
        tk.Label(logo_frame, text="BANK", bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED,
                 font=("Helvetica Neue", 9)).pack()
        tk.Frame(sb, bg=Theme.BORDER, height=1).pack(fill="x", padx=16)

        # User chip
        user_chip = tk.Frame(sb, bg=Theme.BG_ELEVATED, padx=12, pady=10)
        user_chip.pack(fill="x", padx=12, pady=12)
        initials = "".join(p[0].upper() for p in self.user["full_name"].split()[:2])
        tk.Label(user_chip, text=initials, bg=Theme.GREEN, fg=Theme.TEXT_ON_GREEN,
                 font=("Helvetica Neue", 14, "bold"),
                 width=3, relief="flat").pack(side="left")
        name_frame = tk.Frame(user_chip, bg=Theme.BG_ELEVATED)
        name_frame.pack(side="left", padx=10)
        tk.Label(name_frame, text=self.user["full_name"], bg=Theme.BG_ELEVATED,
                 fg=Theme.TEXT_PRIMARY, font=("Helvetica Neue", 10, "bold"),
                 anchor="w").pack(anchor="w")
        tk.Label(name_frame, text=self.user["username"], bg=Theme.BG_ELEVATED,
                 fg=Theme.TEXT_MUTED, font=Theme.FONT_SMALL,
                 anchor="w").pack(anchor="w")

        tk.Frame(sb, bg=Theme.BORDER, height=1).pack(fill="x", padx=16, pady=(0, 8))

        # Nav buttons
        self._nav_btns = {}
        for icon, label, key in self.NAV_ITEMS:
            btn = self._nav_button(sb, icon, label, key)
            self._nav_btns[key] = btn

        # Account selector (if multiple accounts)
        if len(self.accounts) > 1:
            tk.Frame(sb, bg=Theme.BORDER, height=1).pack(fill="x", padx=16, pady=8)
            tk.Label(sb, text="ACCOUNTS", bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED,
                     font=Theme.FONT_SMALL).pack(anchor="w", padx=16)
            self.acc_var = tk.StringVar()
            menu_opts = [f"****{a['account_no'][-4:]} — {a['account_type']}" for a in self.accounts]
            self.acc_var.set(menu_opts[0])
            opt = tk.OptionMenu(sb, self.acc_var, *menu_opts, command=self._switch_account)
            opt.config(bg=Theme.BG_SURFACE, fg=Theme.TEXT_PRIMARY,
                       activebackground=Theme.BG_ELEVATED,
                       relief="flat", font=Theme.FONT_SMALL, highlightthickness=0)
            opt.pack(fill="x", padx=12, pady=4)

        # Sign out
        tk.Frame(sb, bg=Theme.BG_PANEL).pack(fill="y", expand=True)
        tk.Frame(sb, bg=Theme.BORDER, height=1).pack(fill="x", padx=16)
        styled_button(sb, "⏻  Sign Out", self._sign_out, style="ghost").pack(
            fill="x", padx=12, pady=12, ipady=4)

    def _nav_button(self, parent, icon, label, key):
        f = tk.Frame(parent, bg=Theme.BG_PANEL, cursor="hand2")
        f.pack(fill="x", padx=8, pady=2)

        lbl = tk.Label(f, text=f"  {icon}  {label}", bg=Theme.BG_PANEL,
                       fg=Theme.TEXT_SECOND, font=Theme.FONT_BODY,
                       anchor="w", padx=8, pady=10)
        lbl.pack(fill="x")

        indicator = tk.Frame(f, bg=Theme.BG_PANEL, width=3)
        indicator.place(x=0, y=0, relheight=1.0)

        def on_click(_=None, k=key):
            self._navigate(k)

        def on_enter(_=None):
            if self._active_nav != key:
                f.config(bg=Theme.BG_ELEVATED)
                lbl.config(bg=Theme.BG_ELEVATED)

        def on_leave(_=None):
            if self._active_nav != key:
                f.config(bg=Theme.BG_PANEL)
                lbl.config(bg=Theme.BG_PANEL)

        for w in (f, lbl):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

        return {"frame": f, "label": lbl, "indicator": indicator}

    def _navigate(self, key: str):
        self._active_nav = key

        # Update sidebar highlights
        for k, widgets in self._nav_btns.items():
            if k == key:
                widgets["frame"].config(bg=Theme.BG_ELEVATED)
                widgets["label"].config(bg=Theme.BG_ELEVATED,
                                        fg=Theme.GREEN, font=("Helvetica Neue", 11, "bold"))
                widgets["indicator"].config(bg=Theme.GREEN)
            else:
                widgets["frame"].config(bg=Theme.BG_PANEL)
                widgets["label"].config(bg=Theme.BG_PANEL,
                                        fg=Theme.TEXT_SECOND, font=Theme.FONT_BODY)
                widgets["indicator"].config(bg=Theme.BG_PANEL)

        # Clear content area
        for w in self.content_area.winfo_children():
            w.destroy()

        # Route
        routes = {
            "dashboard": self._page_dashboard,
            "transfer":  self._page_transfer,
            "ledger":    self._page_ledger,
            "security":  self._page_security,
        }
        routes.get(key, self._page_dashboard)()

    def _switch_account(self, selection):
        idx = [f"****{a['account_no'][-4:]} — {a['account_type']}" for a in self.accounts].index(selection)
        self.active_account = self.accounts[idx]
        self._navigate(self._active_nav)

    # ── Page: Dashboard ─────────────────────────────────────────────

    def _page_dashboard(self):
        self._active_nav = "dashboard"
        ca = self.content_area
        acc = self.active_account
        if not acc:
            tk.Label(ca, text="No accounts found.", bg=Theme.BG_DARK,
                     fg=Theme.TEXT_SECOND).pack(expand=True)
            return

        # Scrollable canvas
        canvas = tk.Canvas(ca, bg=Theme.BG_DARK, highlightthickness=0)
        vsb    = tk.Scrollbar(ca, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        frame = tk.Frame(canvas, bg=Theme.BG_DARK)
        canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        pad = Theme.PAD

        # ── Hero balance card ────────────────────────────────────────
        hero = tk.Frame(frame, bg=Theme.BG_PANEL,
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        hero.pack(fill="x", padx=pad, pady=(pad, 10))

        left = tk.Frame(hero, bg=Theme.BG_PANEL)
        left.pack(side="left", fill="both", expand=True, padx=28, pady=24)

        tk.Label(left, text=acc["account_type"].upper() + " ACCOUNT",
                 bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED,
                 font=("Helvetica Neue", 9, "bold")).pack(anchor="w")
        tk.Label(left, text=self.service.mask_account(acc["account_no"]),
                 bg=Theme.BG_PANEL, fg=Theme.TEXT_SECOND,
                 font=Theme.FONT_MONO_LG).pack(anchor="w", pady=(2, 8))
        tk.Label(left, text=self.service.fmt_currency(acc["balance"]),
                 bg=Theme.BG_PANEL, fg=Theme.GREEN,
                 font=("Helvetica Neue", 36, "bold")).pack(anchor="w")
        tk.Label(left, text="Available Balance",
                 bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED,
                 font=Theme.FONT_SMALL).pack(anchor="w", pady=(2, 0))

        # Right: quick actions
        right = tk.Frame(hero, bg=Theme.BG_PANEL)
        right.pack(side="right", padx=28, pady=24)
        tk.Label(right, text="Quick Actions", bg=Theme.BG_PANEL,
                 fg=Theme.TEXT_MUTED, font=("Helvetica Neue", 9, "bold")).pack(anchor="e")
        for lbl, cmd in [("+ Deposit", lambda: self._quick_deposit()),
                          ("− Withdraw", lambda: self._quick_withdraw()),
                          ("⇄ Transfer", lambda: self._navigate("transfer"))]:
            tk.Button(right, text=lbl, command=cmd,
                      bg=Theme.BG_SURFACE, fg=Theme.TEXT_PRIMARY,
                      activebackground=Theme.BG_ELEVATED,
                      relief="flat", cursor="hand2",
                      font=Theme.FONT_SMALL, padx=14, pady=6).pack(fill="x", pady=2)

        # ── Stats row ────────────────────────────────────────────────
        txns = self.db.get_transactions(acc["id"], limit=50)
        total_credit = sum(t["amount"] for t in txns if t["txn_type"] == "CREDIT")
        total_debit  = sum(t["amount"] for t in txns if t["txn_type"] == "DEBIT")

        stats_row = tk.Frame(frame, bg=Theme.BG_DARK)
        stats_row.pack(fill="x", padx=pad, pady=(0, 10))
        for title, value, color in [
            ("Total Credits (50 txns)", self.service.fmt_currency(total_credit), Theme.GREEN),
            ("Total Debits (50 txns)",  self.service.fmt_currency(total_debit),  Theme.CRIMSON),
            ("Transaction Count",       str(len(txns)),                          Theme.BLUE_ACCENT),
        ]:
            stat = tk.Frame(stats_row, bg=Theme.BG_PANEL,
                            highlightbackground=Theme.BORDER, highlightthickness=1)
            stat.pack(side="left", fill="both", expand=True, padx=(0, 8))
            tk.Label(stat, text=title, bg=Theme.BG_PANEL,
                     fg=Theme.TEXT_MUTED, font=("Helvetica Neue", 9)).pack(anchor="w", padx=16, pady=(14, 2))
            tk.Label(stat, text=value, bg=Theme.BG_PANEL,
                     fg=color, font=("Helvetica Neue", 18, "bold")).pack(anchor="w", padx=16, pady=(0, 14))

        # ── Mini ledger ──────────────────────────────────────────────
        tk.Label(frame, text="Recent Transactions",
                 bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                 font=Theme.FONT_HEADING).pack(anchor="w", padx=pad, pady=(10, 6))

        self._render_txn_list(frame, txns[:8], bg=Theme.BG_DARK)

    def _quick_deposit(self):
        self._show_amount_dialog("Deposit Funds", "CREDIT", lambda amt: (
            self._do_transaction("deposit", amt)
        ))

    def _quick_withdraw(self):
        self._show_amount_dialog("Withdraw Funds", "DEBIT", lambda amt: (
            self._do_transaction("withdraw", amt)
        ))

    def _show_amount_dialog(self, title, txn_type, callback):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=Theme.BG_DARK)
        dlg.resizable(False, False)
        dlg.grab_set()
        w, h = 360, 240
        dlg.geometry(f"{w}x{h}+{(self.root.winfo_x()+(self.root.winfo_width()-w)//2)}+"
                     f"{(self.root.winfo_y()+(self.root.winfo_height()-h)//2)}")

        tk.Label(dlg, text=title, bg=Theme.BG_DARK,
                 fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(pady=(20, 4))
        tk.Label(dlg, text="Enter amount (₹)",
                 bg=Theme.BG_DARK, fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL).pack()

        entry = styled_entry(dlg, width=20)
        entry.pack(pady=10, ipady=8, padx=40, fill="x")
        entry.focus_set()

        desc_entry = styled_entry(dlg, width=20)
        tk.Label(dlg, text="Description (optional)", bg=Theme.BG_DARK,
                 fg=Theme.TEXT_MUTED, font=Theme.FONT_SMALL).pack()
        desc_entry.pack(pady=(0, 8), ipady=6, padx=40, fill="x")

        err_lbl = tk.Label(dlg, text="", bg=Theme.BG_DARK,
                           fg=Theme.CRIMSON, font=Theme.FONT_SMALL)
        err_lbl.pack()

        color = Theme.GREEN if txn_type == "CREDIT" else Theme.CRIMSON

        def confirm():
            raw_amt = entry.get()
            raw_desc = desc_entry.get().strip() or title
            ok, val, err = self.service.validate_amount(raw_amt)
            if not ok:
                err_lbl.config(text=err)
                return
            if txn_type == "CREDIT":
                result = self.db.deposit(self.active_account["id"], val, raw_desc)
            else:
                result = self.db.withdraw(self.active_account["id"], val, raw_desc)
            if result["success"]:
                self.active_account["balance"] = result["new_balance"]
                dlg.destroy()
                self._navigate(self._active_nav)
            else:
                err_lbl.config(text=result["error"])

        tk.Button(dlg, text="Confirm", command=confirm,
                  bg=color, fg=Theme.TEXT_ON_GREEN if txn_type == "CREDIT" else "#FFF",
                  activebackground=Theme.GREEN_DIM, relief="flat",
                  font=Theme.FONT_SUBHEAD, pady=8, cursor="hand2").pack(
            fill="x", padx=40, pady=8)
        dlg.bind("<Return>", lambda _: confirm())

    def _do_transaction(self, action, amount):
        pass  # handled inline in dialog

    # ── Page: Transfer ──────────────────────────────────────────────

    def _page_transfer(self):
        ca = self.content_area
        pad = Theme.PAD

        scroll_canvas = tk.Canvas(ca, bg=Theme.BG_DARK, highlightthickness=0)
        scroll_canvas.pack(fill="both", expand=True)
        frame = tk.Frame(scroll_canvas, bg=Theme.BG_DARK)
        scroll_canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))

        tk.Label(frame, text="Move Money", bg=Theme.BG_DARK,
                 fg=Theme.TEXT_PRIMARY, font=("Helvetica Neue", 22, "bold")).pack(
            anchor="w", padx=pad, pady=(pad, 4))
        tk.Label(frame, text="Deposit, withdraw, or send funds to any Nexus account.",
                 bg=Theme.BG_DARK, fg=Theme.TEXT_SECOND, font=Theme.FONT_BODY).pack(
            anchor="w", padx=pad, pady=(0, pad))

        cols = tk.Frame(frame, bg=Theme.BG_DARK)
        cols.pack(fill="x", padx=pad, expand=True)

        def action_card(parent, title, icon, color, fields_cfg, btn_label, action_fn):
            card = tk.Frame(parent, bg=Theme.BG_PANEL,
                            highlightbackground=color, highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=4, anchor="n")

            header = tk.Frame(card, bg=color, pady=10)
            header.pack(fill="x")
            tk.Label(header, text=f"{icon}  {title}", bg=color,
                     fg="#FFF" if color == Theme.CRIMSON else Theme.TEXT_ON_GREEN,
                     font=("Helvetica Neue", 12, "bold")).pack(padx=16)

            body = tk.Frame(card, bg=Theme.BG_PANEL)
            body.pack(fill="x", padx=16, pady=12)

            entries = {}
            for key, label, placeholder, show in fields_cfg:
                tk.Label(body, text=label, bg=Theme.BG_PANEL,
                         fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL,
                         anchor="w").pack(fill="x", pady=(8, 2))
                e = styled_entry(body, show=show or "")
                e.pack(fill="x", ipady=7)
                e.insert(0, placeholder)
                e.config(fg=Theme.TEXT_MUTED)

                def on_focus_in(ev, entry=e, ph=placeholder):
                    if entry.get() == ph:
                        entry.delete(0, "end")
                        entry.config(fg=Theme.TEXT_PRIMARY)

                def on_focus_out(ev, entry=e, ph=placeholder):
                    if not entry.get():
                        entry.insert(0, ph)
                        entry.config(fg=Theme.TEXT_MUTED)

                e.bind("<FocusIn>", on_focus_in)
                e.bind("<FocusOut>", on_focus_out)
                entries[key] = e
                tk.Frame(body, bg=Theme.BORDER, height=1).pack(fill="x")

            err_lbl = tk.Label(body, text="", bg=Theme.BG_PANEL,
                               fg=Theme.CRIMSON, font=Theme.FONT_SMALL, wraplength=260, justify="left")
            err_lbl.pack(anchor="w", pady=(4, 0))

            def on_click():
                # Strip placeholder text
                cleaned = {}
                for k, entry in entries.items():
                    val = entry.get()
                    cleaned[k] = val if val not in [f.get() for f in []] else ""
                result = action_fn(entries, err_lbl)
                if result and result.get("success"):
                    self.active_account["balance"] = result["new_balance"]
                    self._navigate("transfer")
                elif result:
                    err_lbl.config(text=result.get("error", "Unknown error."))

            tk.Button(body, text=btn_label, command=on_click,
                      bg=color, fg="#FFF" if color == Theme.CRIMSON else Theme.TEXT_ON_GREEN,
                      activebackground=Theme.GREEN_DIM if color == Theme.GREEN else "#C0002E",
                      relief="flat", cursor="hand2",
                      font=Theme.FONT_SUBHEAD, pady=8).pack(fill="x", pady=(10, 4))

        # Deposit card
        def do_deposit(entries, err):
            raw = entries["amount"].get()
            desc = entries["desc"].get()
            if raw in ("e.g. 5000", ""):
                err.config(text="Enter a valid amount.")
                return None
            if desc == "e.g. Salary":
                desc = "Deposit"
            result = self.service.deposit(self.active_account["id"], raw, desc)
            return result

        action_card(cols, "Deposit Funds", "↓", Theme.GREEN, [
            ("amount", "AMOUNT (₹)", "e.g. 5000", None),
            ("desc",   "DESCRIPTION", "e.g. Salary", None),
        ], "Deposit →", do_deposit)

        # Withdraw card
        def do_withdraw(entries, err):
            raw = entries["amount"].get()
            desc = entries["desc"].get()
            if raw in ("e.g. 2000", ""):
                err.config(text="Enter a valid amount.")
                return None
            if desc == "e.g. ATM Withdrawal":
                desc = "Withdrawal"
            result = self.service.withdraw(self.active_account["id"], raw, desc)
            return result

        action_card(cols, "Withdraw Funds", "↑", Theme.CRIMSON, [
            ("amount", "AMOUNT (₹)", "e.g. 2000", None),
            ("desc",   "DESCRIPTION", "e.g. ATM Withdrawal", None),
        ], "Withdraw →", do_withdraw)

        # Transfer card (full width below)
        tk.Frame(frame, bg=Theme.BORDER, height=1).pack(fill="x", padx=pad, pady=10)
        tk.Label(frame, text="Peer-to-Peer Transfer",
                 bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                 font=Theme.FONT_HEADING).pack(anchor="w", padx=pad, pady=(0, 8))

        transfer_card = tk.Frame(frame, bg=Theme.BG_PANEL,
                                 highlightbackground=Theme.BLUE_ACCENT, highlightthickness=1)
        transfer_card.pack(fill="x", padx=pad, pady=(0, pad))
        tc_inner = tk.Frame(transfer_card, bg=Theme.BG_PANEL)
        tc_inner.pack(fill="x", padx=20, pady=16)

        t_entries = {}
        for key, label, ph in [
            ("to_acc", "DESTINATION ACCOUNT NUMBER", "12-digit account number"),
            ("amount", "AMOUNT (₹)",                 "e.g. 1000"),
            ("note",   "NOTE (OPTIONAL)",             "e.g. Rent payment"),
        ]:
            tk.Label(tc_inner, text=label, bg=Theme.BG_PANEL,
                     fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(10, 2))
            e = styled_entry(tc_inner)
            e.pack(fill="x", ipady=7)
            e.insert(0, ph)
            e.config(fg=Theme.TEXT_MUTED)

            def on_fi(ev, entry=e, p=ph):
                if entry.get() == p:
                    entry.delete(0, "end"); entry.config(fg=Theme.TEXT_PRIMARY)
            def on_fo(ev, entry=e, p=ph):
                if not entry.get():
                    entry.insert(0, p); entry.config(fg=Theme.TEXT_MUTED)
            e.bind("<FocusIn>", on_fi); e.bind("<FocusOut>", on_fo)
            t_entries[key] = e
            tk.Frame(tc_inner, bg=Theme.BORDER, height=1).pack(fill="x")

        t_err = tk.Label(tc_inner, text="", bg=Theme.BG_PANEL,
                         fg=Theme.CRIMSON, font=Theme.FONT_SMALL)
        t_err.pack(anchor="w", pady=(4, 0))

        def do_transfer():
            to_acc = t_entries["to_acc"].get()
            raw    = t_entries["amount"].get()
            note   = t_entries["note"].get()
            if to_acc in ("12-digit account number", ""):
                t_err.config(text="Enter a destination account number."); return
            if raw in ("e.g. 1000", ""):
                t_err.config(text="Enter a valid amount."); return
            if note == "e.g. Rent payment": note = ""
            result = self.service.transfer(self.active_account["id"], to_acc, raw, note)
            if result["success"]:
                self.active_account["balance"] = result["new_balance"]
                messagebox.showinfo("Transfer Successful",
                    f"₹{float(raw):,.2f} transferred to ****{to_acc[-4:]}.")
                self._navigate("transfer")
            else:
                t_err.config(text=result["error"])

        styled_button(tc_inner, "⇄  Send Transfer", do_transfer, style="primary").pack(
            fill="x", pady=(10, 0), ipady=5)

        # Show Bob's account as hint
        bob_accs = self.db.get_user_accounts(
            self.db._conn().execute(
                "SELECT id FROM users WHERE username='bob'"
            ).fetchone()["id"]
        )
        if bob_accs:
            tk.Label(frame,
                     text=f"Test: Bob's account → {bob_accs[0]['account_no']}",
                     bg=Theme.BG_DARK, fg=Theme.TEXT_MUTED,
                     font=("Helvetica Neue", 9)).pack(anchor="w", padx=pad, pady=(0, pad))

    # ── Page: Ledger ────────────────────────────────────────────────

    def _page_ledger(self):
        ca  = self.content_area
        acc = self.active_account
        pad = Theme.PAD

        header = tk.Frame(ca, bg=Theme.BG_DARK)
        header.pack(fill="x", padx=pad, pady=(pad, 6))
        tk.Label(header, text="Transaction Ledger",
                 bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                 font=("Helvetica Neue", 22, "bold")).pack(side="left")
        tk.Label(header, text=f"Account  {self.service.mask_account(acc['account_no'])}",
                 bg=Theme.BG_DARK, fg=Theme.TEXT_SECOND,
                 font=Theme.FONT_MONO).pack(side="right", pady=6)

        # Column headers
        cols_frame = tk.Frame(ca, bg=Theme.BG_SURFACE)
        cols_frame.pack(fill="x", padx=pad)
        for text, w, anchor in [
            ("DATE & TIME",    200, "w"),
            ("DESCRIPTION",    0,   "w"),
            ("TYPE",           80,  "center"),
            ("AMOUNT",         120, "e"),
            ("BALANCE",        120, "e"),
        ]:
            lbl = tk.Label(cols_frame, text=text, bg=Theme.BG_SURFACE,
                           fg=Theme.TEXT_MUTED, font=("Helvetica Neue", 8, "bold"),
                           padx=8, pady=8, anchor=anchor)
            if w:
                lbl.config(width=w // 8)
            else:
                lbl.pack(side="left", fill="x", expand=True, padx=4)
                continue
            lbl.pack(side="left", padx=4)

        tk.Frame(ca, bg=Theme.BORDER, height=1).pack(fill="x", padx=pad)

        # Scrollable list
        list_frame = tk.Frame(ca, bg=Theme.BG_DARK)
        list_frame.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        vsb = tk.Scrollbar(list_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        canvas = tk.Canvas(list_frame, bg=Theme.BG_DARK, highlightthickness=0,
                           yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.config(command=canvas.yview)

        inner = tk.Frame(canvas, bg=Theme.BG_DARK)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        txns = self.db.get_transactions(acc["id"], limit=200)
        self._render_txn_list(inner, txns, bg=Theme.BG_DARK, full=True)

        if not txns:
            tk.Label(inner, text="No transactions yet.", bg=Theme.BG_DARK,
                     fg=Theme.TEXT_MUTED, font=Theme.FONT_BODY).pack(pady=40)

    def _render_txn_list(self, parent, txns, bg=Theme.BG_DARK, full=False):
        for i, t in enumerate(txns):
            is_credit = t["txn_type"] == "CREDIT"
            row_bg    = bg if i % 2 == 0 else Theme.BG_SURFACE

            row = tk.Frame(parent, bg=row_bg,
                           highlightbackground=Theme.BORDER, highlightthickness=0)
            row.pack(fill="x", pady=1)

            # Date
            dt_str = t["created_at"][:16]
            tk.Label(row, text=dt_str, bg=row_bg, fg=Theme.TEXT_MUTED,
                     font=Theme.FONT_SMALL, width=18, anchor="w", padx=8, pady=10).pack(side="left")

            # Description
            desc = t["description"] or t["txn_type"]
            tk.Label(row, text=desc, bg=row_bg, fg=Theme.TEXT_PRIMARY,
                     font=Theme.FONT_SMALL, anchor="w", padx=4).pack(side="left", fill="x", expand=True)

            # Type badge
            badge_bg    = Theme.GREEN_FAINT  if is_credit else Theme.CRIMSON_FAINT
            badge_fg    = Theme.GREEN        if is_credit else Theme.CRIMSON
            badge_text  = "● CR" if is_credit else "● DR"
            tk.Label(row, text=badge_text, bg=badge_bg, fg=badge_fg,
                     font=("Helvetica Neue", 8, "bold"), padx=6, pady=3).pack(side="left", padx=8)

            # Amount
            sign   = "+" if is_credit else "−"
            amount = f"{sign}₹{t['amount']:,.2f}"
            tk.Label(row, text=amount, bg=row_bg,
                     fg=Theme.GREEN if is_credit else Theme.CRIMSON,
                     font=("Helvetica Neue", 10, "bold"), width=14, anchor="e", padx=8).pack(side="left")

            if full:
                tk.Label(row, text=f"₹{t['balance_after']:,.2f}", bg=row_bg,
                         fg=Theme.TEXT_SECOND, font=Theme.FONT_MONO, width=13, anchor="e", padx=8).pack(side="left")

    # ── Page: Security Analytics ─────────────────────────────────────

    def _page_security(self):
        ca  = self.content_area
        pad = Theme.PAD

        canvas = tk.Canvas(ca, bg=Theme.BG_DARK, highlightthickness=0)
        vsb    = tk.Scrollbar(ca, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        frame = tk.Frame(canvas, bg=Theme.BG_DARK)
        canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        tk.Label(frame, text="Account Security & Analytics",
                 bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                 font=("Helvetica Neue", 22, "bold")).pack(anchor="w", padx=pad, pady=(pad, 4))

        # Security score card
        score_card = tk.Frame(frame, bg=Theme.BG_PANEL,
                              highlightbackground=Theme.GREEN, highlightthickness=1)
        score_card.pack(fill="x", padx=pad, pady=(8, 10))

        left_s = tk.Frame(score_card, bg=Theme.BG_PANEL)
        left_s.pack(side="left", padx=24, pady=20)
        tk.Label(left_s, text="Security Score", bg=Theme.BG_PANEL,
                 fg=Theme.TEXT_MUTED, font=("Helvetica Neue", 9, "bold")).pack(anchor="w")

        # Animated score ring (canvas-based)
        ring_canvas = tk.Canvas(left_s, width=100, height=100, bg=Theme.BG_PANEL,
                                highlightthickness=0)
        ring_canvas.pack(pady=8)
        ring_canvas.create_oval(10, 10, 90, 90, outline=Theme.BG_ELEVATED, width=8)
        ring_canvas.create_arc(10, 10, 90, 90, start=90, extent=-270,
                               outline=Theme.GREEN, width=8, style="arc")
        ring_canvas.create_text(50, 50, text="94", fill=Theme.GREEN,
                                font=("Helvetica Neue", 20, "bold"))
        tk.Label(left_s, text="Excellent", bg=Theme.BG_PANEL,
                 fg=Theme.GREEN, font=("Helvetica Neue", 10, "bold")).pack()

        # Checklist
        right_s = tk.Frame(score_card, bg=Theme.BG_PANEL)
        right_s.pack(side="left", padx=24, pady=20, fill="y")
        checks = [
            (True,  "Password hashed with PBKDF2-HMAC-SHA256"),
            (True,  "Unique cryptographic salt per account"),
            (True,  "All queries use parameterised SQL"),
            (True,  "Transfers wrapped in ACID transactions"),
            (True,  "Input validation on all numeric fields"),
            (False, "Two-Factor Authentication (coming soon)"),
        ]
        for ok, text in checks:
            row = tk.Frame(right_s, bg=Theme.BG_PANEL)
            row.pack(anchor="w", pady=3)
            icon  = "✓" if ok else "○"
            color = Theme.GREEN if ok else Theme.TEXT_MUTED
            tk.Label(row, text=icon, bg=Theme.BG_PANEL, fg=color,
                     font=("Helvetica Neue", 11, "bold")).pack(side="left", padx=(0, 8))
            tk.Label(row, text=text, bg=Theme.BG_PANEL,
                     fg=Theme.TEXT_PRIMARY if ok else Theme.TEXT_MUTED,
                     font=Theme.FONT_SMALL).pack(side="left")

        # Change password
        tk.Label(frame, text="Change Password", bg=Theme.BG_DARK,
                 fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(anchor="w", padx=pad, pady=(16, 6))

        pwd_card = tk.Frame(frame, bg=Theme.BG_PANEL,
                            highlightbackground=Theme.BORDER, highlightthickness=1)
        pwd_card.pack(fill="x", padx=pad, pady=(0, pad))
        pwd_inner = tk.Frame(pwd_card, bg=Theme.BG_PANEL)
        pwd_inner.pack(fill="x", padx=20, pady=16)

        pwd_entries = {}
        for key, label in [("current", "CURRENT PASSWORD"),
                            ("new",     "NEW PASSWORD"),
                            ("confirm", "CONFIRM NEW PASSWORD")]:
            tk.Label(pwd_inner, text=label, bg=Theme.BG_PANEL,
                     fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(8, 2))
            e = styled_entry(pwd_inner, show="●")
            e.pack(fill="x", ipady=7)
            tk.Frame(pwd_inner, bg=Theme.BORDER, height=1).pack(fill="x")
            pwd_entries[key] = e

        # Strength bar for new password
        self._sec_strength_var = tk.StringVar(value="")
        tk.Label(pwd_inner, textvariable=self._sec_strength_var,
                 bg=Theme.BG_PANEL, fg=Theme.TEXT_SECOND, font=Theme.FONT_SMALL,
                 anchor="w").pack(fill="x", pady=(4, 0))

        def on_new_key(_=None):
            score, label = self.service.validate_password_strength(pwd_entries["new"].get())
            bars = "█" * score + "░" * (4 - score)
            self._sec_strength_var.set(f"Strength: {bars}  {label}")

        pwd_entries["new"].bind("<KeyRelease>", on_new_key)

        pwd_err = tk.Label(pwd_inner, text="", bg=Theme.BG_PANEL,
                           fg=Theme.CRIMSON, font=Theme.FONT_SMALL)
        pwd_err.pack(anchor="w", pady=(4, 0))

        def do_change_pwd():
            cur  = pwd_entries["current"].get()
            new  = pwd_entries["new"].get()
            conf = pwd_entries["confirm"].get()
            if new != conf:
                pwd_err.config(text="New passwords do not match."); return
            score, _ = self.service.validate_password_strength(new)
            if score < 2:
                pwd_err.config(text="New password is too weak."); return
            result = self.db.change_password(self.user["id"], cur, new)
            if result["success"]:
                pwd_err.config(text="")
                messagebox.showinfo("Success", "Password updated successfully.")
                for e in pwd_entries.values(): e.delete(0, "end")
                self._sec_strength_var.set("")
            else:
                pwd_err.config(text=result["error"])

        styled_button(pwd_inner, "Update Password", do_change_pwd, style="primary").pack(
            fill="x", pady=(12, 0), ipady=5)

        # Account info card
        tk.Label(frame, text="Account Information", bg=Theme.BG_DARK,
                 fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(anchor="w", padx=pad, pady=(16, 6))

        info_card = tk.Frame(frame, bg=Theme.BG_PANEL,
                             highlightbackground=Theme.BORDER, highlightthickness=1)
        info_card.pack(fill="x", padx=pad, pady=(0, pad))
        info_inner = tk.Frame(info_card, bg=Theme.BG_PANEL)
        info_inner.pack(fill="x", padx=20, pady=16)

        acc = self.active_account
        info_rows = [
            ("Full Name",         self.user["full_name"]),
            ("Username",          self.user["username"]),
            ("Email",             self.user["email"]),
            ("Account Number",    acc["account_no"]),
            ("Account Type",      acc["account_type"]),
            ("Member Since",      self.user["created_at"][:10]),
        ]
        for label, value in info_rows:
            row = tk.Frame(info_inner, bg=Theme.BG_PANEL)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, bg=Theme.BG_PANEL,
                     fg=Theme.TEXT_MUTED, font=Theme.FONT_SMALL, width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=Theme.BG_PANEL,
                     fg=Theme.TEXT_PRIMARY, font=Theme.FONT_BODY, anchor="w").pack(side="left")

    # ── Sign out ────────────────────────────────────────────────────

    def _sign_out(self):
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            self.root.destroy()
            launch()


# ══════════════════════════════════════════════════════════════════
#  SECTION 8 — APPLICATION ENTRY POINT
# ══════════════════════════════════════════════════════════════════

# Global singletons (created once, reused across sign-outs)
_db: DatabaseManager | None  = None
_svc: BankingService | None  = None


def launch():
    global _db, _svc
    if _db is None:
        _db  = DatabaseManager()
        _svc = BankingService(_db)

    def on_login(user: dict):
        BankingApp(user, _db, _svc)

    AuthWindow(_db, _svc, on_login)


def main():
    def after_splash():
        launch()

    SplashScreen(on_complete=after_splash)


if __name__ == "__main__":
    main()
