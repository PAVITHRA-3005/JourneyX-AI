from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from journeyx.core.eval_item import EvalItem
from journeyx.eval.kb_context import load_kb_digest
from journeyx.llm.client import ChatMessage, LLMClient
from journeyx.observability.trace import TraceSpan, TraceWriter

StrategyId = Literal["A_structured", "B_cot", "C_decomposition"]

STRATEGY_FILES: dict[StrategyId, str] = {
    "A_structured": "strategy_a_structured_fewshot.md",
    "B_cot": "strategy_b_cot.md",
    "C_decomposition": "strategy_c_decomposition.md",
}


@dataclass
class BaselineResult:
    eval_id: str
    strategy: StrategyId
    category: str
    gold_fact_hits: int
    gold_fact_total: int
    refused_expected: bool
    refusal_detected: bool
    schema_ok: bool
    latency_ms: float
    tokens_in: int | None
    tokens_out: int | None
    errors: list[str]
    answer_preview: str


def load_eval(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(EvalItem.model_validate_json(line))
    return items


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_prompt(name: str) -> str:
    path = _project_root() / "prompts" / "baseline" / name
    return path.read_text(encoding="utf-8")


def _extract_answer_text(content: str, strategy: StrategyId) -> str:
    content = content.strip()
    if content.startswith("{"):
        try:
            data = json.loads(content)
            for key in ("answer", "final_answer", "reasoning"):
                if key in data and isinstance(data[key], str):
                    return data[key] if key != "reasoning" else (
                        data.get("answer") or data.get("final_answer") or data["reasoning"]
                    )
            return json.dumps(data)
        except json.JSONDecodeError:
            pass
    return content


def _detect_refusal(text: str, raw_content: str) -> bool:
    if raw_content.strip().startswith("{"):
        try:
            data = json.loads(raw_content)
            if data.get("refusal") is True:
                return True
        except json.JSONDecodeError:
            pass
    lower = (text + " " + raw_content).lower()
    patterns = [
        r"\bcannot book\b",
        r"\bcan't book\b",
        r"\bdo not book\b",
        r"\bunable to book\b",
        r"\blive (price|fare|rate)\b",
        r"\brefuse\b",
        r"\bnot able to\b.*\bbook",
    ]
    return any(re.search(p, lower) for p in patterns)


def _score_gold_facts(answer: str, facts: list[str]) -> tuple[int, int]:
    if not facts:
        return 0, 0
    lower = answer.lower()
    hits = sum(1 for fact in facts if fact.lower() in lower or _fact_token_match(lower, fact))
    return hits, len(facts)


def _fact_token_match(text: str, fact: str) -> bool:
    tokens = [t for t in re.split(r"[_\s]+", fact.lower()) if len(t) > 3]
    if not tokens:
        return fact.lower() in text
    return any(t in text for t in tokens)


def _schema_ok(content: str, strategy: StrategyId, dry_run: bool) -> bool:
    if dry_run:
        return False
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return False
    if strategy == "A_structured":
        return isinstance(data.get("answer"), str) and "slots" in data
    if strategy == "B_cot":
        return isinstance(data.get("answer"), str) and isinstance(data.get("reasoning"), str)
    if strategy == "C_decomposition":
        return isinstance(data.get("final_answer"), str) and isinstance(
            data.get("sub_questions"), list
        )
    return False


def _build_messages(
    item: EvalItem,
    system: str,
    strategy_prompt: str,
    include_kb: bool,
) -> list[ChatMessage]:
    system_text = system + "\n\n" + strategy_prompt
    if include_kb:
        system_text += "\n\n---\n" + load_kb_digest()
    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_text)]
    for turn in item.conversation_prefix:
        messages.append(ChatMessage(role=turn.role, content=turn.content))
    messages.append(ChatMessage(role="user", content=item.query))
    return messages


def run_baseline(
    strategy: StrategyId,
    eval_items: list[EvalItem],
    limit: int | None = None,
    trace_path: Path | None = None,
    include_kb: bool = False,
) -> list[BaselineResult]:
    client = LLMClient()
    system = _load_prompt("system_travel.md")
    strategy_prompt = _load_prompt(STRATEGY_FILES[strategy])
    writer = TraceWriter(trace_path or (_project_root() / "reports" / "traces.jsonl"))

    subset = eval_items if limit is None else eval_items[:limit]
    results: list[BaselineResult] = []

    for idx, item in enumerate(subset):
        trace_id = writer.new_trace_id()
        messages = _build_messages(item, system, strategy_prompt, include_kb)
        errors: list[str] = []
        try:
            resp = client.chat(messages, temperature=0.2)
        except Exception as exc:  # noqa: BLE001
            resp = None
            errors.append(str(exc))

        if resp is None:
            results.append(
                BaselineResult(
                    eval_id=item.id,
                    strategy=strategy,
                    category=item.category,
                    gold_fact_hits=0,
                    gold_fact_total=len(item.gold_facts),
                    refused_expected=item.expected_refusal,
                    refusal_detected=False,
                    schema_ok=False,
                    latency_ms=0.0,
                    tokens_in=None,
                    tokens_out=None,
                    errors=errors,
                    answer_preview="",
                )
            )
            continue

        answer_text = _extract_answer_text(resp.content, strategy)
        hits, total = _score_gold_facts(answer_text, item.gold_facts)
        refused = _detect_refusal(answer_text, resp.content)
        schema_ok = _schema_ok(resp.content, strategy, client.dry_run or not client.configured)

        writer.write(
            TraceSpan(
                trace_id=trace_id,
                thread_id=f"baseline-{item.id}",
                corpus_version=item.corpus_version,
                prompt_version=strategy,
                node="baseline",
                step_index=idx + 1,
                latency_ms=resp.latency_ms,
                tokens_in=resp.tokens_in,
                tokens_out=resp.tokens_out,
                status="ok" if not errors else "error",
                metadata={"eval_id": item.id, "category": item.category},
            )
        )

        results.append(
            BaselineResult(
                eval_id=item.id,
                strategy=strategy,
                category=item.category,
                gold_fact_hits=hits,
                gold_fact_total=total,
                refused_expected=item.expected_refusal,
                refusal_detected=refused,
                schema_ok=schema_ok,
                latency_ms=resp.latency_ms,
                tokens_in=resp.tokens_in,
                tokens_out=resp.tokens_out,
                errors=errors,
                answer_preview=answer_text[:200],
            )
        )

    return results


def summarize_results(results: list[BaselineResult]) -> dict[str, Any]:
    if not results:
        return {}
    n = len(results)
    schema_rate = sum(1 for r in results if r.schema_ok) / n
    fact_rate = (
        sum(r.gold_fact_hits / r.gold_fact_total for r in results if r.gold_fact_total) / n
    )
    refusal_items = [r for r in results if r.refused_expected]
    refusal_acc = (
        sum(1 for r in refusal_items if r.refusal_detected) / len(refusal_items)
        if refusal_items
        else None
    )
    return {
        "count": n,
        "schema_valid_rate": round(schema_rate, 3),
        "avg_gold_fact_recall": round(fact_rate, 3),
        "refusal_accuracy": round(refusal_acc, 3) if refusal_acc is not None else None,
        "avg_latency_ms": round(sum(r.latency_ms for r in results) / n, 1),
    }