#!/usr/bin/env python3
"""Run end-to-end agent evaluation on the frozen eval_v1 set."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from journeyx.eval.agent_eval import load_eval, run_agent_eval, write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval", type=Path, default=ROOT / "data/eval/eval_v1.jsonl")
    parser.add_argument("--limit", type=int, default=30, help="Subset for quota safety")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/agent_eval_v1.json")
    args = parser.parse_args()
    items = load_eval(args.eval)
    rows = run_agent_eval(items, limit=args.limit)
    write_report(rows, args.out)
    print(f"Wrote {args.out} ({len(rows)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())