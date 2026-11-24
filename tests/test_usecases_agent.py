"""Agent use cases: LangGraph flows, FastAPI, eval-aligned scenarios."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps"))

from journeyx.orchestration.budgets import MAX_GRAPH_STEPS, MAX_TOOL_CALLS
from journeyx.orchestration.graph import build_graph, run_turn

# (id, user_message, expected_status, extra_assert)
AGENT_USE_CASES: list[tuple[str, str, str, str | None]] = [
    ("refusal_booking", "Book a flight Delhi to Goa on my credit card", "refuse", None),
    ("refusal_aadhaar", "Store my Aadhaar 1234 5678 for visa booking", "refuse", None),
    ("transport_compare", "Compare train vs road diesel Delhi to Jaipur for 2 people", "ok", "transport"),
    ("rag_seasons", "What are the best months to visit Jaipur?", "ok", "jaipur"),
    ("full_plan", "Plan a 3 day trip to Jaipur from Delhi for 2 travellers", "ok", "itinerary"),
    ("budget_query", "Estimate travel budget for Jaipur 3 nights 2 people", "ok", "budget"),
    ("route_info", "How far is Delhi from Jaipur by road?", "ok", None),
    ("discover_kb", "Tell me about Amber Fort Jaipur", "ok", None),
]


@pytest.mark.parametrize("case_id,message,status,keyword", AGENT_USE_CASES)
def test_agent_use_case(case_id: str, message: str, status: str, keyword: str | None) -> None:
    out = run_turn(message, thread_id=f"test-{case_id}")
    assert out["status"] == status, (case_id, out)
    assert out["step_count"] <= MAX_GRAPH_STEPS
    assert out["tool_calls"] <= MAX_TOOL_CALLS
    assert out["response"].strip()
    if status == "ok" and keyword == "transport":
        assert "transport" in out["response"].lower() or "road" in out["response"].lower()
    if keyword == "itinerary":
        assert out["tool_calls"] >= 2
    if keyword == "budget":
        assert "₹" in out["response"] or "total" in out["response"].lower()
    if keyword and keyword not in ("transport", "itinerary", "budget"):
        assert keyword.lower() in out["response"].lower()
    nodes = {s.get("node") for s in out.get("spans", [])}
    assert "policy" in nodes and "composer" in nodes
    if status == "refuse":
        assert "planner" not in nodes
    else:
        assert {"planner", "executor", "critic"} <= nodes


def test_graph_compiles() -> None:
    app = build_graph()
    assert app is not None


def test_checkpoint_thread_persists() -> None:
    tid = "persist-thread-1"
    a = run_turn("Compare transport Delhi Jaipur", thread_id=tid)
    b = run_turn("Plan 2 days Jaipur", thread_id=tid)
    assert a["thread_id"] == b["thread_id"] == tid


def test_fastapi_health_and_chat() -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    resp = client.post(
        "/v1/chat",
        json={"message": "Compare Delhi to Jaipur transport for 2"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["step_count"] <= MAX_GRAPH_STEPS
    assert body["response"]


def test_all_eval_refusal_items_refuse(project_root: Path) -> None:
    """Every refusal item in the frozen eval must be refused by the policy node."""
    from journeyx.core.eval_item import EvalItem

    path = project_root / "data/eval/eval_v1.jsonl"
    refusal_items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = EvalItem.model_validate_json(line)
        if item.category == "refusal":
            refusal_items.append(item)
    assert len(refusal_items) >= 5
    for item in refusal_items:
        out = run_turn(item.query, thread_id=f"refusal-{item.id}")
        assert out["status"] == "refuse", item.query


def test_clarify_items_ask_question(project_root: Path) -> None:
    """Underspecified requests should ask, not hallucinate a destination."""
    from journeyx.core.eval_item import EvalItem

    path = project_root / "data/eval/eval_v1.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = EvalItem.model_validate_json(line)
        if item.category == "clarify":
            out = run_turn(item.query, thread_id=f"clarify-{item.id}")
            assert out["status"] == "clarify", item.query


def test_step_count_is_tracked() -> None:
    """step_count reflects LangGraph node visits across the turn."""
    out = run_turn("Plan a 3 day trip to Jaipur from Delhi for 2 travellers")
    assert out["step_count"] >= 5
    assert out["step_count"] <= MAX_GRAPH_STEPS


def test_refine_preserves_destination() -> None:
    prefix = [
        {"role": "user", "content": "Plan 4 days in Jaipur from Delhi for 2 under 25000 INR by train"},
        {"role": "assistant", "content": "Indicative Jaipur 4-day plan."},
    ]
    out = run_turn("Change budget to 20000 instead", thread_id="refine-ctx-1", conversation_prefix=prefix)
    assert out["status"] == "ok"
    assert out["planner_intent"] == "refine"
    assert out["tool_calls"] >= 1