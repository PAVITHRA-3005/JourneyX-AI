# Foundation— Single-agent prompting baseline

## Strategies (Track B II)

| ID | File | Description |
|----|------|-------------|
| A_structured | `prompts/baseline/strategy_a_structured_fewshot.md` | JSON few-shot + slots |
| B_cot | `prompts/baseline/strategy_b_cot.md` | Chain-of-thought + answer |
| C_decomposition | `prompts/baseline/strategy_c_decomposition.md` | Sub-questions then synthesis |

## How to run

```bash
pip install -r requirements.txt
python scripts/seed_eval_data.py
# Keys in config/credentials.local.yaml (see docs/capstone-api-setup.md)
# Live run (Data validation gate):
# $env:JOURNEYX_BASELINE_DRY_RUN='false'
python scripts/run_baseline.py --limit 65
# Dry run without API:
# $env:JOURNEYX_BASELINE_DRY_RUN='true'
# python scripts/run_baseline.py --limit 30
```

Results: `reports/baseline_results.json`, traces: `reports/traces.jsonl`, summary: `docs/baseline_results_summary.md` (auto-exported).

Optional KB ablation: `python scripts/run_baseline.py --with-kb --limit 30`

## Metrics captured

- `schema_valid_rate` — valid JSON per strategy schema
- `avg_gold_fact_recall` — overlap with `eval_v1` `gold_facts`
- `refusal_accuracy` — on `expected_refusal` items
- `avg_latency_ms`, token usage when API configured

## Document how 8B breaks

After a live run, counts are auto-exported to **`docs/baseline_results_summary.md`** (Invalid JSON, hallucinated prices proxy, clarify, refusal miss). Add qualitative notes here if needed:

| Failure mode | A | B | C | Notes |
|--------------|---|---|---|-------|
| Verbose / token bloat | | | | inspect `reports/traces.jsonl` |

## Data validation gate

Baseline on **≥65** queries (`run_baseline.py --limit 65`) before agent code. Use `scripts/complete_live_baseline.ps1` with Capstone APIs reachable (campus/VPN).