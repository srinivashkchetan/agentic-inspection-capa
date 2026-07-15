"""Parallel retrieval: exact facts from the RDBMS, grounding from RAG (PRD §5).

RDBMS facts are the report record itself (system of record). RAG returns top-k
grounding chunks. Two retrievers share one corpus (`app/pipeline/corpus.py`):

* ``SeedRetriever``   — keyword overlap, zero deps (used in tests / fallback).
* ``ChromaRetriever`` — embedded Chroma vector DB with a pluggable embedding
                        function (the real vector store, PRD §5.2).

``get_retriever()`` picks one from settings (``CAPA_RETRIEVER`` = auto|chroma|seed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from app.config import get_settings
from app.models import FailureType, InspectionReport
from app.pipeline.corpus import Document, load_corpus

_COLLECTION = "capa_knowledge"


@dataclass
class RetrievedChunk:
    id: str  # citation id, e.g. "SOP-COATING-01"
    title: str
    text: str
    score: float = 0.0


@dataclass
class RetrievalResult:
    facts: dict = field(default_factory=dict)  # verbatim RDBMS facts
    chunks: list[RetrievedChunk] = field(default_factory=list)  # RAG grounding


_TYPE_HINTS: dict[FailureType, list[str]] = {
    FailureType.WORKMANSHIP: ["coating", "peel", "finish", "stitch", "paint", "z1.4"],
    FailureType.PACKING: ["carton", "packing", "drop", "z1.4"],
    FailureType.FUNCTIONAL: ["measurement", "function", "z1.4"],
    FailureType.COMPLIANCE: ["lab", "test report", "f8", "program"],
}


class Retriever:
    """Interface seam. Implementations embed/rank over the shared corpus."""

    def search(self, query: str, hint: FailureType, k: int = 3) -> list[RetrievedChunk]:
        raise NotImplementedError


def _augment(query: str, hint: FailureType) -> str:
    return f"{query} {' '.join(_TYPE_HINTS.get(hint, []))}".strip()


class SeedRetriever(Retriever):
    """Keyword-overlap retriever over the corpus (zero-infra, deterministic)."""

    def __init__(self, corpus: list[Document] | None = None) -> None:
        self._corpus = corpus if corpus is not None else load_corpus()

    def search(self, query: str, hint: FailureType, k: int = 3) -> list[RetrievedChunk]:
        terms = {t for t in _augment(query, hint).lower().split() if len(t) > 3}
        scored: list[RetrievedChunk] = []
        for doc in self._corpus:
            hay = f"{doc.title} {doc.text}".lower()
            score = sum(1 for t in terms if t in hay)
            if score:
                scored.append(RetrievedChunk(doc.id, doc.title, doc.text, float(score)))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]


class ChromaRetriever(Retriever):
    """Embedded Chroma vector DB with a pluggable embedding function."""

    def __init__(
        self,
        path: str | None = None,
        corpus: list[Document] | None = None,
        embedding_function=None,
    ) -> None:
        import chromadb

        from app.pipeline.embeddings import HashingEmbeddingFunction

        settings = get_settings()
        self._client = chromadb.PersistentClient(path=path or settings.capa_chroma_path)
        self._ef = embedding_function or HashingEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION, embedding_function=self._ef
        )
        self.index(corpus if corpus is not None else load_corpus())

    def index(self, corpus: list[Document]) -> int:
        """Upsert corpus documents into the collection. Returns doc count."""
        if not corpus:
            return 0
        self._collection.upsert(
            ids=[d.id for d in corpus],
            documents=[f"{d.title}\n{d.text}" for d in corpus],
            metadatas=[{"title": d.title} for d in corpus],
        )
        return len(corpus)

    def search(self, query: str, hint: FailureType, k: int = 3) -> list[RetrievedChunk]:
        res = self._collection.query(query_texts=[_augment(query, hint)], n_results=k)
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        chunks: list[RetrievedChunk] = []
        for i, doc_id in enumerate(ids):
            title = (metas[i] or {}).get("title", doc_id) if metas else doc_id
            text = docs[i].split("\n", 1)[-1] if docs else ""
            dist = dists[i] if dists else 0.0
            chunks.append(RetrievedChunk(doc_id, title, text, score=1.0 / (1.0 + float(dist))))
        return chunks


@lru_cache
def get_retriever() -> Retriever:
    """Select the retriever from settings (auto falls back to seed)."""
    choice = get_settings().capa_retriever.lower()
    if choice in {"chroma", "auto"}:
        try:
            return ChromaRetriever()
        except Exception:
            if choice == "chroma":
                raise
    return SeedRetriever()


def collect_facts(report: InspectionReport) -> dict:
    """Exact, verbatim facts from the RDBMS record (never generated, PRD §5)."""
    g = report.general
    return {
        "report_id": report.report_id,
        "overall_result": report.overall_result,
        "fail_code": report.fail_code,
        "fail_reason": report.fail_reason,
        "vendor": g.vendor_supplier_name if g else None,
        "factory": g.factory_name if g else None,
        "retail_market": g.retail_market if g else None,
        "department": g.department_name if g else None,
        "product_category": g.product_category if g else None,
        "country_of_origin": g.country_of_origin if g else None,
        "protocol_no": g.protocol_no if g else None,
        "products": [p.model_dump(exclude_none=True) for p in report.products],
        "visual_defects": (
            [d.model_dump() for d in report.visual_check.defects]
            if report.visual_check
            else []
        ),
        "remarks": report.remarks,
    }


def build_query(report: InspectionReport) -> str:
    """Small, targeted query from the failing defects (keeps context lean)."""
    parts: list[str] = [report.fail_reason or ""]
    if report.visual_check:
        parts += [
            d.defect_description or "" for d in report.visual_check.defects if d.major or d.minor
        ]
    return " ".join(p for p in parts if p).strip() or (report.fail_reason or report.report_id)


def retrieve(
    report: InspectionReport,
    failure_type: FailureType,
    retriever: Retriever | None = None,
    k: int | None = None,
) -> RetrievalResult:
    retriever = retriever or get_retriever()
    top_k = k if k is not None else get_settings().capa_rag_top_k
    chunks = retriever.search(build_query(report), failure_type, k=top_k)
    return RetrievalResult(facts=collect_facts(report), chunks=chunks)
