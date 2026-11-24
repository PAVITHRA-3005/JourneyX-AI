#!/usr/bin/env python3
"""Build hybrid retrieval indexes (RAG)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from journeyx.rag.chunking import load_documents
from journeyx.rag.ingest import ingest_corpus
from journeyx.rag.linter import lint_documents


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", type=str, default=None)
    parser.add_argument("--experiment", action="store_true", help="Run chunking ablation")
    parser.add_argument("--lint-only", action="store_true")
    args = parser.parse_args()

    docs = load_documents(ROOT / "data/documents/documents.jsonl")
    issues = lint_documents(docs)
    errors = [i for i in issues if i.severity == "error"]
    if issues:
        print(f"Lint: {len(issues)} issues ({len(errors)} errors)")
        for item in issues[:20]:
            print(f"  [{item.severity}] {item.doc_id}: {item.message}")
    if errors:
        return 1
    if args.lint_only:
        return 0

    report = ingest_corpus(strategy=args.strategy, run_experiment=args.experiment)
    print(json.dumps(report, indent=2))
    load_retriever = None  # noqa: F841
    from journeyx.rag import retrieve

    retrieve.load_retriever.cache_clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())