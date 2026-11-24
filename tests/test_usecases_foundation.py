"""Foundation use cases: specs, eval, schemas, baseline dry-run, credentials."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from journeyx.core.eval_item import EvalItem
from journeyx.core.planner_output import PlannerOutput, TaskPlanItem, TripSlots
from journeyx.observability.trace import TraceSpan, TraceWriter

REQUIRED_DOCS = [
    "docs/product-spec.md",
    "docs/refusal-policy.md",
    "docs/dataset-schemas.md",
    "docs/tool-contracts.md",
    "data/eval/EVAL_FROZEN.md",
]

REQUIRED_CATEGORIES = {
    "refusal",
    "clarify",
    "rag_qa",
    "transport_compare",
    "full_plan",
    "refine",
}


def test_required_documentation_exists(project_root: Path) -> None:
    for rel in REQUIRED_DOCS:
        assert (project_root / rel).is_file(), rel


def test_eval_v1_categories_and_size(project_root: Path) -> None:
    path = project_root / "data/eval/eval_v1.jsonl"
    items: list[EvalItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(EvalItem.model_validate_json(line))
    assert len(items) >= 60
    cats = {i.category for i in items}
    assert REQUIRED_CATEGORIES <= cats
    refusal = [i for i in items if i.category == "refusal"]
    assert all(i.expected_refusal for i in refusal)


def test_manifest_foundation_counts(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "data/manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["document_count"] >= 500
    assert manifest["eval_count"] >= 60
    assert manifest["retrieval_label_count"] >= 30


def test_structured_corpus_loads(project_root: Path) -> None:
    from journeyx.core.structured import TravelDocument

    docs = project_root / "data/documents/documents.jsonl"
    n = 0
    for line in docs.read_text(encoding="utf-8").splitlines():
        if line.strip():
            TravelDocument.model_validate(json.loads(line))
            n += 1
    assert n >= 500


def test_planner_output_schema_roundtrip() -> None:
    model = PlannerOutput(
        intent="compare_transport",
        slots=TripSlots(origin_city_id="city_delhi", dest_city_id="city_jaipur", party_size=2),
        tasks=[TaskPlanItem(task="compare_transport", rationale="user asked modes")],
    )
    again = PlannerOutput.model_validate_json(model.model_dump_json())
    assert again.intent == "compare_transport"
    assert again.tasks[0].task == "compare_transport"


def test_capstone_settings_load_without_local_yaml(project_root: Path) -> None:
    from journeyx.config.capstone import get_settings, reload_settings

    reload_settings()
    s = get_settings()
    assert s.chat.model == "Qwen/Qwen3-8B" or s.chat.model
    assert (project_root / "config/credentials.example.yaml").is_file()


def test_baseline_dry_run_sample(project_root: Path) -> None:
    from journeyx.eval.baseline import load_eval, run_baseline

    items = load_eval(project_root / "data/eval/eval_v1.jsonl")
    results = run_baseline("A_structured", items, limit=6, include_kb=False)
    assert len(results) == 6
    assert all(r.latency_ms == 0.0 or r.schema_ok is not None for r in results)


def test_trace_writer_append(project_root: Path, tmp_path: Path) -> None:
    writer = TraceWriter(tmp_path / "traces.jsonl")
    tid = writer.new_trace_id()
    writer.write(
        TraceSpan(
            trace_id=tid,
            thread_id="t1",
            corpus_version="v1",
            prompt_version="test",
            node="planner",
            step_index=1,
            latency_ms=1.0,
        )
    )
    assert (tmp_path / "traces.jsonl").read_text(encoding="utf-8").strip()


def test_baseline_prompt_files_exist(project_root: Path) -> None:
    base = project_root / "prompts/baseline"
    for name in ("strategy_a_structured_fewshot.md", "strategy_b_cot.md", "strategy_c_decomposition.md"):
        assert (base / name).is_file()