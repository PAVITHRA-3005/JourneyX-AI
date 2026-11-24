#!/usr/bin/env python3
"""Write docs/baseline_results_summary.md from reports/baseline_results.json."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_STRAT_COL = {
    "A_structured": "A",
    "B_cot": "B",
    "C_decomposition": "C",
}


def _failure_counts(results: list[dict]) -> dict[str, dict[str, int]]:
    """Aggregate failure-mode counts per strategy column (A/B/C)."""
    modes = ("invalid_json", "hallucinated_prices", "missing_clarify", "refusal_miss")
    out: dict[str, dict[str, int]] = {m: {c: 0 for c in "ABC"} for m in modes}
    for row in results:
        strat = row.get("strategy", "")
        col = _STRAT_COL.get(strat)
        if not col:
            continue
        if not row.get("schema_ok"):
            out["invalid_json"][col] += 1
        if row.get("refused_expected") and not row.get("refusal_detected"):
            out["refusal_miss"][col] += 1
        if row.get("category") == "clarify" and not row.get("schema_ok"):
            out["missing_clarify"][col] += 1
        total = row.get("gold_fact_total") or 0
        hits = row.get("gold_fact_hits") or 0
        if row.get("category") in ("transport_compare", "full_plan", "rag_qa") and total > 0:
            if hits / total < 0.5:
                out["hallucinated_prices"][col] += 1
    return out


def main() -> int:
    src = ROOT / "reports/baseline_results.json"
    if not src.is_file():
        print("Run scripts/run_baseline.py first.")
        return 1

    data = json.loads(src.read_text(encoding="utf-8"))
    summaries = data.get("summaries", {})
    results = data.get("results", [])
    live = any(r.get("tokens_in") not in (None, 0) for r in results) or any(
        r.get("latency_ms", 0) > 0 for r in results
    )

    lines = [
        "# Baseline results summary (auto-generated)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Run type: **{'live API' if live else 'dry-run — configure .env and re-run'}**",
        "",
        "## Strategy summaries",
        "",
        "| Strategy | N | schema_valid_rate | avg_gold_fact_recall | refusal_accuracy | avg_latency_ms |",
        "|----------|---|-------------------|----------------------|------------------|----------------|",
    ]
    for strat, s in summaries.items():
        lines.append(
            f"| {strat} | {s.get('count')} | {s.get('schema_valid_rate')} | "
            f"{s.get('avg_gold_fact_recall')} | {s.get('refusal_accuracy')} | {s.get('avg_latency_ms')} |"
        )

    failures = _failure_counts(results)
    lines.extend(
        [
            "",
            "## Failure modes",
            "",
            "| Mode | A | B | C | Notes |",
            "|------|---|---|---|-------|",
        ]
    )
    notes = {
        "invalid_json": "schema_ok=false",
        "hallucinated_prices": "gold_fact recall <50% on plan/rag/transport",
        "missing_clarify": "clarify category + invalid schema",
        "refusal_miss": "expected_refusal but not detected",
    }
    labels = {
        "invalid_json": "Invalid JSON",
        "hallucinated_prices": "Hallucinated prices",
        "missing_clarify": "Missing clarify",
        "refusal_miss": "Refusal miss",
    }
    for mode in ("invalid_json", "hallucinated_prices", "missing_clarify", "refusal_miss"):
        f = failures[mode]
        lines.append(
            f"| {labels[mode]} | {f['A']} | {f['B']} | {f['C']} | {notes[mode]} |"
        )
    lines.extend(["", "See `docs/baseline-prompting.md` for methodology."])

    out = ROOT / "docs/baseline_results_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())