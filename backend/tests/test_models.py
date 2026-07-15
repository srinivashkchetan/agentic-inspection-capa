"""The seed dataset must load into typed models without loss (PRD §5.1)."""

from __future__ import annotations

from app.models import InspectionReport


def test_all_seed_records_parse(reports: list[InspectionReport]) -> None:
    assert len(reports) >= 30  # 9 actual + 25 synthetic per PRD
    assert all(r.report_id for r in reports)
    assert all(r.overall_result in {"PASS", "FAIL", "PENDING"} for r in reports)


def test_fail_report_has_defects_and_code(fail_report: InspectionReport) -> None:
    assert fail_report.fail_code
    assert fail_report.general is not None
    assert fail_report.visual_check is not None
