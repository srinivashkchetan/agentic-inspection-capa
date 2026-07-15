"""Result-state and failure-type classification (PRD §6.1, §5.1).

Deterministic and rule-based on purpose: misclassifying a compliance F-code as a
workmanship CAPA is a named risk (PRD §11), so this stage does not use the LLM.
"""

from __future__ import annotations

from app.models import FailureType, InspectionReport, ResultState

# Section -> failure type, using result_summary line items (PRD §5.1 Section B).
_SUMMARY_TO_TYPE: dict[str, FailureType] = {
    "Visual Check": FailureType.WORKMANSHIP,
    "Export Carton Packing": FailureType.PACKING,
    "Inner Carton Packing": FailureType.PACKING,
    "Product Packaging": FailureType.PACKING,
    "Carton Drop Test": FailureType.PACKING,
    "Function / Measurement": FailureType.FUNCTIONAL,
    "Weight": FailureType.FUNCTIONAL,
    "Program Specific Requirements": FailureType.COMPLIANCE,
    "Labeling": FailureType.COMPLIANCE,
    "Printed Materials": FailureType.COMPLIANCE,
    "Markings": FailureType.COMPLIANCE,
    "Barcode Verification": FailureType.COMPLIANCE,
}


def classify_result_state(report: InspectionReport) -> ResultState:
    return ResultState(report.overall_result.upper())


def classify_failure_type(report: InspectionReport) -> FailureType:
    """Route by the failing Section-B line items and the F/P code.

    Compliance is detected first: an F-series code with clean workmanship is a
    program gap (e.g. F8 = missing lab test report) and belongs on the rules
    track, not GenAI (PRD §9.1).
    """
    state = classify_result_state(report)
    if state is ResultState.PASS:
        return FailureType.NONE

    failing = [
        section
        for section, verdict in report.result_summary.items()
        if str(verdict).upper() in {"FAIL", "PENDING"}
    ]
    types = {_SUMMARY_TO_TYPE[s] for s in failing if s in _SUMMARY_TO_TYPE}

    # Prefer the most defect-bearing physical failure; compliance only if alone.
    for preferred in (
        FailureType.WORKMANSHIP,
        FailureType.FUNCTIONAL,
        FailureType.PACKING,
    ):
        if preferred in types:
            return preferred
    if FailureType.COMPLIANCE in types:
        return FailureType.COMPLIANCE

    # Fall back to the F/P code family when the summary is ambiguous.
    code = (report.fail_code or "").upper()
    if code.startswith("F"):
        return FailureType.COMPLIANCE
    return FailureType.WORKMANSHIP


def should_draft(report: InspectionReport) -> bool:
    """Trigger CAPA drafting only on FAIL or PENDING (PRD §5)."""
    return classify_result_state(report) in {ResultState.FAIL, ResultState.PENDING}


def is_rules_track(report: InspectionReport) -> bool:
    """Compliance-only failures are deterministic -> rules track / human, not GenAI."""
    return classify_failure_type(report) is FailureType.COMPLIANCE
