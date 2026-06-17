# Payfin v2 — Production Architecture Blueprint

## Executive Summary

Payfin has been refactored from a monolithic Flask + SQLite app into a **Vercel-native serverless fintech platform**:

| Layer | Before | After |
|-------|--------|-------|
| Frontend | Jinja2 + Vanilla JS | **Next.js 15 + React 19 + Tailwind** |
| API | `app.py` monolith | **Flask serverless** (`api/index.py`) |
| Database | SQLite (ephemeral on Vercel) | **PostgreSQL** (Neon/Supabase) + SQLAlchemy 2 |
| Realtime | Page refresh | **Pusher** (serverless-safe) |
| Payments | Simulated | **Aggregator layer** (Razorpay/Cashfree/Stripe) |

---

## 1. Vercel-Optimized Serverless Architecture & Database Migration

### 1.1 Why SQLite Fails on Vercel

Vercel Functions are **ephemeral**. The filesystem resets between invocations. SQLite files cannot persist. All state must live in external services: PostgreSQL, Redis, object storage.

### 1.2 PostgreSQL + SQLAlchemy Setup

**File:** `api/db.py`

```python
# Serverless: NullPool — one connection per invocation
engine = create_engine(DATABASE_POOL_URL, poolclass=NullPool, pool_pre_ping=True)

# Local dev: small QueuePool
engine = create_engine(DATABASE_POOL_URL, pool_size=5, max_overflow=10)
```

**Connection URLs:**
- `DATABASE_URL` — direct (Alembic migrations, admin)
- `DATABASE_POOL_URL` — pooled (Neon `*-pooler` host, port 6543, or Supabase transaction pooler)

**Neon example:**
```
DATABASE_URL=postgresql+psycopg://user:pass@ep-xxx.region.aws.neon.tech/payfin?sslmode=require
DATABASE_POOL_URL=postgresql+psycopg://user:pass@ep-xxx-pooler.region.aws.neon.tech/payfin?sslmode=require
```

### 1.3 Vercel Flask Entry Point

**File:** `api/index.py` exports `app` — Vercel auto-detects Flask WSGI.

**File:** `vercel.json` rewrites:
```json
{ "source": "/api/:path*", "destination": "/api/index" }
```

All routes remain prefixed `/api/*`. CORS configured in `app_factory.py` via `CORS_ORIGINS`.

### 1.4 Request Lifecycle

```
Client → Vercel Edge (CSP/HSTS headers)
      → /api/* rewrite → Python Function (api/index.py)
      → before_request: open SQLAlchemy session
      → route handler → repository
      → teardown_request: commit/rollback + close session
```

---

## 2. Frontend Modernization & Hyper-Responsiveness

### 2.1 Stack

- **Next.js 15** App Router (SSR + client islands)
- **Tailwind CSS** with Payfin design tokens (`app/globals.css`)
- **Framer Motion** micro-interactions
- **Lucide React** icons
- **Pusher-js** realtime balance/transaction updates

### 2.2 Design System

Preserved from original `static/css/style.css`:
- Background: `#050810` with teal/gold gradients
- Glass cards: `glass-card` utility (backdrop-blur + gradient border)
- Skeleton loaders: `components/skeleton.tsx` with shimmer animation
- 100% responsive: mobile sidebar collapses, grid breakpoints `sm/lg`

### 2.3 Realtime Architecture (Serverless-Safe)

WebSockets don't persist in serverless. Use **Pusher** or **Supabase Realtime**:

```
Payment API → notify_balance_update() → Pusher REST API
Frontend → useRealtime() hook → private-user-{id} channel
```

**Events:** `balance.updated`, `transaction.created`

---

## 3. Production-Grade Fintech Security & Compliance

### 3.1 MFA (TOTP)

**Files:** `api/services/mfa_service.py`, `api/routes/security.py`

- `pyotp` generates secrets
- `qrcode` renders base64 QR for authenticator apps
- Login flow: password → JWT with `mfa_verified=false` → `/api/security/mfa/verify` → new JWT

### 3.2 Webhook Security (HMAC-SHA256)

**File:** `api/services/webhook_service.py`

```python
expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
hmac.compare_digest(expected, provided_signature)
```

Endpoints: `/api/webhooks/ledger`, `/api/webhooks/razorpay`

### 3.3 Idempotency Keys

**File:** `api/middleware/idempotency.py`

- Header: `Idempotency-Key` (required on `/api/upi/send`, `/api/gateway/pay`)
- DB table `idempotency_keys` with unique `(user_id, key_hash)`
- Replays identical request → cached response; mismatched body → 422

### 3.4 Audit Logging

**File:** `api/middleware/audit.py` + `audit_logs` table

Append-only JSONB metadata for: login failures, balance changes, MFA toggles, webhooks.

---

## 4. Real-World API & Third-Party Integration

### 4.1 Payment Aggregator Layer

**File:** `api/services/payment_aggregator.py`

| Provider | Env Vars | Fallback |
|----------|----------|----------|
| Razorpay | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Internal ledger |
| Cashfree | `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY` | Internal ledger |
| Stripe | `STRIPE_SECRET_KEY` | Internal ledger |

Set `PAYMENT_PROVIDER=razorpay|cashfree|stripe|internal`

### 4.2 IFSC Validation

**File:** `api/services/ifsc_service.py`

Live lookup: `GET https://ifsc.razorpay.com/{IFSC}`

### 4.3 VPA/UPI Lookup

**File:** `api/services/vpa_service.py`

1. Internal registry (`upi_handles` table)
2. External VPAs marked `verified: false`

### 4.4 PDF Statements

**File:** `api/services/statement_service.py`

`GET /api/statements/monthly?month=6&year=2026&account_id=1`

ReportLab generates in-memory PDF stream (serverless-friendly).

---

## 5. CI/CD & Vercel Deployment

### 5.1 Deploy Steps

```bash
# 1. Provision Neon PostgreSQL + Upstash Redis + Pusher
# 2. Set env vars in Vercel (see .env.example)
# 3. Run migrations (CI or manual):
DATABASE_URL=... alembic upgrade head
# 4. Deploy:
vercel --prod
```

### 5.2 Zero-Downtime Migrations (Alembic)

**Rule:** Migrations run in CI **before** Vercel promote, never on cold start in production.

```yaml
# .github/workflows/deploy.yml (recommended)
- run: alembic upgrade head
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
- run: vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }}
```

`INIT_DB_ON_STARTUP=false` in production `vercel.json`.

### 5.3 Security Headers

Configured in `vercel.json`:
- CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- API layer adds duplicate headers via `@app.after_request`

---

## Local Development

```bash
docker compose up -d postgres redis
pip install -r api/requirements.txt
npm install
npm run db:migrate
npm run db:seed
npm run api:dev    # :5328
npm run dev        # :3000
```

Demo: `demo` / `Demo@12345`

---

## Project Structure

```
├── api/                    # Python serverless backend
│   ├── index.py            # Vercel entry
│   ├── app_factory.py      # Flask factory
│   ├── db.py               # SQLAlchemy engine
│   ├── models/             # ORM models
│   ├── repositories/       # Business logic
│   ├── routes/             # API blueprints
│   ├── middleware/         # Auth, audit, idempotency
│   └── services/           # MFA, payments, IFSC, PDF
├── app/                    # Next.js pages
├── components/             # React UI
├── alembic/                # DB migrations
├── vercel.json
└── .env.example
```
