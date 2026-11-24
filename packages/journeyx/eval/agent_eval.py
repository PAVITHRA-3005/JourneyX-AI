from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from journeyx.core.eval_item import EvalItem
from journeyx.orchestration.graph import run_turn

FailureClass = Literal[
    "ok",
    "refusal_miss",
    "refusal_false_positive",
    "clarify_miss",
    "no_grounding",
    "no_tool_result",
    "incomplete_plan",
    "refine_incomplete",
    "step_budget",
    "empty_response",
    "other",
]


@dataclass
class AgentEvalRow:
    eval_id: str
    category: str
    query: str
    status: str
    step_count: int
    tool_calls: int
    failure_class: FailureClass
    gold_fact_hits: int
    gold_fact_total: int
    notes: str


def load_eval(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(EvalItem.model_validate_json(line))
    return items


def _fact_hits(text: str, gold_facts: list[str]) -> int:
    low = text.lower()
    hits = 0
    for fact in gold_facts:
        if fact.lower() in low:
            hits += 1
    return hits


def _classify(item: EvalItem, out: dict) -> FailureClass:
    """Classify agent output against frozen eval expectations (strict, per category)."""
    resp = (out.get("response") or "").strip()
    status = out.get("status", "")
    low = resp.lower()

    if not resp:
        return "empty_response"
    if out.get("step_count", 0) > 10:
        return "step_budget"

    if item.expected_refusal:
        return "ok" if status == "refuse" else "refusal_miss"
    if status == "refuse":
        return "refusal_false_positive"

    if item.category == "clarify":
        return "ok" if status == "clarify" else "clarify_miss"

    if item.category == "rag_qa":
        return "ok" if ("[cite:" in resp or "kb:" in low) else "no_grounding"

    if item.category == "transport_compare":
        return "ok" if ("transport option:" in low or "route:" in low) else "no_tool_result"

    if item.category == "full_plan":
        return "ok" if "itinerary:" in low else "incomplete_plan"

    if item.category == "refine":
        # Refine passes when the turn updates the plan while keeping prior context.
        if status == "ok" and ("itinerary:" in low or "estimated total:" in low):
            return "ok"
        return "refine_incomplete"

    return "ok"


def run_agent_eval(items: list[EvalItem], limit: int | None = None) -> list[AgentEvalRow]:
    subset = items if limit is None else items[:limit]
    rows: list[AgentEvalRow] = []
    for item in subset:
        prefix = [{"role": m.role, "content": m.content} for m in item.conversation_prefix]
        out = run_turn(item.query, thread_id=f"eval-{item.id}", conversation_prefix=prefix)
        resp = out.get("response") or ""
        failure = _classify(item, out)
        hits = _fact_hits(resp, item.gold_facts)
        rows.append(
            AgentEvalRow(
                eval_id=item.id,
                category=item.category,
                query=item.query,
                status=out.get("status", ""),
                step_count=out.get("step_count", 0),
                tool_calls=out.get("tool_calls", 0),
                failure_class=failure,
                gold_fact_hits=hits,
                gold_fact_total=len(item.gold_facts),
                notes="",
            )
        )
    return rows


def summarize(rows: list[AgentEvalRow]) -> dict:
    by_cat: dict[str, list[AgentEvalRow]] = {}
    for r in rows:
        by_cat.setdefault(r.category, []).append(r)
    failure_counts: dict[str, int] = {}
    for r in rows:
        failure_counts[r.failure_class] = failure_counts.get(r.failure_class, 0) + 1
    return {
        "n": len(rows),
        "task_completion_rate": sum(1 for r in rows if r.failure_class == "ok") / max(len(rows), 1),
        "avg_tool_calls": sum(r.tool_calls for r in rows) / max(len(rows), 1),
        "avg_step_count": sum(r.step_count for r in rows) / max(len(rows), 1),
        "failure_taxonomy": failure_counts,
        "by_category": {
            cat: {
                "n": len(rs),
                "ok_rate": sum(1 for r in rs if r.failure_class == "ok") / max(len(rs), 1),
            }
            for cat, rs in by_cat.items()
        },
    }


def write_report(rows: list[AgentEvalRow], path: Path) -> None:
    summary = summarize(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "results": [asdict(r) for r in rows],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")