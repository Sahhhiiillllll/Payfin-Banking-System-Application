<div align="center">
  <h1>🏦 Payfin</h1>
  <p><strong>India's next-generation digital banking platform</strong></p>
  <p>UPI payments · Real-time transfers · Bank-grade security · MFA · Audit logs</p>

  ![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
  ![Flask](https://img.shields.io/badge/Flask-3.0-blue?logo=flask)
  ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)
  ![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)
  ![Python](https://img.shields.io/badge/Python-3.12-yellow?logo=python)
  ![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)
</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Environment Variables](#-environment-variables)
- [Local Development](#-local-development)
- [Database Setup](#-database-setup)
- [Deploying to Vercel](#-deploying-to-vercel)
- [API Reference](#-api-reference)
- [Security](#-security)
- [Production Checklist](#-production-checklist)

---

## 🌟 Overview

Payfin is a full-stack digital banking application built for the Indian market. It provides:

- **UPI payments** — send/receive money via UPI IDs
- **Multi-account management** — Savings, Checking, Current, Premium
- **Real-time balance updates** — powered by Pusher or Supabase Realtime
- **TOTP-based MFA** — Google Authenticator / Authy compatible
- **Immutable audit logs** — every sensitive action is recorded
- **Payment gateway integration** — Razorpay, Cashfree, Stripe
- **Bank statement PDF generation** — ReportLab-powered statements
- **IFSC & VPA verification** — before every transfer
- **Idempotent transactions** — safe retry support for all financial operations

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Auth + MFA** | JWT authentication with TOTP (Google Authenticator) |
| 💳 **Multi-Account** | Up to 3 bank accounts per user (Savings / Checking / Current) |
| 💸 **UPI Transfers** | Send money via UPI ID with VPA verification |
| 🏧 **Deposit & Withdraw** | Instant credits and debits with balance tracking |
| 🔁 **Account Transfer** | Transfer between internal accounts |
| 🌐 **Linked Banks** | Add and verify external bank accounts via IFSC |
| 📄 **PDF Statements** | Generate downloadable bank statements by date range |
| 📡 **Realtime Notifications** | Live balance and transaction updates via Pusher |
| 🛡️ **Audit Logs** | Immutable append-only log of all financial actions |
| ♻️ **Idempotency** | All write endpoints accept `Idempotency-Key` header |
| 📊 **Dashboard Stats** | Total balance, monthly spend, transaction counts |
| 🔒 **Rate Limiting** | Redis-backed request throttling via Flask-Limiter |
| 🔑 **Webhook Verification** | HMAC-signed webhooks from Razorpay / Cashfree |

---

## 🛠 Tech Stack

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS |
| Fonts | Inter + JetBrains Mono (Google Fonts) |
| HTTP Client | Native `fetch` with JWT Bearer |

### Backend
| Layer | Technology |
|---|---|
| Framework | Flask 3.0 (Python 3.12) |
| ORM | SQLAlchemy 2.0 (async-ready) |
| DB Driver | pg8000 (pure Python, Vercel-compatible) |
| Migrations | Alembic |
| Auth | PyJWT + bcrypt |
| MFA | pyotp (TOTP RFC 6238) |
| Rate Limiting | Flask-Limiter + Redis/Upstash |
| PDF | ReportLab |
| QR Codes | qrcode + Pillow |
| Realtime | Pusher (HTTP API, serverless-safe) |
| Payments | Razorpay / Cashfree / Stripe |

### Infrastructure
| Layer | Technology |
|---|---|
| Hosting | Vercel (Next.js + Python Serverless) |
| Database | Neon (PostgreSQL 16, serverless) |
| Cache / Queue | Upstash (Redis, serverless) |
| Realtime | Pusher / Supabase Realtime |
| CI/CD | Vercel Git Integration |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Vercel Edge Network                      │
│  ┌────────────────────────┐   ┌────────────────────────────┐    │
│  │   Next.js Frontend     │   │   Python Serverless API    │    │
│  │   (Static + SSR)       │   │   api/index.py → Flask     │    │
│  │                        │   │                            │    │
│  │  app/                  │   │  /api/auth/*               │    │
│  │  ├── layout.tsx        │   │  /api/accounts/*           │    │
│  │  ├── page.tsx          │   │  /api/transactions/*       │    │
│  │  └── (dashboard)/*     │   │  /api/upi/*                │    │
│  │                        │   │  /api/gateway/*            │    │
│  │  lib/api.ts            │   │  /api/security/*           │    │
│  │  (typed HTTP client)   │   │  /api/webhooks/*           │    │
│  │                        │   │  /api/statements/*         │    │
│  └────────┬───────────────┘   └────────────┬───────────────┘    │
│           │  /api/* → rewrites             │                    │
└───────────┼────────────────────────────────┼───────────────────-┘
            │                                │
            ▼                                ▼
┌───────────────────────┐    ┌───────────────────────────────────┐
│   Neon PostgreSQL     │    │         External Services         │
│   (Serverless PG 16)  │    │                                   │
│                       │    │  Pusher       → Realtime events   │
│   tables:             │    │  Upstash      → Rate limit cache  │
│   ├── users           │    │  Razorpay     → Payment gateway   │
│   ├── accounts        │    │  Cashfree     → Payment gateway   │
│   ├── transactions    │    │  Stripe       → Payment gateway   │
│   ├── upi_handles     │    │  IFSC API     → Bank verification │
│   ├── linked_accounts │    │  NPCI VPA API → UPI verification  │
│   ├── audit_logs      │    │                                   │
│   ├── idempotency_keys│    └───────────────────────────────────┘
│   ├── webhook_events  │
│   └── sessions        │
└───────────────────────┘
```

### Request Flow

```
User Browser
    │
    ├─── GET /dashboard     → Next.js SSR/CSR page
    │
    └─── POST /api/auth/login
              │
              ▼
         vercel.json rewrite → api/index.py (Flask WSGI)
              │
              ├── middleware/auth.py     (JWT decode)
              ├── middleware/audit.py    (audit log)
              ├── routes/auth.py        (handler)
              ├── repositories/banking.py (DB logic)
              └── db.py → Neon PostgreSQL (pg8000 + NullPool)
```

### Serverless Cold Start Strategy

- **NullPool** — no persistent connections across Vercel invocations
- **pg8000** — pure Python driver, zero native compilation needed on Vercel
- **`INIT_DB_ON_STARTUP=false`** — schema managed by Alembic, not on startup
- **Upstash Redis** — serverless Redis for rate limiting (no persistent connections)
- **Pusher HTTP API** — stateless realtime events (no WebSocket server needed)

---

## 📁 Project Structure

```
payfin/
├── api/                          # Python Flask API (Vercel Serverless)
│   ├── index.py                  # Vercel entry point — exports `app`
│   ├── app_factory.py            # Flask app factory, CORS, error handlers
│   ├── config.py                 # All env-var config with pg8000 normalization
│   ├── db.py                     # SQLAlchemy engine, session, health check
│   ├── requirements.txt          # Python dependencies
│   ├── utils.py                  # Shared validators (amount, email, IFSC)
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py               # User, UpiHandle, SessionRecord
│   │   ├── account.py            # Account, LinkedAccount
│   │   ├── transaction.py        # Transaction, GatewayTransaction
│   │   └── security.py           # AuditLog, IdempotencyKey, WebhookEvent
│   │
│   ├── routes/                   # Flask Blueprints
│   │   ├── __init__.py           # register_routes()
│   │   ├── auth.py               # /api/auth/* (register, login, me, logout)
│   │   ├── accounts.py           # /api/accounts/*, /api/dashboard/stats
│   │   ├── transactions.py       # /api/transactions/* (deposit, withdraw, transfer)
│   │   ├── upi.py                # /api/upi/* (send, verify VPA)
│   │   ├── gateway.py            # /api/gateway/* (pay via aggregator)
│   │   ├── security.py           # /api/security/* (MFA setup, enable, verify)
│   │   ├── webhooks.py           # /api/webhooks/* (Razorpay, Cashfree)
│   │   └── statements.py         # /api/statements/* (PDF download)
│   │
│   ├── repositories/
│   │   └── banking.py            # All DB operations (ACID, idempotency)
│   │
│   ├── services/
│   │   ├── mfa_service.py        # TOTP generation and verification
│   │   ├── ifsc_service.py       # IFSC bank code verification
│   │   ├── vpa_service.py        # UPI VPA (Virtual Payment Address) lookup
│   │   ├── payment_aggregator.py # Razorpay / Cashfree / Stripe abstraction
│   │   ├── realtime_service.py   # Pusher event publishing
│   │   ├── statement_service.py  # PDF statement generation
│   │   └── webhook_service.py    # Webhook HMAC signature verification
│   │
│   └── middleware/
│       ├── auth.py               # JWT decorators (api_login_required)
│       └── audit.py              # Immutable audit log writer
│
├── app/                          # Next.js App Router pages
│   ├── layout.tsx                # Root layout (fonts, metadata)
│   ├── page.tsx                  # Landing / home page
│   └── globals.css               # Tailwind + CSS custom properties
│
├── lib/
│   └── api.ts                    # Typed fetch client for all API endpoints
│
├── alembic/                      # Database migrations
│   ├── env.py                    # Migration environment (loads Config)
│   └── versions/
│       └── 001_initial_schema.py # Full initial schema migration
│
├── alembic.ini                   # Alembic configuration
├── vercel.json                   # Vercel deployment config
├── next.config.ts                # Next.js config (dev proxy, production)
├── package.json                  # Node.js dependencies
├── tailwind.config.ts            # Tailwind configuration
├── tsconfig.json                 # TypeScript configuration
├── requirements.txt              # Root-level (Vercel Python runtime discovery)
└── .env.example                  # Environment variable template
```

---

## 🔑 Environment Variables

Copy `.env.example` to `.env.local` for local development.
For production, add all variables in **Vercel Dashboard → Project → Settings → Environment Variables**.

### Required Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Flask secret key (min 32 chars) | `openssl rand -hex 32` |
| `JWT_SECRET_KEY` | JWT signing secret (min 32 chars) | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:pass@host/db` |
| `DATABASE_POOL_URL` | Pooled connection (Neon pooler) | `postgresql://user:pass@pooler/db` |
| `FLASK_ENV` | `production` or `development` | `production` |

> **Driver note:** Use plain `postgresql://` URLs. Payfin automatically injects the `pg8000` driver — no need to specify `+psycopg2` or `+pg8000` manually.

### Optional Variables

| Variable | Description | Default |
|---|---|---|
| `REDIS_URL` | Upstash Redis URL for rate limiting | In-memory fallback |
| `RATELIMIT_STORAGE_URI` | Same as `REDIS_URL` | `memory://` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `FRONTEND_URL` | Your Vercel deployment URL | `http://localhost:3000` |
| `PUSHER_APP_ID` | Pusher app ID for realtime | Disabled if unset |
| `PUSHER_KEY` | Pusher key | — |
| `PUSHER_SECRET` | Pusher secret | — |
| `PUSHER_CLUSTER` | Pusher cluster region | `ap2` |
| `RAZORPAY_KEY_ID` | Razorpay key ID | Internal fallback |
| `RAZORPAY_KEY_SECRET` | Razorpay secret | — |
| `CASHFREE_APP_ID` | Cashfree app ID | — |
| `CASHFREE_SECRET_KEY` | Cashfree secret | — |
| `STRIPE_SECRET_KEY` | Stripe secret key | — |
| `PAYMENT_PROVIDER` | `razorpay` / `cashfree` / `stripe` | `razorpay` |
| `MFA_ISSUER` | TOTP issuer name in authenticator apps | `Payfin` |
| `WEBHOOK_SECRET` | HMAC secret for webhook verification | Random string |
| `INIT_DB_ON_STARTUP` | Auto-create tables on cold start | `false` |
| `UPI_SUFFIX` | UPI ID domain suffix | `payfin` |
| `JWT_EXPIRY_HOURS` | JWT token lifetime in hours | `24` |

---

## 💻 Local Development

### Prerequisites

- Node.js 20+
- Python 3.12+
- PostgreSQL 14+ (local) or a [Neon](https://neon.tech) free tier account

### 1. Clone & install

```bash
git clone https://github.com/Sahhhiiillllll/Payfin-----Banking-System-Application.git
cd Payfin-----Banking-System-Application

# Frontend
npm install

# Backend
cd api
pip install -r requirements.txt
cd ..
```

### 2. Configure environment

```bash
cp .env.example .env.local
# Edit .env.local with your DATABASE_URL and SECRET_KEY
```

### 3. Run database migrations

```bash
# From repo root
alembic upgrade head
```

### 4. Start both servers

**Terminal 1 — Flask API (port 5001):**
```bash
cd api
FLASK_APP=index.py FLASK_DEBUG=true flask run --port 5001
```

**Terminal 2 — Next.js frontend (port 3000):**
```bash
npm run dev
```

Visit **http://localhost:3000** — the Next.js dev server proxies `/api/*` to Flask on port 5001.

---

## 🗄 Database Setup

### Using Neon (recommended for Vercel)

1. Create a free project at [neon.tech](https://neon.tech)
2. Copy the **Connection String** from the dashboard
3. Set `DATABASE_URL` and `DATABASE_POOL_URL` in your environment
4. Run migrations:

```bash
DATABASE_URL="postgresql://user:pass@ep-xxx.region.aws.neon.tech/payfin?sslmode=require" \
  alembic upgrade head
```

### Using Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Use the **Session Mode** connection string (port 5432) for `DATABASE_URL`
3. Use the **Transaction Mode** pooler string (port 6543) for `DATABASE_POOL_URL`

### Schema overview

| Table | Purpose |
|---|---|
| `users` | User accounts, hashed passwords, MFA secrets |
| `accounts` | Bank accounts (Savings/Checking/Current/Premium) |
| `upi_handles` | UPI IDs linked to users |
| `linked_accounts` | Verified external bank accounts |
| `transactions` | All credits, debits, transfers |
| `gateway_transactions` | Payment gateway order records |
| `audit_logs` | Immutable audit trail |
| `idempotency_keys` | Idempotent transaction deduplication |
| `webhook_events` | Incoming webhook event log |
| `sessions` | Active JWT session tracking |

---

## 🚀 Deploying to Vercel

### Step 1 — Push to GitHub

```bash
git add .
git commit -m "feat: production-ready Vercel deployment"
git push origin main
```

### Step 2 — Import project on Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Framework preset: **Next.js** (auto-detected)
4. Leave Build Command and Install Command as defaults

### Step 3 — Add environment variables

In Vercel Dashboard → Project → **Settings → Environment Variables**, add:

```
SECRET_KEY          = <output of: openssl rand -hex 32>
JWT_SECRET_KEY      = <output of: openssl rand -hex 32>
DATABASE_URL        = postgresql://user:pass@ep-xxx.neon.tech/payfin?sslmode=require
DATABASE_POOL_URL   = postgresql://user:pass@ep-xxx-pooler.neon.tech/payfin?sslmode=require
FLASK_ENV           = production
NODE_ENV            = production
CORS_ORIGINS        = https://your-project.vercel.app,http://localhost:3000
FRONTEND_URL        = https://your-project.vercel.app
INIT_DB_ON_STARTUP  = false
```

Add any optional variables (Redis, Pusher, Razorpay) as needed.

### Step 4 — Run initial migration

```bash
DATABASE_URL="<your neon url>" alembic upgrade head
```

### Step 5 — Deploy

Click **Deploy** in Vercel or push to `main`. Vercel will:
1. Run `npm install` + `npm run build` for the Next.js frontend
2. Package `api/index.py` as a Python 3.12 serverless function
3. Route all `/api/*` requests to the Flask WSGI app via `vercel.json`

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/register` | Create account | No |
| POST | `/api/auth/login` | Login (returns JWT) | No |
| GET | `/api/auth/me` | Get current user | JWT |
| POST | `/api/auth/logout` | Invalidate session | JWT |

### Accounts

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/accounts` | List user accounts | JWT |
| POST | `/api/accounts/add` | Add new account | JWT |
| GET | `/api/accounts/<id>/stats` | Account statistics | JWT |
| GET | `/api/linked-accounts` | External linked banks | JWT |
| POST | `/api/linked-accounts/add` | Link external bank | JWT |
| DELETE | `/api/linked-accounts/<id>` | Remove linked bank | JWT |
| GET | `/api/dashboard/stats` | Dashboard summary | JWT |
| PUT | `/api/user/profile` | Update profile | JWT |
| POST | `/api/user/change-password` | Change password | JWT |

### Transactions

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/transactions` | All transactions (paginated) | JWT |
| GET | `/api/transactions/account/<id>` | Account transactions | JWT |
| POST | `/api/transactions/deposit` | Deposit funds | JWT |
| POST | `/api/transactions/withdraw` | Withdraw funds | JWT |
| POST | `/api/transactions/transfer` | Internal transfer | JWT |

### UPI

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/upi/send` | Send via UPI ID | JWT + Idempotency-Key |
| POST | `/api/upi/verify-vpa` | Verify VPA exists | JWT |

### Payment Gateway

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/gateway/pay` | Create payment order | JWT + Idempotency-Key |

### Security / MFA

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/security/mfa/setup` | Get TOTP secret + QR | JWT |
| POST | `/api/security/mfa/enable` | Enable MFA | JWT |
| POST | `/api/security/mfa/verify` | Verify TOTP code | JWT (MFA pending) |

### Webhooks

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/webhooks/razorpay` | Razorpay payment webhook |
| POST | `/api/webhooks/cashfree` | Cashfree payment webhook |

### Statements

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/statements/download` | Download PDF statement | JWT |

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Service + DB connectivity |

---

## 🔒 Security

Payfin implements multiple layers of security:

- **bcrypt (rounds=12)** — all passwords hashed with bcrypt, never stored plaintext
- **TOTP MFA** — RFC 6238 compliant one-time passwords via pyotp
- **JWT with expiry** — short-lived tokens (24h default), stored in HttpOnly cookies
- **Idempotency keys** — SHA-256 keyed deduplication prevents double-charges
- **Immutable audit log** — append-only `audit_logs` table for all financial actions
- **Rate limiting** — per-IP limits via Flask-Limiter + Upstash Redis
- **HMAC webhook verification** — Razorpay and Cashfree webhook signatures validated
- **CORS** — origin whitelist configured per environment
- **Security headers** — HSTS, X-Frame-Options, CSP, etc. via both Flask and vercel.json
- **ACID transactions** — all balance mutations use SQLAlchemy transactions with rollback
- **Input validation** — all user inputs validated and sanitised before DB queries
- **NullPool** — no connection leaks across serverless invocations

---

## ✅ Production Checklist

Before going live, ensure:

- [ ] `SECRET_KEY` and `JWT_SECRET_KEY` are random 32+ char strings (not defaults)
- [ ] `FLASK_ENV=production` and `FLASK_DEBUG=False`
- [ ] `DATABASE_URL` points to a real PostgreSQL database (Neon / Supabase)
- [ ] `INIT_DB_ON_STARTUP=false` — schema managed by Alembic only
- [ ] Alembic migrations have been run: `alembic upgrade head`
- [ ] `CORS_ORIGINS` contains only your production domain(s)
- [ ] `REDIS_URL` set for persistent rate limiting (Upstash recommended)
- [ ] `WEBHOOK_SECRET` is a random secret (required if using Razorpay/Cashfree webhooks)
- [ ] SSL is enforced on your database connection (`?sslmode=require`)
- [ ] Vercel environment variables are set for **Production** environment scope
- [ ] Custom domain configured in Vercel (optional but recommended)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <p>Built with ❤️ for the Indian fintech ecosystem</p>
  <p>
    <a href="https://neon.tech">Neon</a> ·
    <a href="https://vercel.com">Vercel</a> ·
    <a href="https://upstash.com">Upstash</a> ·
    <a href="https://pusher.com">Pusher</a>
  </p>
</div>
