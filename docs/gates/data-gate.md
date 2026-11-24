# Data validation gate checklist

| Item | Status |
|------|--------|
| `docs/product-spec.md` | Done |
| `docs/refusal-policy.md` | Done |
| `docs/dataset-schemas.md` | Done |
| `docs/tool-contracts.md` | Done |
| `data/eval/eval_v1.jsonl` (≥60) | Done (re-seed; 71+ items) |
| `data/eval/retrieval_labels_v1.jsonl` (≥30) | Done (re-seed) |
| `data/eval/EVAL_FROZEN.md` | Done (SHA256) |
| Corpus ≥500 documents | Done (re-seed) |
| Structured + `road_diesel` transport | Done |
| Refine eval `conversation_prefix` | Done |
| Pydantic schemas | Done (`packages/journeyx/core/`) |
| LLM adapter + retries | Done (`packages/journeyx/llm/client.py`) |
| Trace stub | Done (`packages/journeyx/observability/trace.py`) |
| Baseline A/B/C runner | Done (`scripts/run_baseline.py`) |
| Validator | `python scripts/validate_data_gate.py` — **PASSED** |
| Baseline metrics ≥30 queries | Live run → `docs/baseline_results_summary.md` |
| No LangGraph / multi-agent | Confirmed |

**Validate:** `python scripts/validate_data_gate.py`

**Next:** run `ingest_corpus.py`, then LangGraph agent stack.