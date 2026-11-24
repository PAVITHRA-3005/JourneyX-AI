from __future__ import annotations

from typing import Any

from journeyx.rag.cache import cache_key, get_cached, set_cached
from journeyx.rag.models import SearchRequest
from journeyx.rag.retrieve import load_retriever


def search_travel_kb(
    query: str,
    dest_id: str | None = None,
    doc_types: list[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    types = doc_types or []
    key = cache_key(query, dest_id, types, top_k)
    cached = get_cached(key)
    if cached is not None:
        return cached

    retriever = load_retriever()
    hits = retriever.search(
        SearchRequest(
            query=query,
            dest_id=dest_id,
            doc_types=doc_types or [],
            top_k=top_k,
        )
    )
    chunks = []
    for h in hits:
        chunks.append(
            {
                "doc_id": h.doc_id,
                "chunk_id": h.chunk_id,
                "title": h.title,
                "doc_type": h.doc_type,
                "dest_id": h.dest_id,
                "excerpt": h.excerpt,
                "score": h.score,
                "citation": h.cite_marker,
            }
        )
    result = {
        "query": query,
        "dest_id": dest_id,
        "top_k": top_k,
        "chunks": chunks,
        "disclaimer": "Retrieved from owned KB; verify indicative content.",
        "source": "tool:search_travel_kb",
        "cache_hit": False,
    }
    set_cached(key, result)
    return result