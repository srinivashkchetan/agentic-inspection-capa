"""Shared fixtures. Tests run offline (stub generation) against an isolated DB."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Configure the environment BEFORE any app module imports read settings.
os.environ.setdefault("ANTHROPIC_API_KEY", "")  # force offline stub generation
# Isolated SQLite DB per test session (auto-seeded from the dataset).
_TEST_DB = Path(tempfile.gettempdir()) / "capa_test.db"
_TEST_DB.unlink(missing_ok=True)
os.environ["CAPA_DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
# Deterministic retrieval for pipeline/API tests (RAG-specific tests opt in).
os.environ.setdefault("CAPA_RETRIEVER", "seed")

import pytest

from app.data.repository import get_report_repository
from app.models import InspectionReport


@pytest.fixture(scope="session")
def reports() -> list[InspectionReport]:
    return get_report_repository().list()


@pytest.fixture(scope="session")
def fail_report(reports: list[InspectionReport]) -> InspectionReport:
    return next(r for r in reports if r.overall_result == "FAIL")


@pytest.fixture(scope="session")
def pass_report(reports: list[InspectionReport]) -> InspectionReport:
    return next(r for r in reports if r.overall_result == "PASS")
