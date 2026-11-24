#!/usr/bin/env python3
"""Run retrieval Recall@K / MRR and write reports/retrieval_eval_v1.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from journeyx.eval.retrieval_eval import evaluate_retriever
from journeyx.rag.retrieve import load_retriever


def main() -> int:
    retriever = load_retriever()
    metrics = evaluate_retriever(retriever, ROOT)
    out = ROOT / "reports/retrieval_eval_v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())