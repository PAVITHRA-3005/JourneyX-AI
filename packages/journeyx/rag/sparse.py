from __future__ import annotations

import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from journeyx.rag.models import ChunkRecord

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class BM25Index:
    def __init__(self, chunks: list[ChunkRecord]) -> None:
        self.chunks = chunks
        self._corpus = [tokenize(f"{c.title} {c.text}") for c in chunks]
        self._bm25 = BM25Okapi(self._corpus)

    def search(self, query: str, top_k: int = 20, allowed: set[int] | None = None) -> list[tuple[int, float]]:
        tokens = tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        hits: list[tuple[int, float]] = []
        for idx, score in ranked:
            if score <= 0:
                continue
            if allowed is not None and idx not in allowed:
                continue
            hits.append((idx, float(score)))
            if len(hits) >= top_k:
                break
        return hits

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump({"chunks": self.chunks, "bm25": self._bm25}, f)

    @classmethod
    def load(cls, path: Path) -> BM25Index:
        with path.open("rb") as f:
            data = pickle.load(f)
        obj = cls.__new__(cls)
        obj.chunks = data["chunks"]
        obj._corpus = [tokenize(f"{c.title} {c.text}") for c in obj.chunks]
        obj._bm25 = data["bm25"]
        return obj