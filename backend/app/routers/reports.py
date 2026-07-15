"""Report endpoints: browse ingested FRI reports and trigger CAPA drafting."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.data.repository import CapaStore, ReportRepository, get_capa_store, get_report_repository
from app.models import CapaDraft, InspectionReport
from app.pipeline.orchestrator import NotTriggerableError, draft_capa
from app.schemas import ReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
def list_reports(repo: ReportRepository = Depends(get_report_repository)) -> list[ReportSummary]:
    return [ReportSummary.from_report(r) for r in repo.list()]


@router.get("/{report_id}", response_model=InspectionReport)
def get_report(
    report_id: str, repo: ReportRepository = Depends(get_report_repository)
) -> InspectionReport:
    report = repo.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return report


@router.post("/{report_id}/draft", response_model=CapaDraft, status_code=201)
def draft(
    report_id: str,
    repo: ReportRepository = Depends(get_report_repository),
    store: CapaStore = Depends(get_capa_store),
) -> CapaDraft:
    """Run the pipeline for a report and persist the resulting draft (PRD §5)."""
    report = repo.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    try:
        capa = draft_capa(report)
    except NotTriggerableError as exc:
        # PASS reports are logged but do not draft a CAPA (PRD §5).
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return store.save(capa)
