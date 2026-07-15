"""Pluggable embedding function for the RAG layer (PRD §5.2).

Default is a dependency-free, deterministic hashed bag-of-words embedding so the
vector DB works offline and in CI with no model download and no external API.
Swap in real semantic embeddings (e.g. a sentence-transformer or a provider
endpoint) by supplying a different embedding function to the Chroma collection —
the retriever interface is unchanged.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _stable_hash(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")


class HashingEmbeddingFunction:
    """Signed hashed bag-of-words -> L2-normalized vector (lexical similarity).

    Conforms to Chroma's embedding-function protocol: callable ``(input) -> list``
    plus ``name`` / ``get_config`` / ``build_from_config`` for persistence.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002 (Chroma API)
        return [self._embed(text) for text in input]

    # Chroma >=1.x calls these on the collection's embedding function.
    def embed_documents(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return self(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return self(input)

    @staticmethod
    def is_legacy() -> bool:
        return False

    @staticmethod
    def default_space() -> str:
        return "cosine"

    @staticmethod
    def supported_spaces() -> list[str]:
        return ["cosine", "l2", "ip"]

    def _embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _tokens(text):
            h = _stable_hash(tok)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec.tolist()

    # --- Chroma persistence hooks -------------------------------------------
    @staticmethod
    def name() -> str:
        return "capa_hashing"

    def get_config(self) -> dict:
        return {"dim": self.dim}

    @classmethod
    def build_from_config(cls, config: dict) -> "HashingEmbeddingFunction":
        return cls(dim=config.get("dim", 256))
