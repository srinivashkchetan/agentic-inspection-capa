# CAPA Frontend (Next.js)

The human-in-the-loop review console for quality engineers. A **decoupled**
client of the FastAPI backend — it consumes only the JSON API and never touches
the model, RDBMS, or vector store (PRD §5.2). This split means the same backend
serves this UI unchanged as it hardens toward production.

## Run

```bash
cd frontend
npm install
cp .env.local.example .env.local     # points at the backend (default :8000)
npm run dev                          # http://localhost:3000
```

The backend must be running (see `../backend/README.md`). With the backend in
offline mode you can click through the whole flow with no API key.

## What it does

- **`/`** — list of ingested FRI reports with result, fail code, and failure type.
- **`/reports/[id]`** — the review workspace:
  1. shows the report's key facts (verbatim from the system of record),
  2. **Generate draft CAPA** runs the backend pipeline and renders root cause,
     containment, ordered corrective actions (each with its citation),
     verification method, confidence, and any guardrail flags,
  3. **HITL #1** approve/reject → vendor implementation → evidence,
  4. **HITL #2** verify pass (close & write back) or fail (rework).

Compliance-only failures come back `escalated` (rules track), so HITL #1 approve
is disabled for them — matching the backend routing (PRD §9.1).

## Structure

- `src/lib/types.ts` — the API contract, mirroring the backend schemas.
- `src/lib/api.ts` — typed fetch client (`NEXT_PUBLIC_API_BASE_URL`).
- `src/app/` — App Router pages (list + review workspace).

## Migration note

Because everything goes through `src/lib/api.ts`, swapping styling, adding auth,
or moving to a different rendering strategy touches only this app — the backend
contract is fixed.
