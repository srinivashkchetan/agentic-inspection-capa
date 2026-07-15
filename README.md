# Agentic Inspection — AI-Assisted Corrective Action Planning (CAPA)

An AI system that drafts corrective action plans (CAPAs) from third-party quality
inspection reports, then routes them through two human-in-the-loop approval gates.
It deliberately separates duties: **exact facts come from an RDBMS**, **grounding
knowledge comes from RAG**, and **only reasoning and synthesis come from the GenAI
model** — the model proposes, it never becomes the source of record.

See the PRD (`plan/CAPA_AI_PRD.md`) for architecture, the grounded input data
model (§5.1), the **tech stack (§5.2)**, guardrails/evals (§7), success metrics,
and the phased roadmap.

## Repository layout

| Path | What |
| --- | --- |
| `plan/CAPA_AI_PRD.md` | Product Requirements Document (v1.1) — includes the tech stack (§5.2) |
| `reports/inspection_reports_all.json` | 34 inspection-event records (9 real FRI reports + 25 synthetic) — seed/test data |
| `backend/` | **FastAPI** service — the pipeline and JSON API (source of truth) |
| `frontend/` | **Next.js + TypeScript** — decoupled HITL review console |
| `docs/` | Formatted PRD (Word) |

The two apps are independent toolchains and deploys. The frontend consumes only
the backend's JSON API — it never talks to the model, RDBMS, or vector store.

## Quick start

```bash
# 1. Backend (http://localhost:8000, docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,rag]"      # add ,postgres for the psycopg driver
cp .env.example .env             # optional: add ANTHROPIC_API_KEY for live generation
uvicorn app.main:app --reload    # creates + seeds the DB on startup

# 2. Frontend (http://localhost:3000), in a second terminal
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

**No API key?** The backend runs in offline mode and returns deterministic,
source-cited draft CAPAs — the whole pipeline and UI work end-to-end with zero
token spend. Add `ANTHROPIC_API_KEY` to switch to live Claude Opus 4.8 generation.

**Storage & RAG.** The relational store (facts + CAPAs) defaults to SQLite and
switches to **Postgres** by setting `CAPA_DATABASE_URL` (`backend/docker-compose.yml`
provides Postgres + pgvector). The RAG layer uses an embedded **Chroma** vector DB
by default (`CAPA_RETRIEVER=auto|chroma|seed`), indexed from `backend/corpus/*.md`
via `python -m scripts.index_corpus`.

## Pipeline (PRD §5)

```
ingest → classify → [trigger on FAIL/PENDING] → retrieve (RDBMS ‖ RAG)
       → assemble → generate (Claude) → guardrails → HITL #1 → HITL #2 → close
```

PASS reports are logged but do not draft a CAPA. Compliance-only failures (e.g.
fail code F8 — missing lab test report) are routed to a rules track and surfaced
for human referral rather than drafted by the model (PRD §9.1).

## Tests

```bash
cd backend && pytest          # unit + API contract tests
cd backend && pytest evals/   # correctness evals (PRD §7.3)
```

## Data note

The 9 real records were transcribed from image-based (scanned) inspection PDFs; a
few multi-value fields are captured representatively. Each record carries a
`source` field (`actual` or `synthetic`) and `source_file`.
