# JourneyX evaluation report (template)

Fill after running scripts on VPN where needed.

## Datasets

| Asset | Path | Count |
|-------|------|-------|
| Corpus | `data/manifest.yaml` | document_count |
| Frozen eval | `data/eval/eval_v1.jsonl` | 72 |
| Retrieval labels | `data/eval/retrieval_labels_v1.jsonl` | 42+ |

## Retrieval (template III)

Source: `reports/retrieval_eval_v1.json`

| Metric | Value |
|--------|-------|
| Recall@5 | |
| Recall@10 | |
| MRR@10 | |
| embedding_fallback | from manifest |

## Baseline prompting (template II)

Source: `reports/baseline_results.json`, `docs/baseline_results_summary.md`

| Strategy | schema_valid_rate | gold_fact_recall | refusal_accuracy |
|----------|-------------------|------------------|------------------|
| A | | | |
| B | | | |
| C | | | |

## Agent E2E (template IV–V)

Generate:

```powershell
.\.venv\Scripts\python.exe scripts\run_agent_eval.py --limit 72
```

Source: `reports/agent_eval_v1.json`

| Metric | Value |
|--------|-------|
| task_completion_rate | |
| avg_tool_calls | |
| avg_step_count | |

### Failure taxonomy

| Class | Count |
|-------|-------|
| ok | |
| refusal_miss | |
| no_grounding | |
| step_budget | |
| … | |

## Responsible AI

```powershell
.\.venv\Scripts\python.exe scripts\run_redteam.py
```

Attach `reports/redteam_log.jsonl` excerpt.

## Ablation (optional)

Chunking experiment: `ingest_corpus.py --experiment`

## How we compensate for 8B

- Code-first Executor
- Hybrid RAG + structured SoT
- Policy refusal node
- Step/tool caps