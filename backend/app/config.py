"""Application settings, loaded from environment / .env (PRD §5.2 tooling)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from this file: backend/app/config.py -> repo/
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic. Empty key -> offline stub generation (see pipeline/generate.py).
    anthropic_api_key: str = ""
    # Single MVP tier per PRD §9.1. Only the exact sanctioned ID; no date suffix.
    capa_model: str = "claude-opus-4-8"

    capa_data_path: str = str(_REPO_ROOT / "reports" / "inspection_reports_all.json")
    capa_cors_origins: str = "http://localhost:3000"

    # Relational store (facts + CAPAs). Empty -> SQLite file (zero-infra dev);
    # set a Postgres URL for prod via docker-compose (PRD §5.2).
    capa_database_url: str = ""
    # Seed the reports table from the JSON dataset on startup if empty.
    capa_seed_on_start: bool = True

    # RAG retriever: "auto" uses Chroma when installed, else the seed retriever.
    # Force one explicitly with "chroma" or "seed".
    capa_retriever: str = "auto"
    capa_chroma_path: str = str(_REPO_ROOT / "backend" / ".chroma")
    capa_rag_top_k: int = 3

    @property
    def data_path(self) -> Path:
        p = Path(self.capa_data_path)
        return p if p.is_absolute() else (_REPO_ROOT / p).resolve()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.capa_cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        """Effective SQLAlchemy URL; falls back to a local SQLite file."""
        return self.capa_database_url.strip() or f"sqlite:///{_REPO_ROOT / 'backend' / 'capa.db'}"

    @property
    def offline(self) -> bool:
        """True when no API key is configured -> deterministic stub generation."""
        return not self.anthropic_api_key.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
