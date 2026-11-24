# Baseline results summary (auto-generated)

Generated: 2026-11-14T16:41:47.277247+00:00
Run type: **dry-run — configure .env and re-run**

## Strategy summaries

| Strategy | N | schema_valid_rate | avg_gold_fact_recall | refusal_accuracy | avg_latency_ms |
|----------|---|-------------------|----------------------|------------------|----------------|
| A_structured | 5 | 0.0 | 0.0 | 0.0 | 0.0 |
| B_cot | 5 | 0.0 | 0.0 | 0.0 | 0.0 |
| C_decomposition | 5 | 0.0 | 0.0 | 0.0 | 0.0 |

## Failure modes (fill after live run)

| Mode | A | B | C | Notes |
|------|---|---|---|-------|
| Invalid JSON | | | | |
| Hallucinated prices | | | | |
| Missing clarify | | | | |
| Refusal miss | | | | |

See `docs/baseline-prompting.md` for methodology.