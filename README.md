# VeriBrand Trace
### Explainable Pre-Publication Brand Governance & Human-in-the-Loop Diff Platform

[![Next.js](https://img.shields.io/badge/Next.js-14.2-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#)

> **Core Safety Principle:** *Suggest, Never Override.* AI findings and suggestions are advisory. Human reviewers retain final publishing authority.

---

## 1. Project Overview

**Team:** Last of Us  
**Round 1 Team Members:** Sayantan Dutta, Soumya Roy, Debarun Banerjee, Risijit Dhar.

VeriBrand Trace solves the critical challenge of pre-publication brand drift, unverified superlatives, inconsistent terminology, and visual non-compliance. It provides:

- **Deterministic Compliance:** High-speed, zero-hallucination regex terminology scanning, Delta-E CIEDE2000 color validation, and WCAG 2.1 AA accessibility contrast verification.
- **Grounded AI Claim Verification:** Gemini 2.5 Flash with `pgvector` retrieval grounded strictly in the workspace's Brand Vault guidelines and approved facts.
- **Explainable Violation Cards:** Findings paired with exact source clauses, confidence levels, and measured evidence.
- **Interactive Diff Workspace:** Side-by-side editing in TipTap allowing creators to review, accept suggestions non-destructively, edit manually, or request justified exceptions.
- **Human-in-the-Loop Review Queue:** Authorised Reviewers inspect diffs, evaluate exceptions, and sign tamper-evident compliance certificates.

---

## 2. Monorepo Structure

```text
VeriBrandTrace/
├── client/                     # Next.js 14 App Router, TypeScript, Tailwind CSS, TipTap
│   ├── src/
│   │   ├── app/                # App pages (overview, audits, brand-vault, review-queue)
│   │   ├── components/         # Accessible UI components (Navbar, DiffEditor, ViolationCard)
│   │   └── types/              # Shared TypeScript definitions
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── .env.local.example
├── server/                     # Python 3.11 FastAPI Backend
│   ├── app/
│   │   ├── api/v1/             # REST endpoints (/health, auth, vault, audits, reviews)
│   │   ├── core/               # App configuration (Pydantic Settings), security
│   │   ├── models/             # SQLAlchemy ORM models (18 relational entities)
│   │   ├── schemas/            # Pydantic v2 validation models
│   │   ├── services/           # Deterministic, RAG, AI, and workflow services
│   │   └── main.py             # FastAPI entrypoint & CORS middleware
│   ├── tests/                  # Automated pytest test suites
│   ├── requirements.txt
│   ├── pytest.ini
│   └── .env.example
├── Docs/                       # 16 Architecture & Specification Documents
├── completedWord.md            # Checkpoint Progress Log
├── package.json                # Monorepo root scripts
└── .gitignore                  # Security & artifact exclusions
```

---

## 3. Quickstart & Local Development

### Prerequisites
- Node.js `v22.21.0` or later
- Python `3.11.9` or later
- PostgreSQL with `pgvector`

### Backend Setup
```bash
cd server
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
- API Health Check: `http://127.0.0.1:8000/api/v1/health`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

Run tests:
```bash
python -m pytest tests -v
```

### Frontend Setup
```bash
cd client
npm install
npm run dev
```
- Web Client: `http://localhost:3000`
- Frontend Health: `http://localhost:3000/api/health`

---

## 4. Documentation Map

The single source of truth resides in `Docs/`:
- `PRD.md` — Product scope, 14 Functional Requirements, and acceptance criteria.
- `DESIGN.md` — UI/UX specification, color palette, and accessibility design laws.
- `ARCHITECTURE.md` — System architecture, trust boundaries, and processing sequences.
- `DATABASE.md` — Relational entities, pgvector schema, and audit hash-chaining.
- `API.md` — REST API endpoint schemas and status codes.
- `AGENTS.md` — Pipeline service boundaries (Intake, Privacy, Rules, RAG, AI, Normalizer).
- `PLAN.md` — Phased development roadmap.
- `SETUP.md` — Local environment setup and verified commands.
- `FEATURES.md` — Feature catalog and tracking matrix.
- `AUTH.md` — RBAC rules (`CREATOR`, `REVIEWER`, `GOVERNANCE_ADMIN`), token security.
- `MCP.md` — Optional Model Context Protocol extension specifications.
- `INTEGRATIONS.md` — External services, Gemini API boundaries, and privacy gates.
- `TESTING.md` — Quality assurance strategy, deterministic and AI test fixtures.
- `DEBUGGING.md` — Troubleshooting and incident response runbook.

