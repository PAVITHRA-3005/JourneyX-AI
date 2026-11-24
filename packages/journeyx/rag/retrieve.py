from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

from journeyx.rag.dense import DenseIndex
from journeyx.rag.embeddings import EmbeddingsClient
from journeyx.rag.fusion import reciprocal_rank_fusion
from journeyx.rag.ingest import load_chunks_jsonl, load_rag_config, project_root
from journeyx.rag.models import ChunkRecord, RetrievalHit, SearchRequest
from journeyx.rag.rerank import CrossEncoderReranker
from journeyx.rag.sparse import BM25Index


class HybridRetriever:
    def __init__(
        self,
        chunks: list[ChunkRecord],
        bm25: BM25Index,
        dense: DenseIndex,
        vectors: np.ndarray,
        cfg: dict,
    ) -> None:
        self.chunks = chunks
        self.bm25 = bm25
        self.dense = dense
        self.vectors = vectors
        self.cfg = cfg
        self.embed_client = EmbeddingsClient()
        rerank_cfg = cfg.get("reranker", {})
        self.reranker = CrossEncoderReranker(rerank_cfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"))

    def _filter_indices(self, dest_id: str | None, doc_types: list[str]) -> set[int] | None:
        if not dest_id and not doc_types:
            return None
        allowed: set[int] = set()
        for i, c in enumerate(self.chunks):
            if dest_id and c.dest_id != dest_id:
                continue
            if doc_types and c.doc_type not in doc_types:
                continue
            allowed.add(i)
        return allowed

    def search(self, request: SearchRequest) -> list[RetrievalHit]:
        rcfg = self.cfg["retrieval"]
        allowed = self._filter_indices(request.dest_id, request.doc_types)

        bm25_hits = self.bm25.search(request.query, rcfg["bm25_top_k"], allowed)
        q_vec = self.embed_client.embed_texts([request.query])[0]
        dense_hits = self.dense.search(q_vec, rcfg["dense_top_k"], allowed)

        fused = reciprocal_rank_fusion([bm25_hits, dense_hits], k=rcfg.get("rrf_k", 60))[
            : rcfg["fused_top_k"]
        ]

        cand_chunks: list[ChunkRecord] = []
        cand_scores: list[float] = []
        for idx, score in fused:
            cand_chunks.append(self.chunks[idx])
            cand_scores.append(score)

        reranked = self.reranker.rerank(request.query, cand_chunks, cand_scores, request.top_k)

        hits: list[RetrievalHit] = []
        for chunk, score in reranked:
            excerpt = chunk.text[:400] + ("…" if len(chunk.text) > 400 else "")
            hits.append(
                RetrievalHit(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    doc_type=chunk.doc_type,
                    dest_id=chunk.dest_id,
                    excerpt=excerpt,
                    score=score,
                    citation_id=chunk.doc_id,
                )
            )
        return hits


@lru_cache(maxsize=1)
def load_retriever() -> HybridRetriever:
    root = project_root()
    cfg = load_rag_config()
    version = cfg.get("corpus_version", "v1")
    index_dir = root / "data/indexes" / version
    chunks = load_chunks_jsonl(index_dir / "chunks.jsonl")
    bm25 = BM25Index.load(index_dir / "bm25.pkl")
    dense, vectors = DenseIndex.load(index_dir / "dense")
    return HybridRetriever(chunks, bm25, dense, vectors, cfg)