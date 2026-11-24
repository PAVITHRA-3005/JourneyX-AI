# RAG pipeline (RAG

## Architecture

```text
documents.jsonl → chunking → chunks.jsonl
    → embeddings (capstone API / dev fallback)
    → BM25 (rank_bm25) + FAISS (dense) → RRF fusion → cross-encoder rerank
```

## Commands

```bash
pip install -r requirements.txt
python scripts/ingest_corpus.py              # build indexes
python scripts/ingest_corpus.py --experiment # chunking ablation
python scripts/run_retrieval_eval.py         # Recall@K / MRR
python scripts/validate_retrieval_gate.py
```

## Configuration

See `config/rag.yaml` (chunking winner, top-k, RRF constant, reranker model).

## Tools

- `search_travel_kb(query, dest_id?, doc_types?, top_k)` — citations in `chunks[].citation`
- `get_route_info`, `compare_transport` — structured indicative data

## Metrics

Separate from E2E generation: `reports/retrieval_eval_v1.json` on `data/eval/retrieval_labels_v1.jsonl`.

## Environment

Primary: `config/credentials.local.yaml` (`embeddings` section). Optional overrides via `.env`.

| Variable | Purpose |
|----------|---------|
| `JOURNEYX_EMBEDDING_FALLBACK` | `false` for production VM02 ingest |
| `JOURNEYX_DISABLE_RERANK` | Skip cross-encoder (faster CI) |