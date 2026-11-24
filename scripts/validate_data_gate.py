#!/usr/bin/env python3
"""Validate data-layer deliverables: schemas, eval set, manifest, and required documents."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from pydantic import TypeAdapter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from journeyx.core.eval_item import EvalItem
from journeyx.core.structured import (
    Accommodation,
    City,
    DestinationProfile,
    Poi,
    PriceAssumption,
    Route,
    TransportOption,
    TravelDocument,
)


def load_jsonl(path: Path, model: type) -> list:
    adapter = TypeAdapter(model)
    rows = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(adapter.validate_json(line))
            except Exception as exc:
                raise ValueError(f"{path.name} line {i}: {exc}") from exc
    return rows


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    data = ROOT / "data"

    required_docs = [
        ROOT / "docs/product-spec.md",
        ROOT / "docs/refusal-policy.md",
        ROOT / "docs/dataset-schemas.md",
        ROOT / "docs/tool-contracts.md",
        ROOT / "data/eval/EVAL_FROZEN.md",
    ]
    for p in required_docs:
        if not p.is_file():
            errors.append(f"Missing doc: {p.relative_to(ROOT)}")

    eval_path = data / "eval/eval_v1.jsonl"
    eval_items: list[EvalItem] = []
    if not eval_path.is_file():
        errors.append("Missing data/eval/eval_v1.jsonl — run scripts/seed_eval_data.py")
    else:
        eval_items = load_jsonl(eval_path, EvalItem)
        if len(eval_items) < 60:
            errors.append(f"Eval count {len(eval_items)} < 60")
        cats = {i.category for i in eval_items}
        for need in ("refusal", "clarify", "rag_qa", "transport_compare", "full_plan", "refine"):
            if need not in cats:
                errors.append(f"Eval missing category: {need}")
        refine = [i for i in eval_items if i.category == "refine"]
        if any(not i.conversation_prefix for i in refine):
            errors.append("Refine eval items missing conversation_prefix")
        with_docs = sum(1 for i in eval_items if i.relevant_doc_ids)
        if with_docs < 20:
            errors.append(f"Eval items with relevant_doc_ids {with_docs} < 20")

    labels_path = data / "eval/retrieval_labels_v1.jsonl"
    label_count = 0
    if labels_path.is_file():
        label_count = sum(1 for l in labels_path.read_text(encoding="utf-8").splitlines() if l.strip())
        if label_count < 30:
            errors.append(f"retrieval_labels_v1 count {label_count} < 30")
    else:
        errors.append("Missing data/eval/retrieval_labels_v1.jsonl")

    manifest_path = data / "manifest.yaml"
    if manifest_path.is_file():
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        doc_count = manifest.get("document_count", 0)
        if doc_count < 500:
            errors.append(f"document_count {doc_count} < 500 (RAG entry requirement)")
    else:
        errors.append("Missing data/manifest.yaml")

    transport = data / "structured/transport_option.jsonl"
    if transport.is_file():
        modes = {json.loads(l)["mode"] for l in transport.read_text(encoding="utf-8").splitlines() if l.strip()}
        if "road_diesel" not in modes:
            errors.append("transport_option missing road_diesel mode")

    schema_files = [
        (data / "structured/cities.jsonl", City),
        (data / "structured/destination_profile.jsonl", DestinationProfile),
        (data / "structured/pois.jsonl", Poi),
        (data / "structured/accommodations.jsonl", Accommodation),
        (data / "structured/routes.jsonl", Route),
        (data / "structured/transport_option.jsonl", TransportOption),
        (data / "structured/price_assumption.jsonl", PriceAssumption),
        (data / "documents/documents.jsonl", TravelDocument),
    ]
    for path, model in schema_files:
        if not path.is_file():
            errors.append(f"Missing {path.relative_to(ROOT)}")
            continue
        try:
            load_jsonl(path, model)
        except ValueError as exc:
            errors.append(str(exc))

    summary = ROOT / "docs/baseline_results_summary.md"
    if not summary.is_file():
        warnings.append("Missing docs/baseline_results_summary.md — run export after baseline")
    elif "dry-run" in summary.read_text(encoding="utf-8"):
        warnings.append("Baseline summary is dry-run only — run live API before closing the data gate")

    if warnings:
        print("Data gate warnings:")
        for w in warnings:
            print(f"  ! {w}")

    if errors:
        print("Data validation gate: FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Data validation gate: PASSED (data + docs)")
    print(f"  Eval items: {len(eval_items)}")
    print(f"  Retrieval labels: {label_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())