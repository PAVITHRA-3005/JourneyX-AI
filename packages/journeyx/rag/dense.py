from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np

from journeyx.rag.models import ChunkRecord


class DenseIndex:
    def __init__(self, chunks: list[ChunkRecord], vectors: np.ndarray) -> None:
        if len(chunks) != vectors.shape[0]:
            raise ValueError("chunks and vectors length mismatch")
        self.chunks = chunks
        self.dim = vectors.shape[1]
        self._index = faiss.IndexFlatIP(self.dim)
        self._index.add(vectors.astype(np.float32))

    def search(
        self, query_vec: np.ndarray, top_k: int = 20, allowed: set[int] | None = None
    ) -> list[tuple[int, float]]:
        q = query_vec.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(q)
        k_search = min(len(self.chunks), max(top_k * 3, top_k))
        scores, indices = self._index.search(q, k_search)
        hits: list[tuple[int, float]] = []
        for idx, score in zip(indices[0], scores[0], strict=False):
            if idx < 0:
                continue
            if allowed is not None and int(idx) not in allowed:
                continue
            hits.append((int(idx), float(score)))
            if len(hits) >= top_k:
                break
        return hits

    def save(self, path: Path, vectors: np.ndarray) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(path.with_suffix(".faiss")))
        np.save(path.with_suffix(".npy"), vectors.astype(np.float32))

    @classmethod
    def load(cls, path: Path) -> tuple[DenseIndex, np.ndarray]:
        index_path = path.with_suffix(".faiss")
        vectors = np.load(path.with_suffix(".npy"))
        meta_chunks_path = path.parent / "chunks.jsonl"
        from journeyx.rag.ingest import load_chunks_jsonl

        chunks = load_chunks_jsonl(meta_chunks_path)
        obj = cls.__new__(DenseIndex)
        obj.chunks = chunks
        obj.dim = vectors.shape[1]
        obj._index = faiss.read_index(str(index_path))
        return obj, vectors