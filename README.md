# Payfin
# *Bank Smarter. Move Faster.*

---

## 🏦 Overview

**Payfin** is a production-ready, full-stack digital banking web application built with Flask + Vanilla HTML/CSS/JS.

| Item | Value |
|------|-------|
| Company | Payfin |
| UPI Handle | `username@payfin` |
| Currency | INR (₹) |
| Stack | Python 3.11, Flask, SQLite, Vanilla JS |

---

## ✨ Features

- 🔐 **Real-world Auth** — bcrypt hashed passwords, JWT tokens, HTTP-only cookies
- 👤 **Sign Up / Sign In** — Full registration with validation & password strength meter
- ⚡ **UPI Payments** — Unique `@payfin` handle per user, real-time VPA lookup
- 🔗 **Link Bank Accounts** — Add up to 5 external accounts with IFSC validation
- 💳 **Payment Gateway** — UPI / Card / Net Banking / Wallet payment simulation
- 📋 **Transaction History** — Filter, search, and export CSV ledger
- 📊 **Dashboard** — Real-time balance, 30-day stats, recent transactions
- 🔑 **Security Center** — Change password, profile edit, session management
- 🛡️ **Production Security** — Rate limiting, security headers, CSRF, parameterized SQL

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your SECRET_KEY and JWT_SECRET_KEY
```

### 3. Run development server
```bash
python app.py
```

Open **http://localhost:5000**

### Demo credentials
| Username | Password |
|----------|----------|
| `demo`   | `Demo@12345` |

---

## 🐳 Docker Deployment

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🖥️ Production Deployment (Gunicorn)

```bash
gunicorn -c gunicorn.conf.py app:app
```

---

## 🌐 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create new account |
| POST | `/api/auth/login` | Sign in, returns JWT |
| POST | `/api/auth/logout` | Invalidate session |
| GET  | `/api/auth/me` | Get current user |

### Banking
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/accounts` | List all accounts |
| POST | `/api/transactions/deposit` | Deposit funds |
| POST | `/api/transactions/withdraw` | Withdraw funds |
| POST | `/api/transactions/transfer` | Account-to-account transfer |
| GET  | `/api/transactions` | Full transaction history |

### UPI
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/upi/handle` | Get your UPI ID |
| GET  | `/api/upi/lookup/:handle` | Resolve UPI → user |
| POST | `/api/upi/send` | Send money via UPI |

### Linked Accounts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/linked-accounts` | List linked banks |
| POST | `/api/linked-accounts/add` | Link a bank account |
| DELETE | `/api/linked-accounts/:id` | Remove linked account |

### Payment Gateway
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/gateway/pay` | Process payment |
| GET  | `/api/gateway/history` | Payment history |

---

## 🔐 Security Architecture

| Layer | Implementation |
|-------|---------------|
| Password Hashing | bcrypt (cost factor 12) |
| Session Tokens | JWT HS256 (24h expiry) |
| Rate Limiting | Flask-Limiter (5/min on auth) |
| SQL Injection | 100% parameterized queries |
| XSS Prevention | Jinja2 auto-escaping + CSP |
| CSRF | SameSite cookies + token validation |
| Transport | HTTPS (production), Security headers |

---

## 📁 Project Structure

```
Banking System/
├── app.py                  # Main Flask application & all routes
├── database.py             # Production DB layer (SQLite + bcrypt)
├── config.py               # Environment configuration
├── requirements.txt        # Python dependencies
├── gunicorn.conf.py        # Production server config
├── Dockerfile              # Container definition
├── docker-compose.yml      # Docker Compose
├── .env.example            # Environment variable template
├── templates/
│   ├── base.html           # Base template
│   ├── index.html          # Landing page
│   ├── login.html          # Sign in
│   ├── register.html       # Sign up
│   ├── sidebar.html        # Navigation sidebar
│   ├── dashboard.html      # Main dashboard
│   ├── transactions.html   # Transaction history
│   ├── upi.html            # UPI payments
│   ├── linked_accounts.html# Linked bank accounts
│   ├── payment_gateway.html# Payment gateway
│   ├── security.html       # Security & settings
│   └── 404.html / 500.html # Error pages
└── static/
    ├── css/style.css       # Complete design system
    └── js/
        ├── app.js          # Core utilities (API, Toast, Modal)
        ├── auth.js         # Login/Register logic
        └── dashboard.js    # Dashboard logic
```

---

## 🏢 Company Information

**Payfin**
- GSTIN: 07AABCV1234M1ZX
- RBI Reg. No.: NBFC-2025-VE-001
- Tagline: *Bank Smarter. Move Faster.*

© 2026 Payfin All rights reserved.
