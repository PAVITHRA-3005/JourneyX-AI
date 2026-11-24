import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_search_travel_kb_citations():
    from journeyx.tools.search_kb import search_travel_kb

    result = search_travel_kb("Amber Fort Jaipur", dest_id="dest_jaipur", top_k=5)
    assert result["chunks"]
    assert all("citation" in c and c["citation"].startswith("[cite:") for c in result["chunks"])


def test_compare_transport_delhi_jaipur():
    from journeyx.tools.transport import compare_transport

    out = compare_transport("city_delhi", "city_jaipur", 2)
    modes = {m["mode"] for m in out["modes"]}
    assert "train" in modes
    assert "road_diesel" in modes


def test_retrieval_eval_report_exists():
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_retrieval_eval.py")],
        cwd=ROOT,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "packages")},
        check=True,
    )
    data = json.loads((ROOT / "reports/retrieval_eval_v1.json").read_text(encoding="utf-8"))
    assert data["labeled_queries"] >= 25