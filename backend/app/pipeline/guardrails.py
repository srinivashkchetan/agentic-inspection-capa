"""Input & output guardrails (PRD §7.1, §7.2).

MVP implements the checks that need no external service: retrieval-quality gate,
citation enforcement, schema/completeness validation, and abstention control.
Each returns flags rather than raising, so the orchestrator can escalate.
"""

from __future__ import annotations

from app.models import GeneratedCapa
from app.pipeline.retrieve import RetrievalResult

# Thresholds (strict for the MVP: favor manual fallback over risky output, §9.1).
MIN_RETRIEVAL_CHUNKS = 1
MIN_CONFIDENCE = 0.3


def input_guardrails(result: RetrievalResult) -> list[str]:
    """Retrieval-quality gate: require >=1 relevant doc, else escalate (PRD §7.1)."""
    flags: list[str] = []
    if len(result.chunks) < MIN_RETRIEVAL_CHUNKS:
        flags.append("retrieval_quality: no grounding document cleared the threshold")
    if not result.facts.get("report_id"):
        flags.append("schema_grounding: report could not be resolved to a record")
    return flags


def output_guardrails(draft: GeneratedCapa, allowed_citations: list[str]) -> list[str]:
    """Citation enforcement, completeness, and abstention control (PRD §7.2)."""
    flags: list[str] = []

    if not draft.corrective_actions:
        flags.append("completeness: draft has no corrective actions")

    allowed = set(allowed_citations)
    for action in draft.corrective_actions:
        if not action.citation:
            flags.append(f"citation: step {action.step} is missing a citation")
        elif allowed and action.citation not in allowed:
            flags.append(
                f"citation: step {action.step} cites unknown source '{action.citation}'"
            )

    for field in ("root_cause", "containment", "verification_method"):
        if not str(getattr(draft, field, "")).strip():
            flags.append(f"completeness: '{field}' is empty")

    if draft.confidence < MIN_CONFIDENCE:
        flags.append("abstention: confidence below threshold — recommend escalate")

    return flags
