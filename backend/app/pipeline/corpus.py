"""Knowledge corpus loader — single source of truth for both retrievers.

Reads `backend/corpus/*.md` documents (id/title frontmatter + body). These stand
in for SOPs, quality standards, and prior 8D/FMEA reports (PRD §5). Add or edit
files here and re-index (`scripts/index_corpus.py`) to update the RAG corpus.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus"


@dataclass
class Document:
    id: str
    title: str
    text: str


def _parse(path: Path) -> Document | None:
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        for line in front.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    doc_id = meta.get("id") or path.stem
    return Document(id=doc_id, title=meta.get("title", doc_id), text=body.strip())


@lru_cache
def load_corpus(corpus_dir: Path | None = None) -> list[Document]:
    directory = corpus_dir or _CORPUS_DIR
    if not directory.exists():
        return []
    docs = [_parse(p) for p in sorted(directory.glob("*.md"))]
    return [d for d in docs if d is not None]
