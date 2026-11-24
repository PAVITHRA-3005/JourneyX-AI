from __future__ import annotations

MAX_GRAPH_STEPS = 10
MAX_LLM_CALLS = 4
MAX_TOOL_CALLS = 8
MAX_CRITIC_REVISES = 2
TARGET_HAPPY_STEPS = 6


def step_update(state: dict, node: str) -> dict:
    """Return a state update that increments the step counter and appends a span.

    LangGraph only persists what a node *returns*, so counters must be returned
    (absolute values on LastValue channels), never mutated in place.
    """
    count = int(state.get("step_count", 0)) + 1
    spans = list(state.get("spans") or []) + [{"node": node, "step_index": count}]
    return {"step_count": count, "spans": spans}


def over_budget(state: dict) -> bool:
    return int(state.get("step_count", 0)) >= MAX_GRAPH_STEPS