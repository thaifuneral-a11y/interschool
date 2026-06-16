# International Student Care OS

A production-ready student wellbeing and support platform for international schools — built with **FastAPI + Next.js 15**.

---

## Architecture

```
┌─────────────────────┐     HTTPS      ┌──────────────────────────┐
│   Next.js 15 (PWA)  │  ──────────►  │  FastAPI (Python 3.12)   │
│   Vercel            │               │  Railway                  │
└─────────────────────┘               └────────────┬─────────────┘
                                                    │ asyncpg
                                       ┌────────────▼─────────────┐
                                       │   PostgreSQL (Supabase)   │
                                       └──────────────────────────┘
```

**Stack:** Next.js 15 · TypeScript · TailwindCSS · TanStack Query · React Hook Form · FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · PostgreSQL · JWT · Google OAuth · SendGrid · Firebase FCM

---

## Modules

| Module | Description |
|--------|-------------|
| **Authentication** | Email/password + Google OAuth, JWT refresh tokens, RBAC, invite system |
| **Student Management** | Profiles, emergency contacts, medical summaries, parent links |
| **Attendance** | Daily roll, bulk marking, excused absences, parent explanation workflow |
| **Parent Portal** | Attendance view, school announcements, parent-teacher meeting booking |
| **Counseling** | Referrals, session logs, follow-up reminders, dashboard |
| **Safeguarding** | Incident reporting, risk classification (Low/Medium/High/Critical), escalation, case tracking |
| **Notifications** | In-app, email (SendGrid), push (Firebase FCM) |
| **Dashboard** | KPI cards, 30-day attendance trend chart, at-risk students panel |
| **Admin Console** | Multi-school management (Super Admin only) |

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (or Docker)

### 1. Clone & configure

```bash
git clone https://github.com/your-org/intersos.git
cd intersos
cp .env.example .env
# Edit .env with your values
```

### 2. Backend

```bash
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run DB migrations
alembic upgrade head

# Start API
uvicorn appintersos:app --reload --host 0.0.0.0 --port 8000
# API docs → http://localhost:8000/api/docs
```

### 3. Frontend

```bash
cd web
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
# App → http://localhost:3000
```

### 4. Docker (all-in-one)

```bash
docker compose up --build
# API → http://localhost:8000/api/docs
# App → http://localhost:3000
```

### 5. Tests

```bash
# From project root (with venv active)
pytest tests/ -v
```

---

## Deployment

### Backend → Railway

1. Create a new **Railway** project and connect your repo.
2. Set the start command: `uvicorn appintersos:app --host 0.0.0.0 --port $PORT`
3. Add all environment variables from `.env.example` in Railway's Variables panel.
4. The `DATABASE_URL` should point to your **Supabase** PostgreSQL instance.
5. On first deploy, run migrations via Railway's CLI: `railway run alembic upgrade head`

### Frontend → Vercel

1. Import the `/web` directory into **Vercel**.
2. Set the root directory to `web`.
3. Add environment variable: `NEXT_PUBLIC_API_URL=https://your-api.railway.app`
4. Deploy. Vercel auto-detects Next.js.

### Database → Supabase

1. Create a new Supabase project.
2. Copy the **Connection string** (Transaction pooler, port 5432) from Database Settings.
3. Use it as `DATABASE_URL` (replace `postgresql://` with `postgresql+asyncpg://`).
4. Enable **Row Level Security** and use `set_config('app.school_id', ...)` for multi-tenancy.

---

## Roles & Permissions

| Role | Students | Attendance | Counseling | Safeguarding | Admin |
|------|:---:|:---:|:---:|:---:|:---:|
| Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| School Admin | ✅ | ✅ | ✅ | ✅ | ❌ |
| Principal | ✅ | ✅ | ✅ | ✅ | ❌ |
| Teacher | ✅ | ✅ | Read | Read | ❌ |
| Counselor | ✅ | Read | ✅ | ✅ | ❌ |
| Parent | Own child | Own child | ❌ | ❌ | ❌ |
| Student | Own profile | Own | ❌ | ❌ | ❌ |

---

## Project Structure

```
intersos/
├── appintersos.py          # FastAPI app factory
├── requirements.txt
├── alembic.ini
├── docker-compose.yml
├── .env.example
│
├── api/
│   ├── core/
│   │   ├── config.py       # Pydantic settings
│   │   ├── database.py     # Async SQLAlchemy engine
│   │   ├── security.py     # JWT, bcrypt, Google OAuth
│   │   └── dependencies.py # FastAPI deps (auth, RBAC)
│   ├── models/
│   │   └── core.py         # All SQLAlchemy ORM models
│   ├── schemas/
│   │   └── all.py          # All Pydantic v2 schemas
│   ├── routers/
│   │   ├── auth.py
│   │   ├── students.py
│   │   ├── attendance.py
│   │   ├── counseling.py
│   │   ├── safeguarding.py
│   │   ├── parents.py
│   │   ├── notifications.py
│   │   ├── dashboard.py
│   │   └── admin.py
│   ├── services/
│   │   ├── email.py        # SendGrid + Jinja2 templates
│   │   ├── notifications.py # Firebase FCM
│   │   └── audit.py        # Append-only audit log
│   └── templates/
│       └── email/          # HTML email templates
│
├── alembic/
│   └── env.py
│
├── tests/
│   └── test_platform.py    # Integration test suite
│
└── web/                    # Next.js 15 frontend
    ├── app/
    │   ├── layout.tsx
    │   ├── globals.css
    │   ├── auth/login/
    │   ├── dashboard/
    │   ├── students/
    │   ├── attendance/
    │   ├── counseling/
    │   ├── safeguarding/
    │   ├── parent-portal/
    │   ├── notifications/
    │   └── admin/
    ├── components/
    │   ├── ui/toaster.tsx
    │   └── providers/
    ├── lib/api.ts          # Axios client + all API helpers
    ├── tailwind.config.ts
    ├── next.config.js      # PWA config
    └── tsconfig.json
```

---

## Compliance

- **GDPR/PDPA**: Anonymise (not delete) PII; consent log; DSAR-ready endpoint pattern.
- **Audit log**: Append-only `audit_logs` table — no UPDATE/DELETE allowed.
- **Safeguarding SLA**: CRITICAL risk incidents trigger immediate background task (push + email) within 5 minutes.
- **Data residency**: Supabase project region should match school country requirements.

---

## API Documentation

Running locally: **http://localhost:8000/api/docs** (Swagger UI) or **/api/redoc** (ReDoc).

---

*Built with ❤️ — International Student Care OS v1.0.0*
