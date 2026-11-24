#!/usr/bin/env python3
"""Run prompting baselines (strategies A/B/C) on the frozen eval set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from dotenv import load_dotenv

from journeyx.eval.baseline import load_eval, run_baseline, summarize_results

STRATEGIES = ("A_structured", "B_cot", "C_decomposition")


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval", type=Path, default=ROOT / "data/eval/eval_v1.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="Max eval items (default all)")
    parser.add_argument(
        "--strategy",
        choices=STRATEGIES + ("all",),
        default="all",
    )
    parser.add_argument("--out", type=Path, default=ROOT / "reports/baseline_results.json")
    parser.add_argument(
        "--with-kb",
        action="store_true",
        help="Inject KB digest into system prompt (ablation)",
    )
    parser.add_argument("--export-summary", action="store_true", default=True)
    args = parser.parse_args()

    items = load_eval(args.eval)
    if not items:
        print("No eval items found.")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    all_summaries = {}
    all_rows = []

    strategies = STRATEGIES if args.strategy == "all" else (args.strategy,)
    for strat in strategies:
        results = run_baseline(strat, items, limit=args.limit, include_kb=args.with_kb)
        summary = summarize_results(results)
        all_summaries[strat] = summary
        all_rows.extend([r.__dict__ for r in results])
        print(f"{strat}: {json.dumps(summary)}")

    payload = {"summaries": all_summaries, "results": all_rows}
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    if args.export_summary:
        import subprocess

        subprocess.run(
            [sys.executable, str(ROOT / "scripts/export_baseline_summary.py")],
            check=False,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())