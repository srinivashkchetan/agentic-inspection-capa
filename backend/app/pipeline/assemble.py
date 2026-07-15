"""Context assembly: bounded window, facts and knowledge in distinct channels (PRD §5, §6.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.models import FailureType
from app.pipeline.retrieve import RetrievalResult

SYSTEM_PROMPT = (
    "You are a quality-engineering assistant that drafts corrective action plans "
    "(CAPAs) for defective products found during third-party Final Random Inspection.\n"
    "Rules you must follow:\n"
    "1. You PROPOSE a draft only. You are never the source of record.\n"
    "2. Use ONLY the STRUCTURED FACTS and RETRIEVED KNOWLEDGE provided. Do not invent "
    "part numbers, tolerances, defect codes, or measurements.\n"
    "3. EVERY corrective action must cite a source id from RETRIEVED KNOWLEDGE "
    "(e.g. SOP-COATING-01). Steps without a citation are not allowed.\n"
    "4. If the evidence is insufficient to ground a root cause, set confidence low "
    "and say so rather than fabricating a plan.\n"
    "5. Keep the plan ordered, specific, and verifiable."
)


@dataclass
class AssembledContext:
    system: str
    user: str
    citation_ids: list[str]


def _facts_block(facts: dict) -> str:
    return json.dumps(facts, indent=2, default=str)


def _knowledge_block(result: RetrievalResult) -> str:
    if not result.chunks:
        return "(no grounding documents cleared the retrieval threshold)"
    return "\n\n".join(
        f"[{c.id}] {c.title}\n{c.text}" for c in result.chunks
    )


def assemble(result: RetrievalResult, failure_type: FailureType) -> AssembledContext:
    user = (
        f"FAILURE TYPE (routing key): {failure_type.value}\n\n"
        "=== STRUCTURED FACTS (verbatim from system of record) ===\n"
        f"{_facts_block(result.facts)}\n\n"
        "=== RETRIEVED KNOWLEDGE (cite these ids) ===\n"
        f"{_knowledge_block(result)}\n\n"
        "Draft a CAPA with: root_cause, containment, ordered corrective_actions "
        "(each with a citation id from the retrieved knowledge), verification_method, "
        "and a confidence score in [0,1]."
    )
    return AssembledContext(
        system=SYSTEM_PROMPT,
        user=user,
        citation_ids=[c.id for c in result.chunks],
    )
