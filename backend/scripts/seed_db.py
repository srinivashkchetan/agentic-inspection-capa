"""Seed the relational store from the JSON dataset.

Usage:
    python -m scripts.seed_db          # seed reports into the configured DB

Respects CAPA_DATABASE_URL / CAPA_DATA_PATH (see .env). Idempotent: rows are
merged by report_id.
"""

from __future__ import annotations

from app.config import get_settings
from app.db import get_session_factory, init_db, seed_reports


def main() -> None:
    settings = get_settings()
    init_db()  # ensure tables exist
    with get_session_factory().begin() as session:
        n = seed_reports(session, settings.data_path)
    print(f"Seeded {n} reports into {settings.database_url}")


if __name__ == "__main__":
    main()
