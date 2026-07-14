# Agentic Inspection — AI-Assisted Corrective Action Planning (CAPA)

Product requirements and seed data for an AI system that drafts corrective action plans (CAPAs) from third-party quality inspection reports.

## Contents

| File | Description |
| --- | --- |
| `CAPA_AI_PRD.md` | Product Requirements Document (Markdown), v1.1. |
| `CAPA_AI_PRD.docx` | Same PRD, formatted Word version. |
| `inspection_reports_all.json` | 34 inspection-event records (9 transcribed from real Bureau Veritas / Walmart Final Random Inspection reports + 25 synthetic), used as seed/test data for retrieval and evals. |

## Overview

The CAPA system generates draft corrective action plans for defective products detected during inspection. It deliberately separates duties: exact facts come from an RDBMS, grounding knowledge comes from RAG, and only reasoning and synthesis come from the GenAI model. Every plan is a draft reviewed by a quality engineer (HITL #1) and re-approved after vendor remediation (HITL #2).

The PRD covers system architecture, the grounded input data model (§5.1), guardrails and evaluations, success metrics, a phased roadmap (MVP → Phase 1 → Phase 2), product trade-offs, and risks.

## Data note

The 9 real records were transcribed from image-based (scanned) inspection PDFs; a few multi-value fields are captured representatively. Each record carries a `source` field (`actual` or `synthetic`) and `source_file`.
