"""Chroma vector DB retrieval grounds against the right corpus doc (PRD §5)."""

from __future__ import annotations

import pytest

from app.models import FailureType
from app.pipeline.embeddings import HashingEmbeddingFunction

chromadb = pytest.importorskip("chromadb")

from app.pipeline.retrieve import ChromaRetriever  # noqa: E402


def test_embedding_is_deterministic_and_normalized() -> None:
    ef = HashingEmbeddingFunction(dim=64)
    a = ef(["coating peel off at edge"])[0]
    b = ef(["coating peel off at edge"])[0]
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-5


def test_chroma_retrieves_relevant_doc(tmp_path) -> None:
    retriever = ChromaRetriever(path=str(tmp_path / "chroma"))
    hits = retriever.search("coating peel off at edge", FailureType.WORKMANSHIP, k=3)
    assert hits
    assert "SOP-COATING-01" in {h.id for h in hits}
    assert hits[0].score > 0


def test_compliance_query_finds_f8_doc(tmp_path) -> None:
    retriever = ChromaRetriever(path=str(tmp_path / "chroma"))
    hits = retriever.search("no valid lab test report", FailureType.COMPLIANCE, k=3)
    assert "SOP-LABTEST-F8" in {h.id for h in hits}
