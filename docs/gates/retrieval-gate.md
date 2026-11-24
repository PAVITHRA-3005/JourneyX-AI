# Retrieval validation gate checklist (Track B — RAG / template III)

| Item | Status |
|------|--------|
| ≥500 documents | Done (523) |
| Chunking + winner in manifest | Done (`structure_aware`) |
| Hybrid BM25 + dense + RRF + rerank | `packages/journeyx/rag/` |
| `search_travel_kb` with citations | `packages/journeyx/tools/search_kb.py` |
| `get_route_info`, `compare_transport` | `packages/journeyx/tools/transport.py` |
| Corpus linter (SoT) | `packages/journeyx/rag/linter.py` |
| Recall@K report | `reports/retrieval_eval_v1.json` |
| No LangGraph yet | Agent|

**Validate:** `python scripts/validate_retrieval_gate.py`

**Note:** Production embedding index: `JOURNEYX_EMBEDDING_FALLBACK=false` + `ingest_corpus.py --experiment`. CI uses `JOURNEYX_EMBEDDING_FALLBACK=true`.