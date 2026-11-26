from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    thread_id: str
    trace_id: str
    user_message: str
    conversation_prefix: list[dict[str, str]]

    step_count: int
    llm_calls: int
    tool_calls: int
    critic_revises: int

    policy_action: str  # continue | refuse
    policy_reason: str

    planner: dict[str, Any]
    executor_bundle: list[dict[str, Any]]
    critic_verdict: str  # APPROVE | REVISE | REFUSE
    critic_notes: list[str]

    trip_slots: dict[str, Any]
    final_response: str
    status: str  # ok | clarify | refuse | degraded

    spans: list[dict[str, Any]]
    followup_suggestions: list[str]
