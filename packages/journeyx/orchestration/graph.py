from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from journeyx.orchestration.budgets import MAX_CRITIC_REVISES, over_budget
from journeyx.orchestration.nodes import (
    composer_node,
    critic_node,
    executor_node,
    planner_node,
    policy_node,
)
from journeyx.orchestration.state import AgentState

CHECKPOINT_DB = Path(__file__).resolve().parents[3] / "data" / "checkpoints.sqlite"
_compiled_app = None


def _route_after_policy(state: AgentState) -> Literal["planner", "composer"]:
    if state.get("policy_action") == "refuse":
        return "composer"
    return "planner"


def _route_after_planner(state: AgentState) -> Literal["executor", "composer"]:
    if state.get("status") == "clarify":
        return "composer"
    return "executor"


def _route_after_critic(state: AgentState) -> Literal["executor", "composer"]:
    if over_budget(state):
        return "composer"
    if state.get("critic_verdict") == "REVISE" and int(state.get("critic_revises", 0)) < MAX_CRITIC_REVISES:
        return "executor"
    return "composer"


def build_graph():
    """Build and compile LangGraph (creates new instance)."""
    graph = StateGraph(AgentState)
    graph.add_node("policy", policy_node)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("composer", composer_node)

    graph.set_entry_point("policy")
    graph.add_conditional_edges("policy", _route_after_policy, {"planner": "planner", "composer": "composer"})
    graph.add_conditional_edges("planner", _route_after_planner, {"executor": "executor", "composer": "composer"})
    graph.add_edge("executor", "critic")
    graph.add_conditional_edges("critic", _route_after_critic, {"executor": "executor", "composer": "composer"})
    graph.add_edge("composer", END)

    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    # One SQLite checkpointer per process suits a single uvicorn worker.
    # Use an external store when running multiple workers.
    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    memory = SqliteSaver(conn)
    return graph.compile(checkpointer=memory)


def get_compiled_graph():
    """Singleton compiled app for production serving."""
    global _compiled_app
    if _compiled_app is None:
        _compiled_app = build_graph()
    return _compiled_app


def run_turn(
    user_message: str,
    thread_id: str | None = None,
    conversation_prefix: list[dict[str, str]] | None = None,
) -> dict:
    app = get_compiled_graph()
    thread_id = thread_id or str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    initial: AgentState = {
        "thread_id": thread_id,
        "trace_id": trace_id,
        "user_message": user_message,
        "conversation_prefix": conversation_prefix or [],
        "step_count": 0,
        "llm_calls": 0,
        "tool_calls": 0,
        "critic_revises": 0,
        "spans": [],
        "status": "ok",
    }
    config = {"configurable": {"thread_id": thread_id}}
    final = app.invoke(initial, config=config)
    return {
        "thread_id": thread_id,
        "trace_id": trace_id,
        "response": final.get("final_response", ""),
        "status": final.get("status", "ok"),
        "step_count": final.get("step_count", 0),
        "tool_calls": final.get("tool_calls", 0),
        "planner_intent": (final.get("planner") or {}).get("intent"),
        "spans": final.get("spans", []),
        "followup_suggestions": final.get("followup_suggestions", []),
    }
