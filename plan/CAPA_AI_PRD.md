# Product Requirements Document

## AI-Assisted Corrective Action Planning (CAPA)

**Domain:** Quality Inspection · **Status:** Draft v1.1 · **Date:** July 14, 2026 · **Owner:** Srini (Product)

> **v1.1 revision.** Updated to reflect the primary input now confirmed from sample data: third-party **Final Random Inspection (FRI)** reports (Bureau Veritas, Walmart program) carrying defect codes, AQL sampling results, and PASS/FAIL/PENDING outcomes. Architecture, requirements, MVP scope, and risks were revised to match this real report structure. See §5.1 for the grounded input data model.

---

## 1. Summary

The CAPA system generates draft corrective action plans for defective products detected during inspection. The trigger is an inspection report that resolves to a **FAIL** or **PENDING (client decision)** result — in practice a third-party Final Random Inspection (FRI) report with coded defects (Critical / Major / Minor) sampled under ANSI/ASQ Z1.4. When such a result is found, the system produces a ranked, source-cited action plan for a quality engineer (QE) to review and approve. The architecture deliberately separates duties: **exact facts come from an RDBMS**, **grounding knowledge comes from RAG**, and **only reasoning and synthesis come from the GenAI model**. The model proposes; it never becomes the source of record. This keeps the context window lean, controls cost, and minimizes hallucination.

## 2. Problem & Opportunity

Quality engineers currently author CAPAs manually, cross-referencing part masters, measurement records, SOPs, standards, and prior root-cause reports. The work is slow, inconsistent across engineers, and gated by availability of experienced staff. Meanwhile the raw signal is already highly structured: each FRI report carries the product/PO/vendor/factory lineage, a 19-line result summary, and coded defects with severity — yet none of that is currently carried forward into a drafted corrective action. The sample set also shows the failure signal is heterogeneous: some FAILs are workmanship (e.g., coating peel-off, broken stitches, shift painting), while others are program/compliance gaps (e.g., a missing valid lab test report, fail code F8) — and these demand different corrective logic.

The opportunity is to compress the drafting step — root-cause inference, ordered corrective steps, and evidence-backed justification — while keeping humans as the authority on approval and effectiveness verification. The measure of success is not speed alone but **cost-per-validated-CAPA**: a cheap plan that QEs reject or that fails vendor verification is not actually cheap.

## 3. Goals & Non-Goals

**Goals**

- Reduce QE time-to-draft for common, high-volume defect categories.
- Improve consistency and traceability of CAPAs through mandatory citations.
- Preserve compliance and safety through human-in-the-loop (HITL) approval gates.
- Establish an evaluation harness that gates production readiness on correctness, not fluency.

**Non-Goals**

- The model does not auto-authorize any CAPA in the MVP. All plans are drafts.
- The system is not the system of record; the RDBMS remains authoritative for facts.
- No autonomous action to vendors without human sign-off.
- Not attempting broad coverage across all product lines and defect types at launch.

## 4. Users & Personas

