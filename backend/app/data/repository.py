"""Report + CAPA persistence, backed by the relational store (PRD §5.2).

Same interface as before (list/get/save) so routers and the pipeline are
unchanged; the storage is now SQLAlchemy (SQLite dev / Postgres prod) instead of
in-memory. The reports table is the system of record for facts; the CAPA table
holds drafts and their workflow status.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db import CapaRow, ReportRow, get_session_factory, init_db
from app.models import CapaDraft, InspectionReport


class ReportRepository:
    """Read-only access to ingested FRI reports."""

    def list(self) -> list[InspectionReport]:
        with get_session_factory()() as session:
            rows = session.scalars(select(ReportRow)).all()
            return [InspectionReport.model_validate(r.payload) for r in rows]

    def get(self, report_id: str) -> InspectionReport | None:
        with get_session_factory()() as session:
            row = session.get(ReportRow, report_id)
            return InspectionReport.model_validate(row.payload) if row else None


class CapaStore:
    """Create/read/update CAPA drafts."""

    def save(self, draft: CapaDraft) -> CapaDraft:
        payload = draft.model_dump(mode="json")
        with get_session_factory().begin() as session:
            session.merge(
                CapaRow(
                    id=draft.id,
                    report_id=draft.report_id,
                    status=draft.status.value,
                    payload=payload,
                )
            )
        return draft

    def get(self, capa_id: str) -> CapaDraft | None:
        with get_session_factory()() as session:
            row = session.get(CapaRow, capa_id)
            return CapaDraft.model_validate(row.payload) if row else None

    def list(self) -> list[CapaDraft]:
        with get_session_factory()() as session:
            rows = session.scalars(select(CapaRow)).all()
            return [CapaDraft.model_validate(r.payload) for r in rows]


_report_repo: ReportRepository | None = None
_capa_store: CapaStore | None = None
_initialized = False


def _ensure_db() -> None:
    global _initialized
    if not _initialized:
        init_db()
        _initialized = True


def get_report_repository() -> ReportRepository:
    global _report_repo
    _ensure_db()
    if _report_repo is None:
        _report_repo = ReportRepository()
    return _report_repo


def get_capa_store() -> CapaStore:
    global _capa_store
    _ensure_db()
    if _capa_store is None:
        _capa_store = CapaStore()
    return _capa_store
