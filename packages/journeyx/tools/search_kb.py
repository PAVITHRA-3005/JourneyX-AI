from __future__ import annotations

from typing import Any

from journeyx.rag.cache import cache_key, get_cached, set_cached
from journeyx.rag.models import SearchRequest
from journeyx.rag.retrieve import load_retriever

# Official reference links for supported destinations (v1 corpus)
DESTINATION_REFERENCE_LINKS: dict[str, str] = {
    "dest_jaipur": "https://www.rajasthantourism.gov.in/destinations/jaipur",
    "dest_goa": "https://www.goatourism.gov.in",
    "dest_manali": "https://www.hptdc.in/manali",
    "dest_kochi": "https://www.keralatourism.org/kochi",
    "dest_delhi": "https://www.delhitourism.gov.in",
    "dest_bangalore": "https://www.karnatakatourism.org/bengaluru",
    "dest_mumbai": "https://www.maharashtratourism.gov.in/mumbai",
    "dest_shimla": "https://www.hptdc.in/shimla",
    "dest_rishikesh": "https://www.uttarakhandtourism.gov.in/destination/rishikesh",
    "dest_agra": "https://www.uptourism.gov.in/agra",
    "dest_mysore": "https://www.karnatakatourism.org/mysuru",
    "dest_udaipur": "https://www.rajasthantourism.gov.in/destinations/udaipur",
    "dest_varanasi": "https://www.uptourism.gov.in/varanasi",
}


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
    # Collect unique dest_ids from retrieved chunks for reference links
    chunk_dest_ids = {c.get("dest_id") for c in chunks if c.get("dest_id")}
    if dest_id:
        chunk_dest_ids.add(dest_id)
    reference_links = [
        DESTINATION_REFERENCE_LINKS[did]
        for did in sorted(chunk_dest_ids)
        if did in DESTINATION_REFERENCE_LINKS
    ]

    result = {
        "query": query,
        "dest_id": dest_id,
        "top_k": top_k,
        "chunks": chunks,
        "disclaimer": "Retrieved from owned KB; verify indicative content.",
        "source": "tool:search_travel_kb",
        "cache_hit": False,
        "reference_links": reference_links,
    }
    set_cached(key, result)
    return result