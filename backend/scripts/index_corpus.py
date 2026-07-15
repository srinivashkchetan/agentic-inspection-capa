"""Index the knowledge corpus into the Chroma vector DB (PRD §5 RAG layer).

Usage:
    python -m scripts.index_corpus     # (re)build the vector index from corpus/

Reads backend/corpus/*.md and upserts them into the persistent Chroma collection
at CAPA_CHROMA_PATH using the configured embedding function.
"""

from __future__ import annotations

from app.config import get_settings
from app.pipeline.corpus import load_corpus
from app.pipeline.retrieve import ChromaRetriever


def main() -> None:
    settings = get_settings()
    corpus = load_corpus()
    retriever = ChromaRetriever(path=settings.capa_chroma_path, corpus=corpus)
    n = retriever.index(corpus)
    print(f"Indexed {n} documents into Chroma at {settings.capa_chroma_path}")


if __name__ == "__main__":
    main()