- **Quality Engineer (primary):** Reviews, edits, and approves drafts (HITL #1); verifies vendor evidence and re-approves (HITL #2).
- **Quality Manager:** Oversees automation policy, guardrail strictness, and scope expansion decisions.
- **Vendor / Supplier:** Implements the approved CAPA and submits evidence of effectiveness.
- **Platform / ML Engineer:** Maintains retrieval, evals, guardrails, and data pipelines.

## 5. System Architecture

**Flow.** Inspection report ingested and parsed (third-party FRI report, typically a scanned PDF requiring OCR; and/or a vision-model + inspector event) → result-state and failure-type classification → **trigger on FAIL / PENDING** → orchestration & context-engineering layer → parallel retrieval from RDBMS and RAG → assembled context window → GenAI generation → draft CAPA → human approval (HITL #1) → vendor implementation → human verification and re-approval (HITL #2) → close and write back to the RDBMS. Reports that resolve to PASS are logged but do not draft a CAPA.

| Layer | Responsibility |
| --- | --- |
| **RDBMS** — deterministic facts | System of record, queried by exact key and injected verbatim, never generated: product/BOM & part master, **parsed FRI report records** (report ID, inspection date, service type, overall result and fail/pending code), **coded defects with Critical/Major/Minor counts, AQL thresholds and accept/reject outcomes**, quantities and cartons sampled, supplier/factory/PO/lot lineage, retail market and country of origin, and historical CAPAs with close-out status. |
| **RAG** — retrieved knowledge | Semantic retrieval over unstructured documents via vector DB + reranker: **inspection protocols referenced in the reports (e.g., WGS QA-IP-GR / IFI protocols)**, SOPs & work instructions, quality standards (ISO 9001 / IATF 16949), FMEA and prior 8D root-cause reports, approved-sample and lab-test-report references, and engineering specs/drawings. Grounds the model and supplies citations. |
| **GenAI** — generation only | The LLM stores no facts. Given the assembled context (facts + retrieved chunks + task template) it infers likely root cause, drafts ordered corrective steps, and ranks and justifies each option against cited evidence. Output is always a draft. |
| **Orchestration** — context engineering | Decides what to fetch per defect so prompts stay small (matching record + top-k relevant docs), routes by failure type (workmanship vs. functional vs. compliance), keeps structured facts and knowledge in distinct channels, applies guardrails, and manages the HITL workflow. |

**Closed loop.** After the QE approves the plan (HITL #1), the vendor implements the CAPA and submits evidence. Quality personnel verify effectiveness and re-approve (HITL #2). On pass, the CAPA is closed and written back to the RDBMS — enriching both historical-CAPA facts and the RAG corpus for future defects. On fail, it loops back to the vendor for rework. Anything safety-, compliance-, or spec-critical is enforced from RDBMS/RAG sources and routed for mandatory human sign-off. Note the FRI process already contains a native human-decision state — **PENDING for client decision** — which the system surfaces rather than resolves.

### 5.1 Input Data Model (grounded in sample reports)

The 9 sample FRI reports (Bureau Veritas, Walmart program; departments include Food, Hard Home, Stationery, Sporting Goods, Automotive, Lawn & Garden, Seasonal, Soft Home, Toys) share a consistent structure the system ingests:

- **Header / identifiers:** third-party name, third-party inspection #, report ID, report date, overall result.
- **Section A — General:** vendor/supplier name & ID, factory name & ID, credit office code, retail market (e.g., WMUS, WMCA, Sam's China), department (category) #, product category (e.g., HARDLINE - NON E & E, HARDLINE - E & E, SOFT HOME, FOOD), country of origin, IFI version, service performed (Final Random Inspection), approved/reference sample flags, protocol number.
- **Section B — Result summary:** 19 line items (Shipping Marks, Style, Material, Color, packing checks, Product Conformity, Assortment, Carton Drop Test, Labeling / Printed Materials / Markings, Visual Check, Barcode Verification, Function / Measurement, Weight, Program Specific Requirements, Inspection Conditions), each PASS / FAIL / PENDING / N/A.
- **Sections E–H — Checks:** Visual/workmanship (E), packing (F), functional/measurement (G), and on-site tests (H) — each with the sampling standard (ANSI/ASQ Z1.4), inspection level, sample size, AQL (Critical = Not Allowed, Major typically 1.5–2.5, Minor 4.0), and a defect table of **defect code + description + Critical/Major/Minor counts** with an accept/reject result.
- **Result states & codes:** `PASS`, `FAIL` (with an F-series code, e.g., **F8 = no valid lab test report**), and `PENDING for client decision` (P-series code, e.g., **P2**). The failure taxonomy — **workmanship**, **packing**, **functional/measurement**, and **program/compliance** — is the primary routing key for corrective logic and defect-class scoping.
- **Section I — Attachments & sign-off:** inspector name, reviewer name, inspection date, in/out times, digital images, and test-report attachment flag.

A structured, machine-readable version of these records (9 transcribed real reports + 25 synthetic) is maintained as `inspection_reports_all.json` and serves as seed/test data for retrieval and evals.

### 5.2 Tech Stack

The stack is chosen to honor the architecture's separation of duties (§5) and the "launch narrow, prove correctness" MVP principle (§9.1): embedded, zero-infra defaults for development, with clean seams so each component can be swapped for a managed/production service without touching the pipeline. The pipeline lives entirely behind a JSON API, so the frontend is a decoupled client and never talks to the model, RDBMS, or vector store directly.

| Layer | Choice (MVP / dev) | Production swap | Rationale |
| --- | --- | --- | --- |
| **GenAI model** | Anthropic **Claude Opus 4.8** (`claude-opus-4-8`) via the official `anthropic` Python SDK, adaptive thinking | Model tiering (Phase 1): cheaper tier for routine defects, premium for severe/novel | Single capable tier for the MVP per §9.1; the SDK is the only sanctioned way to call Claude. Draft generation only — never the source of record. |
| **Backend / API** | **Python 3.11+** + **FastAPI** (ASGI, `uvicorn`), **Pydantic v2** models | Same | Best ecosystem for RAG/OCR/embeddings/evals; typed request/response contracts; async I/O for parallel RDBMS + RAG retrieval. |
| **Frontend** | **Next.js (App Router) + React + TypeScript**, decoupled SPA consuming the FastAPI JSON API | Same, hardened (auth, RBAC, polish) | HITL review console for quality engineers (gate #1 draft review/edit/approve, gate #2 evidence verification). Split now to avoid a later migration; frontend is API-only, so the backend is unchanged as the UI matures. |
| **RDBMS (facts)** | **SQLite** via **SQLAlchemy** | **PostgreSQL** (managed) | System of record for exact facts (part/BOM, parsed FRI records, coded defects, AQL thresholds, lineage, historical CAPAs). SQLAlchemy keeps the swap to Postgres a config change. |
| **RAG (knowledge)** | **Chroma** (embedded) + reranker seam | **pgvector** or managed (Pinecone/Weaviate) | Semantic retrieval over SOPs, standards, prior 8D/FMEA. Embedded for zero-infra dev; abstracted behind a retriever interface. |
| **Embeddings** | Pluggable embedding-function interface (local default; provider optional) | Managed embedding endpoint | Kept behind an interface so the retrieval layer is provider-agnostic. |
| **Ingestion / OCR** | Structured JSON seed loader; OCR adapter seam (e.g. a cloud Document AI or local OCR) behind a field-level confidence gate | Production OCR service | Real FRI reports are scanned PDFs; the parser is isolated behind a confidence gate so no low-confidence extraction reaches the RDBMS (§7.1). |
| **Orchestration / guardrails** | In-process pipeline stages (ingest → classify → retrieve → assemble → generate → guardrails) with input/output guardrail hooks | Same, plus policy control surface (Phase 2) | Mirrors §5's context-engineering layer; keeps structured facts and retrieved knowledge in distinct channels. |
| **Evaluation harness** | **pytest** for unit/contract tests; a dedicated `evals/` suite (ingestion, retrieval, faithfulness, acceptance) | CI-gated eval runs with drift alerting (Phase 1+) | §7.3 gates production readiness on correctness, not fluency. |
| **Tooling** | `uv`/`pip` + `pyproject.toml` (backend), `npm` (frontend), `.env` for secrets, Docker-compose seam for local infra | CI/CD, container images | Reproducible dev setup; secrets never hardcoded (`ANTHROPIC_API_KEY` via env). |

**Repository shape.** A two-app monorepo: `backend/` (FastAPI service — the source of truth) and `frontend/` (Next.js review console). The frontend consumes only the documented JSON API (`/reports`, `/capas`), so the two toolchains and deploys stay independent.

## 6. Requirements

### 6.1 Functional

- Ingest and parse a third-party FRI report (OCR for scanned PDFs) into the structured record in §5.1; resolve it to a valid part/BOM/defect-code before any generation.
- Classify each report's result state (PASS / FAIL / PENDING) and failure type (workmanship / packing / functional / compliance); trigger CAPA drafting only on FAIL or PENDING.
- Retrieve exact facts from the RDBMS by key and relevant documents from RAG in parallel.
- Assemble a bounded context window keeping structured facts and retrieved knowledge in distinct channels.
- Generate a CAPA draft conforming to the template: root cause, containment, corrective action, verification method, owner, due date.
- Attach a citation to every corrective action.
- Present the draft to a QE for edit and approval (HITL #1).
- Capture vendor evidence and support QE effectiveness verification and re-approval (HITL #2).
- On pass, close the CAPA and write back to the RDBMS and RAG corpus.

### 6.2 Non-Functional

- **Grounding:** No un-cited corrective steps reach an approved plan.
- **Latency:** Draft generation within an interactive target (e.g., under ~30s for routine defects); tune per model tier.
- **Cost:** Track fully-loaded cost per CAPA; keep routine defects on a cheaper model tier.
- **Auditability:** Every draft, edit, and approval is logged with source references.
- **Access control:** Retrieval and queries scoped to the authorized vendor/plant/product.

## 7. Guardrails & Evaluation

### 7.1 Input Guardrails

| Guardrail | Purpose |
| --- | --- |
| Parse / OCR confidence gate | Halt if the FRI report parse falls below a field-level confidence threshold on key fields (report ID, defect codes, result, part/PO) — no downstream use of low-confidence extractions. |
| Schema & grounding validation | Halt if the defect can't be resolved to a valid part/BOM/defect-code — no generation on malformed or unmatched data. |
| Retrieval quality gate | Enforce a minimum similarity/rerank score and require ≥1 relevant document; if nothing clears threshold, escalate to a human. |
| Prompt-injection sanitization | Strip or neutralize instructions embedded in retrieved docs, PDFs, or inspector notes. |
| Access & data-scope control | Filter retrieval and queries to the authorized vendor/plant/product; block cross-tenant or restricted-spec leakage. |
| PII & sensitive-field masking | Redact supplier commercial terms, personal names, and confidential specs unless required and permitted. |

### 7.2 Output Guardrails

| Guardrail | Purpose |
| --- | --- |
| Citation enforcement | Every corrective action must cite a source; un-grounded steps are flagged or stripped. |
| Fact-consistency check | Verify tolerances, part numbers, and measurements match RDBMS values verbatim. |
| Safety / compliance gate | Block or route for mandatory review any regulated, safety-critical, or containment action. |
| Schema & completeness validation | Output must conform to the CAPA template; reject partial responses. |
| Hallucination / abstention control | Confidence and self-consistency thresholds trigger "insufficient evidence — escalate" rather than a fabricated plan. |

### 7.3 Evaluations

| Eval | What it measures |
| --- | --- |
| Ingestion accuracy | Field-level OCR/parse correctness on FRI reports and accuracy of result-state / failure-type classification vs. labeled ground truth. |
| Retrieval accuracy | recall@k / precision@k and groundedness against labeled SOPs, standards, and prior CAPAs. |
| Root-cause correctness | Agreement between LLM-inferred root cause and QE-validated ground truth (e.g., 8D reports), expert-scored. |
| Faithfulness / hallucination rate | Share of actions fully supported by cited context; rate of unsupported or contradicted claims. |
| Usefulness / acceptance rate | How often the QE accepts the draft with no or minor edits (edit-distance + HITL approval). |
| Closed-loop effectiveness & safety | Downstream re-approval pass rate and rework rate vs. baseline, plus a red-team suite for injection, unsafe actions, and spec tampering. |

**Cadence.** Run retrieval and faithfulness evals continuously — they catch drift as SOPs change. Treat root-cause and effectiveness metrics as the gates that decide production readiness.

## 8. Success Metrics

**North-star: Cost-per-validated-CAPA** = fully-loaded (AI + human) cost ÷ CAPAs that pass second-stage QE approval.

Track against three anchors:

- **Baseline manual cost** — the pre-system cost per CAPA.
- **QE acceptance rate** — share of drafts accepted with no/minor edits (HITL #1).
- **Re-approval pass rate** — share passing vendor-evidence verification (HITL #2).

Supporting metrics: time-to-draft, rework rate, hallucination rate, retrieval recall@k, automation coverage (share of eligible defects the system drafts vs. falls back to manual), and **OCR/parse accuracy** on ingested FRI reports (field-level extraction correctness), since every downstream fact depends on it.

## 9. Phased Roadmap

The guiding principle: **launch narrow with both HITL gates on and strict guardrails; prove correctness before relaxing anything.** Each phase gates on the metrics above, not calendar time.

### 9.1 MVP — Prove Correctness on a Narrow Slice

**Objective:** Demonstrate that the system drafts correct, well-grounded CAPAs a QE will accept, on a single narrow, high-volume defect category.

**Data-informed slice recommendation.** The sample data points to **workmanship (Section E / Visual Check) defects** as the best MVP anchor: they are the most frequent defect type across departments, share a homogeneous structure (defect code + Critical/Major/Minor + short description), and map cleanly to SOP/approved-sample grounding. Recurring, well-defined defects such as *coating peel-off* (Lawn & Garden), *broken stitches / untrimmed thread* (Stationery, Soft Home), and *shift painting on surface* (Toys) are strong first candidates. By contrast, **program/compliance failures (e.g., F8 — missing lab test report) are largely deterministic and rule-based** and should be handled by a lightweight rules track (or human referral), not GenAI, in the MVP.

**Scope**

- One department / product line and one high-volume workmanship defect category.
- Full pipeline: FRI report ingest & parse (OCR) → result/failure-type classification → RDBMS + RAG retrieval → context assembly → draft generation → HITL #1 → vendor implementation → HITL #2 → close & write-back.
- Both HITL gates always on; no auto-approval.
- Strict guardrail thresholds (favor manual fallback over risky output).
- Single model tier (choose one capable model; defer tiering).
- PENDING (client-decision) reports surfaced to the QE; compliance-only failures routed to the rules track.

**In scope**

- Schema/grounding validation, retrieval quality gate, prompt-injection sanitization, access scoping, PII masking.
- Citation enforcement, fact-consistency check, safety gate, schema/completeness validation, abstention control.
- FRI report parser/OCR with a field-level accuracy gate before any record enters the RDBMS.
- Eval harness for retrieval accuracy, root-cause correctness, faithfulness, acceptance rate.

**Out of scope**

- Multiple product lines/defect types, model tiering, any automation beyond drafting, freshness/re-embedding automation, GenAI handling of compliance-only failures.

**Exit criteria (gates to Phase 1)**

- Root-cause correctness meets an expert-agreed threshold.
- HITL #1 acceptance rate and HITL #2 re-approval pass rate beat the manual baseline.
- Hallucination rate below target; red-team suite passes.
- Cost-per-validated-CAPA at or trending below baseline manual cost.

### 9.2 Phase 1 — Efficiency & Selective Automation

**Objective:** Lower cost-per-validated-CAPA and expand coverage without loosening safety, using evidence from the MVP.

**Scope additions**

- **Model tiering:** route routine defects to a cheaper model, severe/novel defects to a premium model.
- **Retrieval tuning:** tune top-k and reranking per defect class to balance grounding vs. token cost.
- **Selective guardrail relaxation:** where MVP data shows the model is trustworthy for a defect class, raise the automation rate (e.g., lighter-touch HITL #1 for low-severity, high-confidence drafts) — safety/compliance-critical defects stay on mandatory sign-off.
- **Scope expansion:** add adjacent high-volume defect categories within the same product line.
- **Knowledge freshness:** introduce a re-embedding cadence so advice tracks current SOPs.
- **Continuous evals in production** with drift alerting.

**Exit criteria (gates to Phase 2)**

- Measurable drop in cost-per-validated-CAPA with acceptance and re-approval rates held or improved.
- Stable performance across the added defect categories.
- Freshness pipeline demonstrably keeps retrieval groundedness from degrading as SOPs change.

### 9.3 Phase 2 — Scale & Breadth (if needed)

**Objective:** Extend the proven system to more product lines and defect types, and industrialize operations. Pursue only where Phase 1 data justifies the added curation and eval burden.

**Scope additions**

- **Multi-line / multi-plant expansion** with per-tenant data scoping.
- **Broader defect taxonomy**, added incrementally with per-class evals and curation.
- **Policy-driven automation tuning:** quality managers set automation level and guardrail strictness per defect class from a control surface, rather than globally.
- **Operational maturity:** dashboards for the north-star and supporting metrics, SLA monitoring, cost attribution per line/tenant.
- **Feedback compounding:** closed CAPAs continuously enrich RDBMS history and RAG corpus, improving future drafts.

**Exit criteria (steady state)**

- North-star metric sustained below baseline across all live lines.
- Coverage (automation rate) and precision balanced to agreed targets per defect class.
- Eval and freshness pipelines operating without manual intervention.

## 10. Product Trade-offs

Each lever buys more benefit at the cost of money, latency, or risk. The PM job is to tune them per defect class, not globally.

| Lever | More benefit | Cost / risk |
| --- | --- | --- |
| Automation level | Auto-approval saves labor and cuts cycle time. | Higher chance a wrong or non-compliant CAPA reaches a vendor; both HITL gates cap that risk. |
| Model capability | Stronger reasoning lifts root-cause quality and acceptance. | Higher cost-per-CAPA and latency; tier cheap for routine, premium for severe/novel. |
| Retrieval depth | More chunks + reranking improve grounding, less hallucination. | Token cost and latency rise with top-k and context size. |
| Guardrail strictness | Tight thresholds cut bad outputs and protect compliance. | More cases fall to manual fallback, lowering automation rate (precision vs. coverage). |
| Scope breadth | More product lines/defect types widen the value pool. | Each addition adds curation, edge cases, and eval burden; start narrow and high-volume. |
| Knowledge freshness | Frequent re-embedding keeps advice aligned to current SOPs. | Adds engineering and infra overhead; tune the sync cadence. |

## 11. Risks & Mitigations

- **OCR / parse errors on scanned FRI reports** → field-level extraction accuracy gate before RDBMS entry; halt and escalate on low-confidence parses (garbage-in-garbage-out is the top new risk).
- **Failure-type misclassification** (e.g., a compliance F-code drafted as a workmanship CAPA) → deterministic result-state/failure-type classifier with human confirmation on ambiguous cases; route compliance-only failures to the rules track.
- **Hallucinated or spec-altered plans** → citation enforcement, fact-consistency checks, abstention control; both HITL gates.
- **Prompt injection via documents/notes** → input sanitization; red-team suite in evals.
- **Cross-tenant / restricted-spec leakage** → access & data-scope control at retrieval time (real reports span WMUS / WMCA / Sam's China and multiple factories, so scoping is exercised from day one).
- **Automation outrunning trust** → gate every relaxation on measured correctness and re-approval rates.
- **SOP / protocol drift** → continuous retrieval/faithfulness evals with drift alerting; re-embedding cadence (Phase 1+); watch IFI/protocol version changes referenced in reports.
- **Coverage vs. precision tension** → track automation rate alongside the north-star; tune strictness per defect class.

## 12. Open Questions

- Which department and workmanship defect category anchors the MVP (data suggests a high-volume Section-E defect class, e.g., coating peel-off or stitching defects)?
- Are FRI reports available in a structured/API feed from the inspection provider, or must every report be OCR'd from scanned PDF? (This materially changes ingestion cost and risk.)
- What are the numeric thresholds for root-cause correctness and acceptance that gate each phase?
- What is the measured baseline manual cost per CAPA (and the current volume of FAIL/PENDING reports per period)?
- Which model(s) are approved for the routine vs. premium tiers?
- What re-embedding cadence balances freshness against infra cost, and how are IFI/protocol version changes tracked?
- Should PENDING (client-decision) reports draft a provisional CAPA, or only surface for QE decision?
