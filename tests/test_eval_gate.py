import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_eval_count_and_manifest():
    eval_path = ROOT / "data/eval/eval_v1.jsonl"
    lines = [line for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 60

    manifest = yaml.safe_load((ROOT / "data/manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["document_count"] >= 500
    assert manifest.get("retrieval_label_count", 0) >= 30


def test_eval_items_parse():
    from journeyx.core.eval_item import EvalItem

    eval_path = ROOT / "data/eval/eval_v1.jsonl"
    for line in eval_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            EvalItem.model_validate(json.loads(line))


def test_refine_has_context():
    from journeyx.core.eval_item import EvalItem

    eval_path = ROOT / "data/eval/eval_v1.jsonl"
    for line in eval_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = EvalItem.model_validate(json.loads(line))
        if item.category == "refine":
            assert len(item.conversation_prefix) >= 2


def test_road_diesel_in_transport():
    path = ROOT / "data/structured/transport_option.jsonl"
    modes = {json.loads(line)["mode"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    assert "road_diesel" in modes