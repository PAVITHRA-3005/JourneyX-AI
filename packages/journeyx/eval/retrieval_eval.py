from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from journeyx.rag.dense import DenseIndex
from journeyx.rag.embeddings import EmbeddingsClient, embed_chunks
from journeyx.rag.fusion import reciprocal_rank_fusion
from journeyx.rag.models import ChunkRecord, SearchRequest
from journeyx.rag.rerank import CrossEncoderReranker
from journeyx.rag.sparse import BM25Index


def load_retrieval_labels(root: Path) -> list[dict[str, Any]]:
    path = root / "data/eval/retrieval_labels_v1.jsonl"
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _resolve_relevant_doc_ids(row: dict[str, Any]) -> list[str]:
    return row.get("relevant_doc_ids", [])


def _hits_to_doc_ids(chunks: list[ChunkRecord], ranked_indices: list[int], k: int) -> list[str]:
    seen: list[str] = []
    for idx in ranked_indices[:k]:
        doc_id = chunks[idx].doc_id
        if doc_id not in seen:
            seen.append(doc_id)
    return seen


def evaluate_strategy(chunks: list[ChunkRecord], root: Path) -> dict[str, float]:
    """In-memory hybrid retrieval metrics for chunking experiment."""
    labels = load_retrieval_labels(root)
    if not chunks:
        return {"recall@5": 0.0, "recall@10": 0.0, "mrr@10": 0.0}

    client = EmbeddingsClient()
    vectors = embed_chunks(chunks, client)
    bm25 = BM25Index(chunks)
    dense = DenseIndex(chunks, vectors)
    reranker = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")

    recall5 = recall10 = mrr_sum = 0.0
    n = 0
    for row in labels:
        gold_docs = _resolve_relevant_doc_ids(row)
        if not gold_docs:
            continue
        query = row["query"]
        bm25_hits = bm25.search(query, 20)
        q_vec = client.embed_texts([query])[0]
        dense_hits = dense.search(q_vec, 20)
        fused = reciprocal_rank_fusion([bm25_hits, dense_hits], k=60)[:20]
        cand_chunks = [chunks[i] for i, _ in fused]
        cand_scores = [s for _, s in fused]
        reranked = reranker.rerank(query, cand_chunks, cand_scores, 10)
        ranked_doc_ids = []
        for ch, _ in reranked:
            if ch.doc_id not in ranked_doc_ids:
                ranked_doc_ids.append(ch.doc_id)

        n += 1
        if any(g in ranked_doc_ids[:5] for g in gold_docs):
            recall5 += 1
        if any(g in ranked_doc_ids[:10] for g in gold_docs):
            recall10 += 1
        rr = 0.0
        for rank, doc_id in enumerate(ranked_doc_ids[:10], start=1):
            if doc_id in gold_docs:
                rr = 1.0 / rank
                break
        mrr_sum += rr

    if n == 0:
        return {"recall@5": 0.0, "recall@10": 0.0, "mrr@10": 0.0, "count": 0.0}

    return {
        "recall@5": round(recall5 / n, 4),
        "recall@10": round(recall10 / n, 4),
        "mrr@10": round(mrr_sum / n, 4),
        "count": float(n),
    }


def evaluate_retriever(retriever, root: Path) -> dict[str, Any]:
    labels = load_retrieval_labels(root)
    recall5 = recall10 = mrr_sum = 0.0
    n = 0
    for row in labels:
        gold = _resolve_relevant_doc_ids(row)
        if not gold:
            continue
        hits = retriever.search(SearchRequest(query=row["query"], top_k=10))
        ranked = [h.doc_id for h in hits]
        n += 1
        if any(g in ranked[:5] for g in gold):
            recall5 += 1
        if any(g in ranked[:10] for g in gold):
            recall10 += 1
        rr = 0.0
        for rank, doc_id in enumerate(ranked[:10], start=1):
            if doc_id in gold:
                rr = 1.0 / rank
                break
        mrr_sum += rr
    return {
        "corpus_version": "v1",
        "recall@5": round(recall5 / n, 4) if n else 0.0,
        "recall@10": round(recall10 / n, 4) if n else 0.0,
        "mrr@10": round(mrr_sum / n, 4) if n else 0.0,
        "labeled_queries": n,
    }