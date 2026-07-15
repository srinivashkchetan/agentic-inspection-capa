"""CAPA draft model + workflow enums (PRD §5 closed loop, §6.1 template)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ResultState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


class FailureType(str, Enum):
    """Primary routing key for corrective logic (PRD §5.1)."""

    WORKMANSHIP = "workmanship"
    PACKING = "packing"
    FUNCTIONAL = "functional"
    COMPLIANCE = "compliance"  # program/compliance (e.g. F8 missing lab report)
    NONE = "none"


class CapaStatus(str, Enum):
    """Closed-loop lifecycle with two human gates (PRD §5)."""

    DRAFT = "draft"  # generated, awaiting HITL #1
    APPROVED_HITL1 = "approved_hitl1"  # QE approved draft
    VENDOR_IMPLEMENTING = "vendor_implementing"
    VERIFYING = "verifying"  # evidence submitted, awaiting HITL #2
    APPROVED_HITL2 = "approved_hitl2"
    CLOSED = "closed"
    REJECTED = "rejected"
    ESCALATED = "escalated"  # guardrail abstention / rules-track referral


class CorrectiveAction(BaseModel):
    """One ordered corrective step. Every step MUST carry a citation (PRD §7.2)."""

    step: int = Field(..., description="1-based ordering of the corrective step.")
    description: str = Field(..., description="What to do to correct the root cause.")
    citation: str = Field(
        ...,
        description="Source reference grounding this step (SOP/standard/prior CAPA/record id).",
    )
    owner: str | None = Field(None, description="Responsible party (vendor/QE).")
    due_date: date | None = None


class GeneratedCapa(BaseModel):
    """The fields the LLM is allowed to synthesize (proposes, never source of record)."""

    root_cause: str = Field(..., description="Inferred likely root cause of the defect.")
    containment: str = Field(..., description="Immediate containment action.")
    corrective_actions: list[CorrectiveAction] = Field(default_factory=list)
    verification_method: str = Field(..., description="How effectiveness will be verified.")
    confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Self-reported confidence; low -> abstain/escalate."
    )


class CapaDraft(BaseModel):
    """A full CAPA draft: generated content + provenance + workflow state."""

    id: str
    report_id: str
    result_state: ResultState
    failure_type: FailureType

    root_cause: str
    containment: str
    corrective_actions: list[CorrectiveAction] = Field(default_factory=list)
    verification_method: str
    owner: str | None = None
    due_date: date | None = None

    status: CapaStatus = CapaStatus.DRAFT
    generated_by: str = Field(..., description="Model id or 'offline-stub'.")
    citations: list[str] = Field(default_factory=list)
    guardrail_flags: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Lightweight audit trail (PRD §6.2 auditability).
    history: list[dict] = Field(default_factory=list)
