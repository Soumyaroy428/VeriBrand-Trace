# VeriBrand Trace
### Explainable Pre-Publication Brand Governance & Human-in-the-Loop Diff Platform

**Team:** Last of Us  
**Round 1 team members:** Sayantan Dutta, Soumya Roy, Debarun Banerjee and Risijit Dhar.

## What it does
VeriBrand Trace checks content before publication using deterministic brand rules and citation-grounded AI. It gives creators traceable violation cards and intent-preserving suggestions, while keeping final approval with authorised human reviewers.

## Core workflow
1. Admin configures Brand Vault.
2. Creator uploads text, DOCX/PDF or PNG/JPG.
3. Privacy gate redacts configured sensitive information.
4. Deterministic engine and grounded RAG AI audit the content.
5. Creator reviews findings and diffs.
6. Reviewer handles exceptions and approves/rejects.
7. Admin reviews governance insights.

## Technology specified in the Round 1 plan
- Frontend: Next.js 14, TypeScript, Tailwind CSS, TipTap
- Backend: Python 3.11, FastAPI, Pydantic v2
- Deterministic checks: Regex, OpenCV, Pillow, EasyOCR, WCAG utilities
- AI: Gemini 2.5 Flash
- Retrieval: ChromaDB or pgvector (choose one)
- Database/RBAC: PostgreSQL (Supabase), SQLAlchemy, JWT Auth

## Documentation map
| File | Purpose |
|---|---|
| `PRD.md` | Product scope and requirements |
| `DESIGN.md` | UX, screens and design principles |
| `ARCHITECTURE.md` | Components and data flow |
| `DATABASE.md` | Tables and relationships |
| `API.md` | Proposed REST API |
| `AGENTS.md` | Agent/service responsibilities |
| `PLAN.md` | Phased execution plan |
| `SETUP.md` | Local development setup |
| `FEATURES.md` | Feature inventory and status |
| `AUTH.md` | Authentication and RBAC |
| `MCP.md` | Optional Model Context Protocol design |
| `INTEGRATIONS.md` | External services and boundaries |
| `TESTING.md` | QA strategy |
| `DEBUGGING.md` | Troubleshooting guide |

## Repository status
This folder contains planning documentation, not a completed application. API routes, schemas, deployment providers, secrets, limits and operational policies must be confirmed against the implementation.

## Core safety principle
**Suggest, never override.** AI findings are advisory. Human reviewers retain final publishing authority.
