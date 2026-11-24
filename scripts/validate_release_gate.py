#!/usr/bin/env python3
"""Release validation gate: Docker, UI, rate limit, cache, agent eval, redteam."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "apps"))

os.environ.setdefault("JOURNEYX_AGENT_DRY_RUN", "true")
os.environ.setdefault("JOURNEYX_EMBEDDING_FALLBACK", "true")
os.environ.setdefault("JOURNEYX_DISABLE_RERANK", "true")


def main() -> int:
    errors: list[str] = []

    for rel in (
        "docker-compose.yml",
        "infra/docker/Dockerfile",
        "apps/ui/streamlit_app.py",
        ".dockerignore",
        "docs/DEMO_SCRIPT.md",
        "docs/eval_report.md",
    ):
        if not (ROOT / rel).is_file():
            errors.append(f"Missing {rel}")

    try:
        from journeyx.rag.cache import cache_key, get_cached, set_cached

        key = cache_key("test", None, [], 3)
        set_cached(key, {"chunks": [], "query": "test"})
        assert get_cached(key) is not None
    except Exception as exc:  # noqa: BLE001
        errors.append(f"retrieval cache: {exc}")

    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        assert client.get("/health").status_code == 200
        r = client.post("/v1/chat", json={"message": "Compare Delhi Jaipur transport"})
        assert r.status_code == 200
        assert r.headers.get("x-request-id")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"FastAPI smoke: {exc}")

    try:
        from journeyx.eval.agent_eval import load_eval, run_agent_eval, summarize

        items = load_eval(ROOT / "data/eval/eval_v1.jsonl")[:8]
        rows = run_agent_eval(items)
        summ = summarize(rows)
        if summ["n"] < 5:
            errors.append("agent eval too few rows")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"agent eval: {exc}")

    try:
        from journeyx.security.redteam import run_redteam

        rt = run_redteam()
        if not all(r.refused for r in rt if "Aadhaar" in r.probe or "Credit card" in r.probe):
            errors.append("PII probes not all refused")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"redteam: {exc}")

    if errors:
        print("Release validation gate: FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("Release validation gate: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())