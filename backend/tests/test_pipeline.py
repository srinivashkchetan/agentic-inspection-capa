"""Pipeline behavior in offline mode: triggering, grounding, and citation rules."""

from __future__ import annotations

import pytest

from app.models import CapaStatus, InspectionReport, ResultState
from app.pipeline import classify
from app.pipeline.orchestrator import NotTriggerableError, draft_capa


def test_pass_report_does_not_draft(pass_report: InspectionReport) -> None:
    assert not classify.should_draft(pass_report)
    with pytest.raises(NotTriggerableError):
        draft_capa(pass_report)


def test_fail_report_drafts_capa(fail_report: InspectionReport) -> None:
    capa = draft_capa(fail_report)
    assert capa.report_id == fail_report.report_id
    assert capa.result_state is ResultState.FAIL
    assert capa.generated_by == "offline-stub"


def test_every_corrective_action_is_cited(fail_report: InspectionReport) -> None:
    """Grounding non-functional: no un-cited corrective step (PRD §7.2)."""
    capa = draft_capa(fail_report)
    for action in capa.corrective_actions:
        assert action.citation, f"step {action.step} missing citation"


def test_compliance_only_failure_routes_to_rules_track(
    reports: list[InspectionReport],
) -> None:
    """F-code with clean workmanship -> escalate, not a GenAI CAPA (PRD §9.1)."""
    f8 = next(
        (r for r in reports if (r.fail_code or "").upper() == "F8"),
        None,
    )
    if f8 is None:
        pytest.skip("no F8 record in dataset")
    capa = draft_capa(f8)
    assert capa.status is CapaStatus.ESCALATED
    assert any("rules track" in f for f in capa.guardrail_flags)
