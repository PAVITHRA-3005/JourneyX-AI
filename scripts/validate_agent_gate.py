#!/usr/bin/env python3
"""Validate Agent LangGraph agent, tools, FastAPI surface."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

# Defaults for offline gate validation (no live APIs).
os.environ.setdefault("JOURNEYX_AGENT_DRY_RUN", "true")
os.environ.setdefault("JOURNEYX_EMBEDDING_FALLBACK", "true")
os.environ.setdefault("JOURNEYX_DISABLE_RERANK", "true")


def main() -> int:
    errors: list[str] = []

    try:
        from journeyx.tools.registry import tool_catalog

        if len(tool_catalog()) < 8:
            errors.append("tool_catalog has fewer than 8 internal tools")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tool registry: {exc}")

    try:
        from journeyx.orchestration.graph import build_graph, run_turn

        build_graph()
        refuse = run_turn("please book my flight with credit card now")
        if refuse.get("status") != "refuse":
            errors.append("policy refusal path did not trigger")
        if refuse.get("step_count", 99) > 10:
            errors.append("refusal path exceeded step cap")

        plan = run_turn("Compare train vs road from Delhi to Jaipur for 2 people")
        if plan.get("step_count", 99) > 10:
            errors.append("happy path exceeded 10 steps")
        if not plan.get("response"):
            errors.append("executor/composer returned empty response")
        nodes = {s.get("node") for s in plan.get("spans", [])}
        for need in ("policy", "planner", "executor", "critic", "composer"):
            if need not in nodes:
                errors.append(f"missing span node={need}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"graph smoke: {exc}")

    try:
        sys.path.insert(0, str(ROOT / "apps"))
        from api.main import app  # noqa: F401

        if not any(getattr(r, "path", "") == "/v1/chat" for r in app.router.routes):
            errors.append("FastAPI missing /v1/chat")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"FastAPI import: {exc}")

    api_main = ROOT / "apps" / "api" / "main.py"
    if not api_main.is_file():
        errors.append("missing apps/api/main.py")

    if errors:
        print("Agent validation gate: FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Agent validation gate: PASSED")
    print("  LangGraph: planner → executor → critic")
    print("  Tools:", len(tool_catalog()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())