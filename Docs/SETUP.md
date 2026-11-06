# Local Development Setup
## VeriBrand Trace
**Team:** Last of Us  
**Status:** Updated for Checkpoint 1 Foundation  

---

## 1. Prerequisites
- **Python 3.11** (`3.11.9` installed locally under `%LOCALAPPDATA%\Programs\Python\Python311`)
- **Node.js LTS** (`v22.21.0` or later) & **npm** (`11.12.1`)
- **Git** (`2.51.2` or later)
- **PostgreSQL / Supabase** (for Database Checkpoint 2 onwards)
- **Gemini API Key** (for Grounded AI Checkpoint 7 onwards)
- **Vector Store:** `pgvector` (via PostgreSQL)

---

## 2. Repository Layout
```text
VeriBrandTrace/
├── client/                     # Next.js 14 App Router, TypeScript, Tailwind, TipTap
│   ├── src/
│   │   ├── app/                # Pages and API routes (health, dashboard, etc.)
│   │   ├── components/         # Reusable UI components (Navbar, etc.)
│   │   └── types/              # TypeScript definitions
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── .env.local.example
├── server/                     # FastAPI + Python 3.11
│   ├── app/
│   │   ├── api/v1/             # API v1 routes (/health, etc.)
│   │   ├── core/               # App configuration (Pydantic Settings)
│   │   ├── models/             # SQLAlchemy ORM models (Checkpoint 2)
│   │   ├── schemas/            # Pydantic v2 schemas
│   │   ├── services/           # Deterministic, RAG, AI, and workflow services
│   │   └── main.py             # FastAPI entrypoint & CORS middleware
│   ├── tests/                  # Pytest test suite
│   ├── requirements.txt
│   ├── pytest.ini
│   └── .env.example
├── Docs/                       # 16 specification & architecture documents
├── completedWord.md            # Checkpoint work completion log
├── package.json                # Monorepo root scripts
├── .gitignore
└── README.md
```

---

## 3. Backend Setup

From the repository root:

```bash
cd server

# Using Python 3.11:
python -m pip install -r requirements.txt

# Run backend development server:
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run backend health tests:
```bash
python -m pytest tests -v
```

Interactive OpenAPI documentation is available at:
`http://127.0.0.1:8000/docs`

---

## 4. Frontend Setup

From the repository root:

```bash
cd client

# Install dependencies:
npm install

# Run frontend development server:
npm run dev
```

The web application will be accessible at:
`http://localhost:3000`

---

## 5. Root Monorepo Commands

Convenience scripts are provided in the root `package.json`:

```bash
# Start frontend:
npm run dev:client

# Build frontend:
npm run build:client

# Start backend:
npm run dev:server

# Run backend tests:
npm run test:server
```

---

## 6. Environment Variables

### Backend (`server/.env` based on `server/.env.example`):
```dotenv
APP_ENV=development
DEBUG=true
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/veribrand
JWT_SECRET=super-secret-development-key-change-in-production-min-32-chars
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
VECTOR_STORE_PROVIDER=pgvector
PRIVATE_STORAGE_PATH=./uploads
```

### Frontend (`client/.env.local` based on `client/.env.local.example`):
```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

---

## 7. Verification

Verify health endpoints:
- Frontend Health: `GET http://localhost:3000/api/health`
- Backend Root: `GET http://127.0.0.1:8000/`
- Backend Health: `GET http://127.0.0.1:8000/health`
- Backend API v1 Health: `GET http://127.0.0.1:8000/api/v1/health`
