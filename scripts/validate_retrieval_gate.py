#!/usr/bin/env python3
"""Validate RAG deliverables: indexes, RAG tool, transport tools, retrieval metrics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))


def main() -> int:
    import os

    # Smoke tests use the on-disk index with embedding fallback and rerank disabled.
    os.environ.setdefault("JOURNEYX_EMBEDDING_FALLBACK", "true")
    os.environ.setdefault("JOURNEYX_DISABLE_RERANK", "true")

    errors: list[str] = []

    manifest = yaml.safe_load((ROOT / "data/manifest.yaml").read_text(encoding="utf-8"))
    if manifest.get("document_count", 0) < 500:
        errors.append("document_count < 500")
    if not manifest.get("chunking_winner"):
        errors.append("chunking_winner not set — run ingest")
    chunk_count = manifest.get("chunk_count", 0)
    if chunk_count < 400:
        errors.append(f"chunk_count {chunk_count} too low")

    index_dir = ROOT / "data/indexes/v1"
    for name in ("chunks.jsonl", "bm25.pkl", "embeddings_v1.npy"):
        if not (index_dir / name).exists() and name != "embeddings_v1.npy":
            errors.append(f"Missing index artifact: {name}")
    if not (index_dir / "dense.faiss").exists():
        errors.append("Missing dense.faiss")

    report = ROOT / "reports/retrieval_eval_v1.json"
    if not report.is_file():
        errors.append("Missing reports/retrieval_eval_v1.json")
    else:
        metrics = json.loads(report.read_text(encoding="utf-8"))
        if metrics.get("labeled_queries", 0) < 25:
            errors.append("retrieval eval labeled_queries < 25")

    try:
        from journeyx.tools.search_kb import search_travel_kb
        from journeyx.tools.transport import compare_transport, get_route_info

        kb = search_travel_kb("best months Jaipur", dest_id="dest_jaipur", top_k=3)
        if not kb.get("chunks"):
            errors.append("search_travel_kb returned no chunks")
        route = get_route_info("city_delhi", "city_jaipur")
        if not route.get("distance_km"):
            errors.append("get_route_info failed")
        cmp = compare_transport("city_delhi", "city_jaipur", 2)
        modes = cmp.get("modes", [])
        mode_names = {m["mode"] for m in modes}
        if "road_diesel" not in mode_names:
            errors.append("compare_transport missing road_diesel")
        if len(modes) < 4:
            errors.append("compare_transport returned too few modes")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Tool smoke failed: {exc}")

    if errors:
        print("Retrieval validation gate: FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Retrieval validation gate: PASSED")
    print(f"  chunking_winner: {manifest.get('chunking_winner')}")
    print(f"  chunk_count: {chunk_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())