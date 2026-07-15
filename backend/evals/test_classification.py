"""Ingestion eval (PRD §7.3): result-state / failure-type classification accuracy.

Ground truth here is the dataset's own overall_result plus a small rule: an
F-series code with clean physical sections is a compliance failure. As labeled
8D/QE data arrives, replace these heuristic labels with curated ground truth.
"""

from __future__ import annotations

from app.data.repository import get_report_repository
from app.pipeline import classify


def test_result_state_matches_dataset() -> None:
    reports = get_report_repository().list()
    correct = sum(
        1
        for r in reports
        if classify.classify_result_state(r).value == r.overall_result.upper()
    )
    assert correct == len(reports)  # deterministic mapping must be exact


def test_failure_type_is_assigned_for_every_failure() -> None:
    reports = get_report_repository().list()
    for r in reports:
        ft = classify.classify_failure_type(r)
        if r.overall_result.upper() == "PASS":
            assert ft.value == "none"
        else:
            assert ft.value != "none"
