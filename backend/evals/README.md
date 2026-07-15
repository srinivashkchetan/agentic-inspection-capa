# Evaluation harness (PRD §7.3)

The eval suite gates production readiness on **correctness, not fluency**. It is
kept separate from unit tests because evals score model output against labeled
ground truth and are run as a gate, not on every commit.

Planned suites (map 1:1 to PRD §7.3):

| Suite | Measures | Status |
| --- | --- | --- |
| `ingestion/` | Field-level parse/OCR correctness; result-state & failure-type classification vs. labels | classification scaffolded (see `test_classification.py`) |
| `retrieval/` | recall@k / precision@k, groundedness vs. labeled SOPs/standards/prior CAPAs | TODO |
| `root_cause/` | Agreement of LLM root cause with QE-validated ground truth (8D), expert-scored | TODO |
| `faithfulness/` | Share of actions fully supported by cited context; unsupported/contradicted rate | TODO |
| `acceptance/` | QE accept-with-no/minor-edits rate (edit distance + HITL approval) | TODO |
| `redteam/` | Prompt injection, unsafe actions, spec tampering | TODO |

**Cadence.** Run retrieval + faithfulness continuously (they catch SOP drift);
treat root-cause and closed-loop effectiveness as the gates for phase promotion.

Run: `pytest evals/`
