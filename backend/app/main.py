"""FastAPI application entry point — the JSON API the Next.js console consumes."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.routers import capas, reports

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and seed reports from the dataset if the DB is empty.
    from app.db import init_db

    init_db()
    yield


app = FastAPI(
    title="CAPA API",
    version=__version__,
    description="AI-Assisted Corrective Action Planning for quality inspection (PRD v1.1).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(capas.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "model": settings.capa_model,
        "generation_mode": "offline-stub" if settings.offline else "live",
    }
