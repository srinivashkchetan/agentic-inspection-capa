"""Wires the pipeline stages and manages the HITL workflow entry point (PRD §5)."""

from __future__ import annotations

import uuid

from app.models import CapaDraft, CapaStatus, InspectionReport
from app.pipeline import assemble, classify, generate, guardrails, retrieve


class NotTriggerableError(Exception):
    """Raised when a PASS report is submitted for drafting (no CAPA, PRD §5)."""


def draft_capa(report: InspectionReport, retriever: retrieve.Retriever | None = None) -> CapaDraft:
    """Run ingest→classify→retrieve→assemble→generate→guardrails for one report."""
    result_state = classify.classify_result_state(report)
    if not classify.should_draft(report):
        raise NotTriggerableError(
            f"Report {report.report_id} resolved to {result_state.value}; no CAPA drafted."
        )

    failure_type = classify.classify_failure_type(report)

    retrieval = retrieve.retrieve(report, failure_type, retriever=retriever)
    input_flags = guardrails.input_guardrails(retrieval)

    context = assemble.assemble(retrieval, failure_type)
    generated = generate.generate(context, retrieval)
    output_flags = guardrails.output_guardrails(generated, context.citation_ids)

    from app.config import get_settings

    flags = input_flags + output_flags
    # Compliance-only failures route to the rules track; anything flagged escalates.
    status = CapaStatus.DRAFT
    if classify.is_rules_track(report):
        flags.append("routing: compliance-only failure — rules track / human referral")
        status = CapaStatus.ESCALATED
    elif any(f.startswith(("abstention", "retrieval_quality")) for f in flags):
        status = CapaStatus.ESCALATED

    return CapaDraft(
        id=f"capa_{uuid.uuid4().hex[:12]}",
        report_id=report.report_id,
        result_state=result_state,
        failure_type=failure_type,
        root_cause=generated.root_cause,
        containment=generated.containment,
        corrective_actions=generated.corrective_actions,
        verification_method=generated.verification_method,
        status=status,
        generated_by="offline-stub" if get_settings().offline else get_settings().capa_model,
        citations=context.citation_ids,
        guardrail_flags=flags,
        confidence=generated.confidence,
        history=[{"event": "generated", "status": status.value}],
    )
