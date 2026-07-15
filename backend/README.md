# CAPA Backend (FastAPI)

The source-of-truth JSON API for AI-assisted corrective action planning. The
Next.js console (`../frontend`) is a decoupled client — it talks only to this
API, never to the model, RDBMS, or vector store directly (PRD §5.2).

## Architecture (PRD §5)

```
ingest → classify → [trigger on FAIL/PENDING] → retrieve (RDBMS ‖ RAG)
       → assemble → generate (Claude) → guardrails → HITL #1 → HITL #2 → close
```

- **RDBMS (facts)** — `app/data/repository.py`. Verbatim, never generated.
- **RAG (grounding)** — `app/pipeline/retrieve.py`. Seed corpus + retriever seam (swap for Chroma).
- **GenAI (generation only)** — `app/llm/client.py`, Claude Opus 4.8. Proposes; never the record.
- **Orchestration & guardrails** — `app/pipeline/`. Facts and knowledge kept in distinct channels.

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,rag]"          # add ,postgres for the psycopg driver
cp .env.example .env                 # add ANTHROPIC_API_KEY for live generation
uvicorn app.main:app --reload        # http://localhost:8000  (docs at /docs)
```

On startup the app creates tables and seeds the reports from the dataset if the
DB is empty. **Offline mode:** with no `ANTHROPIC_API_KEY`, the generation stage
returns a deterministic, source-cited stub — the whole pipeline and UI run with
zero token spend. `GET /health` reports `generation_mode`.

## Relational store (Postgres)

Defaults to a local SQLite file (`CAPA_DATABASE_URL` empty). For Postgres:

```bash
docker compose up -d                 # Postgres + pgvector on :5432
# in .env:
#   CAPA_DATABASE_URL=postgresql+psycopg://capa:capa@localhost:5432/capa
python -m scripts.seed_db            # load the dataset into Postgres
```

The ORM (`app/db.py`) is dialect-agnostic — the same models run on SQLite and
Postgres. `app/data/repository.py` keeps its list/get/save interface, so routers
and the pipeline are unchanged.

## Vector DB (RAG)

`CAPA_RETRIEVER` selects the retriever: `auto` (Chroma if installed, else the
keyword seed retriever), `chroma`, or `seed`. The knowledge corpus lives in
`corpus/*.md` (SOPs, standards, prior 8D) — one source of truth for both
retrievers. Embeddings default to a dependency-free hashed embedding
(`app/pipeline/embeddings.py`); swap in a real semantic model without touching
the retriever interface.

```bash
python -m scripts.index_corpus       # (re)build the Chroma index from corpus/
```

## Test

```bash
pytest            # unit + contract tests
pytest evals/     # correctness evals (PRD §7.3)
```

## Key endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/reports` | List ingested FRI reports (with failure-type + draftable flag) |
| `GET` | `/reports/{id}` | Full report record |
| `POST` | `/reports/{id}/draft` | Run the pipeline → persist a CAPA draft (409 on PASS) |
| `GET` | `/capas` / `/capas/{id}` | List / fetch drafts |
| `PUT` | `/capas/{id}` | QE edits the draft (HITL #1) |
| `POST` | `/capas/{id}/approve` | HITL #1 approve → vendor implementing |
| `POST` | `/capas/{id}/submit-evidence` | Vendor submits effectiveness evidence |
| `POST` | `/capas/{id}/verify` | HITL #2 verify → close (pass) or rework (fail) |

## Swap seams (dev → production)

- **SQLite → Postgres**: set `CAPA_DATABASE_URL` (docker-compose provided). Done.
- **Seed retriever → Chroma**: `CAPA_RETRIEVER=chroma`. pgvector is an alternative
  behind the same `Retriever` interface (`app/pipeline/retrieve.py`).
- **Embeddings**: replace `HashingEmbeddingFunction` with a semantic model/provider.
- **OCR** (not yet wired): add a parser behind a field-level confidence gate before
  records enter the RDBMS (PRD §7.1).
