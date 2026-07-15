"""SQLAlchemy engine, ORM models, and schema/seed helpers (PRD §5.2).

The relational store is the system of record for facts and CAPAs. The full
inspection record is kept as JSON (OCR-flexible fields, PRD §5.1) alongside a few
indexed columns for filtering; CAPA drafts are stored as JSON payloads plus their
workflow status. `DATABASE_URL` selects SQLite (dev) or Postgres (prod) with no
code change.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import JSON, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class ReportRow(Base):
    __tablename__ = "inspection_reports"

    report_id: Mapped[str] = mapped_column(String, primary_key=True)
    overall_result: Mapped[str] = mapped_column(String, index=True)
    fail_code: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)  # full InspectionReport record


class CapaRow(Base):
    __tablename__ = "capa_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    report_id: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)  # full CapaDraft (JSON-mode dump)


def _connect_args(url: str) -> dict:
    # SQLite needs this to be usable across FastAPI's threadpool.
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


@lru_cache
def get_engine():
    url = get_settings().database_url
    return create_engine(url, connect_args=_connect_args(url), future=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables and, if enabled, seed the reports table when empty."""
    Base.metadata.create_all(get_engine())
    settings = get_settings()
    if settings.capa_seed_on_start:
        with get_session_factory().begin() as session:
            count = session.scalar(select(func.count()).select_from(ReportRow)) or 0
            if count == 0:
                seed_reports(session, settings.data_path)


def seed_reports(session: Session, data_path: Path) -> int:
    """Load the JSON dataset into the reports table. Returns rows inserted."""
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    records = raw.get("inspection_reports", raw) if isinstance(raw, dict) else raw
    inserted = 0
    for rec in records:
        session.merge(
            ReportRow(
                report_id=str(rec["report_id"]),
                overall_result=str(rec["overall_result"]).upper(),
                fail_code=rec.get("fail_code"),
                source=rec.get("source"),
                payload=rec,
            )
        )
        inserted += 1
    return inserted
