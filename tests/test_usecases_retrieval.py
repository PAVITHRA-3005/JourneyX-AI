"""RAG use cases: RAG, hybrid retrieval, all structured tools."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from journeyx.core.planner_output import TaskPlanItem, TripSlots
from journeyx.tools.budget import estimate_budget
from journeyx.tools.discovery import find_accommodations, list_pois, lookup_destinations
from journeyx.tools.registry import run_task, tool_catalog
from journeyx.tools.search_kb import search_travel_kb
from journeyx.tools.transport import compare_transport, get_route_info


def test_tool_catalog_has_eight_tools() -> None:
    assert len(tool_catalog()) >= 8


def test_hybrid_search_jaipur_with_citations() -> None:
    result = search_travel_kb("best months Jaipur", dest_id="dest_jaipur", top_k=5)
    assert result["chunks"]
    assert all(c["citation"].startswith("[cite:") for c in result["chunks"])


def test_get_route_info_delhi_jaipur() -> None:
    info = get_route_info("city_delhi", "city_jaipur")
    assert info.get("distance_km", 0) > 0
    assert "disclaimer" in info


def test_compare_transport_modes_and_party_scaling() -> None:
    out = compare_transport("city_delhi", "city_jaipur", party_size=2)
    modes = {m["mode"] for m in out["modes"]}
    assert {"train", "road_diesel"} <= modes
    assert out["party_size"] == 2


def test_lookup_destinations_query() -> None:
    out = lookup_destinations(query="jaipur")
    assert out["count"] >= 1
    assert any(d["dest_id"] == "dest_jaipur" for d in out["destinations"])


def test_find_accommodations_dest_jaipur() -> None:
    out = find_accommodations("dest_jaipur", tier="mid")
    assert "stays" in out
    assert all("price_per_night_inr" in s for s in out["stays"])


def test_list_pois_dest_jaipur() -> None:
    out = list_pois("dest_jaipur")
    assert len(out["pois"]) >= 1


def test_estimate_budget_increases_with_nights() -> None:
    short = estimate_budget("dest_jaipur", nights=1, party_size=1)
    long = estimate_budget("dest_jaipur", nights=4, party_size=1)
    assert long["total_inr"] > short["total_inr"]


def test_registry_runs_every_task_type() -> None:
    slots = TripSlots(
        origin_city_id="city_delhi",
        dest_city_id="city_jaipur",
        dest_id="dest_jaipur",
        days=3,
        party_size=2,
        pace="moderate",
    )
    from typing import cast

    from journeyx.core.planner_output import TaskType

    for task_name in tool_catalog():
        item = TaskPlanItem(task=cast(TaskType, task_name), rationale="test")
        result = run_task(item, slots, "Jaipur trip plan")
        assert "error" not in result or result.get("error") != "unknown_task", task_name


def test_retrieval_eval_metrics_file(project_root: Path) -> None:
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, str(project_root / "scripts/run_retrieval_eval.py")],
        cwd=project_root,
        check=True,
    )
    metrics = json.loads((project_root / "reports/retrieval_eval_v1.json").read_text(encoding="utf-8"))
    assert metrics["labeled_queries"] >= 25
    assert 0 <= metrics["recall@5"] <= 1


def test_manifest_chunking_winner(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "data/manifest.yaml").read_text(encoding="utf-8"))
    assert manifest.get("chunking_winner") == "structure_aware"
    assert manifest.get("chunk_count", 0) >= 400


def test_index_artifacts_present(project_root: Path) -> None:
    idx = project_root / "data/indexes/v1"
    for name in ("chunks.jsonl", "bm25.pkl", "dense.faiss", "embeddings_v1.npy"):
        assert (idx / name).is_file(), name