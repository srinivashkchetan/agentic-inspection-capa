"""Generation stage: the model synthesizes; it never becomes the record (PRD §5).

Two paths:
  * online  -> call Claude via CapaLLM (requires ANTHROPIC_API_KEY).
  * offline -> deterministic, source-cited stub so the UI and tests run with no
               key and no token spend (Settings.offline).
"""

from __future__ import annotations

from app.config import get_settings
from app.models import CorrectiveAction, GeneratedCapa
from app.pipeline.assemble import AssembledContext
from app.pipeline.retrieve import RetrievalResult


def _offline_stub(context: AssembledContext, result: RetrievalResult) -> GeneratedCapa:
    """Deterministic draft grounded in whatever chunks were retrieved."""
    top = result.chunks[0] if result.chunks else None
    citation = top.id if top else "UNGROUNDED"
    defect_desc = ""
    defects = result.facts.get("visual_defects") or []
    for d in defects:
        if d.get("major") or d.get("minor"):
            defect_desc = d.get("defect_description") or ""
            break

    root = (
        f"[OFFLINE STUB] Likely process cause of '{defect_desc or result.facts.get('fail_reason')}' "
        f"based on {top.title if top else 'available grounding'}."
    )
    actions = [
        CorrectiveAction(
            step=1,
            description=(
                "Contain the affected lot and re-inspect against the approved sample."
            ),
            citation=citation,
        ),
        CorrectiveAction(
            step=2,
            description=(
                "Correct the responsible process parameter per the cited SOP and "
                "run a first-article check."
            ),
            citation=citation,
            owner="Vendor",
        ),
    ]
    return GeneratedCapa(
        root_cause=root,
        containment="Quarantine the presented lot pending QE review.",
        corrective_actions=actions,
        verification_method=(
            "Re-inspect a fresh sample under ANSI/ASQ Z1.4 at the same level; "
            "accept only within AQL."
        ),
        confidence=0.4,  # deliberately modest — stub is not a validated plan
    )


def generate(context: AssembledContext, result: RetrievalResult) -> GeneratedCapa:
    if get_settings().offline:
        return _offline_stub(context, result)
    # Local import keeps the SDK optional for offline/dev use.
    from app.llm.client import CapaLLM

    return CapaLLM().draft(context.system, context.user)
