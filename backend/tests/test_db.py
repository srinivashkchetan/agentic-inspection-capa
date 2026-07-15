"""The relational store persists facts and CAPA workflow state (PRD §5.2)."""

from __future__ import annotations

from app.data.repository import get_capa_store, get_report_repository
from app.models import CapaDraft, CapaStatus, FailureType, ResultState


def test_reports_seeded_and_queryable() -> None:
    repo = get_report_repository()
    reports = repo.list()
    assert len(reports) >= 30
    one = reports[0]
    assert repo.get(one.report_id).report_id == one.report_id


def test_capa_roundtrip_and_status_update() -> None:
    store = get_capa_store()
    draft = CapaDraft(
        id="capa_test_1",
        report_id="R-TEST",
        result_state=ResultState.FAIL,
        failure_type=FailureType.WORKMANSHIP,
        root_cause="rc",
        containment="c",
        verification_method="v",
        generated_by="offline-stub",
    )
    store.save(draft)
    assert store.get("capa_test_1").status is CapaStatus.DRAFT

    draft.status = CapaStatus.CLOSED
    store.save(draft)  # merge/upsert persists the new status
    assert store.get("capa_test_1").status is CapaStatus.CLOSED
