from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

import yaml

from journeyx.core.planner_output import PlannerOutput, TaskPlanItem, TripSlots
from journeyx.llm.client import ChatMessage, LLMClient
from journeyx.observability.trace import TraceSpan, TraceWriter
from journeyx.orchestration.budgets import MAX_LLM_CALLS, step_update
from journeyx.tools.registry import run_task

# Refusal patterns (see docs/refusal-policy.md).
REFUSAL_PATTERNS = [
    r"\bbook\b.*\b(flight|train|hotel|ticket|room|cab|taxi)\b",
    r"\bbook\b",
    r"\bpurchase\b",
    r"\birctc\b",
    r"\breserve\b",
    r"\bcredit card\b",
    r"\bdebit card\b",
    r"\bon my card\b",
    r"\baadhaar\b",
    r"\bpassport\b",
    r"\bpay\s*now\b",
    r"\bpayment\b",
    # Live pricing, availability, or cheapest-fare guarantees
    r"\bguarantee\b.*\bcheapest\b",
    r"\blive\b.*\b(price|fare|availability|rate)\b",
    r"\breal[\s-]?time\b.*\b(price|fare|availability)\b",
    # Medical or pharmaceutical advice
    r"\b(medicine|medication|prescription|dosage|tablet)\b",
    # Unsafe or illegal travel
    r"\billegal\b",
    r"\bborder crossing\b",
    r"\bsmuggl",
    r"\bwithout (a )?visa\b",
    r"\bfake (id|passport|ticket|document)\b",
    # Prompt injection and policy override
    r"\bignore\b.*\b(instructions|policy|policies|rules)\b",
    r"\bdisregard\b.*\b(policy|policies|instructions|rules)\b",
    r"\bjailbreak\b",
]

# City names resolved to structured city IDs for slot filling and clarify gating.
CITY_NAME_TO_ID = {
    "delhi": "city_delhi",
    "jaipur": "city_jaipur",
    "goa": "city_goa",
    "manali": "city_manali",
    "kochi": "city_kochi",
    "bangalore": "city_bangalore",
    "bengaluru": "city_bangalore",
    "mumbai": "city_mumbai",
    "shimla": "city_shimla",
    "rishikesh": "city_rishikesh",
    "agra": "city_agra",
    "mysore": "city_mysore",
    "mysuru": "city_mysore",
    "udaipur": "city_udaipur",
    "varanasi": "city_varanasi",
}

LANDMARK_TOKENS = {
    "amber",
    "hawa",
    "taj",
    "qutub",
    "gateway",
    "solang",
    "baga",
    "marine drive",
    "mall road",
    "backwater",
}

REFINE_CUES = [
    "instead",
    "change",
    "switch",
    "add ",
    "more day",
    "another day",
    "relaxed",
    "packed",
    "budget stay",
    "budget tier",
    "remove",
    "prefer",
    "make it",
    "cheaper",
]

MONTHS = [
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
]

TRANSPORT_CUES = (
    "transport", "compare", "train", "flight", "bus", "road", "distance", "how far", "route", "drive",
)

TRACE_PATH = Path(__file__).resolve().parents[3] / "reports" / "agent_traces.jsonl"
_TRACE_WRITER: TraceWriter | None = None
_CORPUS_VERSION: str | None = None


def _writer() -> TraceWriter:
    global _TRACE_WRITER
    if _TRACE_WRITER is None:
        _TRACE_WRITER = TraceWriter(TRACE_PATH)
    return _TRACE_WRITER


def _corpus_version() -> str:
    global _CORPUS_VERSION
    if _CORPUS_VERSION is None:
        manifest = Path(__file__).resolve().parents[3] / "data" / "manifest.yaml"
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
            _CORPUS_VERSION = str(data.get("corpus_version", "v1"))
        except Exception:  # noqa: BLE001
            _CORPUS_VERSION = "v1"
    return _CORPUS_VERSION


def _log_span(state: dict, node: str, latency_ms: float, **meta: Any) -> None:
    span = TraceSpan(
        trace_id=state.get("trace_id", "local"),
        thread_id=state.get("thread_id", "default"),
        corpus_version=_corpus_version(),
        prompt_version="orchestration-v1",
        node=node,  # type: ignore[arg-type]
        step_index=int(state.get("step_count", 0)),
        latency_ms=latency_ms,
        tool_name=meta.get("tool_name"),
        status=meta.get("status", "ok"),
        metadata=meta,
    )
    _writer().write(span)


def _dest_id_for(city_id: str) -> str:
    return "dest_" + city_id.replace("city_", "")


def _parse_slots(text: str) -> dict[str, Any]:
    text = text.lower()
    slots: dict[str, Any] = {}

    positions: list[tuple[int, str]] = []
    for name, cid in CITY_NAME_TO_ID.items():
        for m in re.finditer(rf"\b{name}\b", text):
            positions.append((m.start(), cid))
    positions.sort()
    ordered: list[str] = []
    for _, cid in positions:
        if cid not in ordered:
            ordered.append(cid)

    origin: str | None = None
    dest: str | None = None

    m_from = re.search(r"\bfrom\s+([a-z]+)", text)
    if m_from and m_from.group(1) in CITY_NAME_TO_ID:
        origin = CITY_NAME_TO_ID[m_from.group(1)]
    m_to = re.search(r"\b([a-z]+)\s+to\s+([a-z]+)", text)
    if m_to and m_to.group(1) in CITY_NAME_TO_ID and m_to.group(2) in CITY_NAME_TO_ID:
        origin = CITY_NAME_TO_ID[m_to.group(1)]
        dest = CITY_NAME_TO_ID[m_to.group(2)]

    if dest is None:
        for cid in ordered:
            if cid != origin:
                dest = cid
                break
        if dest is None and ordered:
            dest = ordered[0]
    if origin is None:
        for cid in ordered:
            if cid != dest:
                origin = cid
                break

    if dest:
        slots["dest_city_id"] = dest
        slots["dest_id"] = _dest_id_for(dest)
    if origin:
        slots["origin_city_id"] = origin

    m_days = re.search(r"(\d+)\s*(day|night)", text)
    if m_days:
        slots["days"] = max(1, min(int(m_days.group(1)), 30))
    m_party = re.search(r"(\d+)\s*(people|person|persons|travell|pax|adult)", text)
    if m_party:
        slots["party_size"] = max(1, min(int(m_party.group(1)), 20))

    m_budget = re.search(r"\b(\d{4,6})\b", text)
    if m_budget and ("budget" in text or "under" in text or "inr" in text or "rs" in text or m_budget):
        slots["budget_inr"] = int(m_budget.group(1))

    if "relaxed" in text:
        slots["pace"] = "relaxed"
    elif "packed" in text:
        slots["pace"] = "packed"
    elif "moderate" in text:
        slots["pace"] = "moderate"

    for mo in MONTHS:
        if re.search(rf"\b{mo}\b", text):
            slots["month"] = mo
            break

    return slots


def _slots_model(data: dict[str, Any]) -> TripSlots:
    fields = set(TripSlots.model_fields)
    return TripSlots.model_validate({k: v for k, v in data.items() if k in fields})


# Common global location words that indicate a place is mentioned
_LOCATION_PREPOSITIONS = re.compile(
    r"\b(in|to|from|at|near|around|visit|visiting|travel|travelling|trip|plan|going)\s+[A-Z][a-z]",
    re.IGNORECASE,
)
_COUNTRY_WORDS = re.compile(
    r"\b(paris|london|dubai|singapore|bangkok|new york|tokyo|sydney|rome|barcelona|"
    r"amsterdam|berlin|istanbul|cairo|nairobi|toronto|vancouver|melbourne|"
    r"bali|phuket|kuala lumpur|hong kong|seoul|beijing|shanghai|moscow|"
    r"new zealand|australia|europe|asia|africa|america|usa|uk|france|italy|"
    r"spain|germany|japan|china|thailand|malaysia|indonesia|vietnam|nepal|"
    r"sri lanka|maldives|bhutan|pakistan|bangladesh|myanmar|cambodia|laos)\b",
    re.IGNORECASE,
)


def _has_location(text: str) -> bool:
    t = text.lower()
    # Check known Indian cities
    if any(re.search(rf"\b{name}\b", t) for name in CITY_NAME_TO_ID):
        return True
    # Check known landmarks
    if any(tok in t for tok in LANDMARK_TOKENS):
        return True
    # Check global cities/countries
    if _COUNTRY_WORDS.search(t):
        return True
    # Check location preposition patterns like "in Paris", "to London"
    if _LOCATION_PREPOSITIONS.search(text):
        return True
    return False


def _is_refine(text: str) -> bool:
    t = text.lower()
    return any(cue in t for cue in REFINE_CUES)


def policy_node(state: dict) -> dict:
    upd = step_update(state, "policy")
    msg = (state.get("user_message") or "").lower()
    for pat in REFUSAL_PATTERNS:
        if re.search(pat, msg):
            return {**upd, "policy_action": "refuse", "policy_reason": "refusal_policy_match", "status": "refuse"}
    return {**upd, "policy_action": "continue", "status": state.get("status", "ok")}


def _clarify_output(question: str) -> PlannerOutput:
    return PlannerOutput(
        intent="clarify",
        slots=TripSlots(),
        tasks=[],
        clarifying_question=question,
        confidence=0.6,
    )


def _heuristic_planner(user_message: str, prefix: list[dict[str, str]] | None) -> PlannerOutput:
    text = user_message.lower()

    # Refine: merge slot changes into the prior turn's plan.
    if prefix and _is_refine(text):
        base_text = " ".join(t.get("content", "") for t in prefix if t.get("role") == "user")
        base = _parse_slots(base_text)
        mod = _parse_slots(text)
        if "add" in text and ("day" in text):
            base["days"] = int(base.get("days") or 1) + 1
            mod.pop("days", None)
        merged = {**base, **{k: v for k, v in mod.items() if v is not None}}
        slots = _slots_model(merged)
        tasks = [
            TaskPlanItem(task="assemble_itinerary", rationale="refine itinerary, keep destination"),
            TaskPlanItem(task="estimate_budget", rationale="recompute indicative budget"),
            TaskPlanItem(task="search_travel_kb", rationale="context"),
        ]
        return PlannerOutput(intent="refine", slots=slots, tasks=tasks, confidence=0.7)

    # Clarify when no destination can be resolved from the message.
    if not _has_location(text):
        return _clarify_output(
            "Could you share the destination city (and ideally origin, dates, and budget) so I can plan?"
        )

    parsed = _parse_slots(text)
    slots = _slots_model(parsed)

    if any(cue in text for cue in TRANSPORT_CUES):
        intent = "compare_transport"
        tasks = [
            TaskPlanItem(task="get_route_info", rationale="route context"),
            TaskPlanItem(task="compare_transport", rationale="mode table"),
        ]
    elif "budget" in text or "cost" in text or "estimate" in text or "expense" in text:
        intent = "rag_qa"
        tasks = [
            TaskPlanItem(task="estimate_budget", rationale="deterministic total"),
            TaskPlanItem(task="search_travel_kb", rationale="grounding"),
        ]
    elif any(k in text for k in ("plan", "itinerary", "trip", "days", "day ")):
        intent = "full_plan"
        tasks = [
            TaskPlanItem(task="search_travel_kb", rationale="destination facts"),
            TaskPlanItem(task="list_pois", rationale="sightseeing"),
            TaskPlanItem(task="assemble_itinerary", rationale="day plan"),
            TaskPlanItem(task="estimate_budget", rationale="indicative budget"),
        ]
    else:
        intent = "rag_qa"
        tasks = [TaskPlanItem(task="search_travel_kb", rationale="answer from KB")]

    # For global destinations not in our city map, still proceed with rag_qa
    if intent == "full_plan" and not slots.dest_id:
        # Extract destination from text for global cities
        m_dest = re.search(r"\b(?:in|to|visit|visiting)\s+([A-Z][a-zA-Z\s]+?)(?:\s+from|\s+for|\s+by|\s+under|\s*$)", user_message)
        if m_dest:
            dest_name = m_dest.group(1).strip()
            slots = TripSlots.model_validate({**slots.model_dump(), "dest_id": f"dest_{dest_name.lower().replace(' ', '_')}"})
        else:
            # Fall back to rag_qa for general travel questions
            intent = "rag_qa"
            tasks = [TaskPlanItem(task="search_travel_kb", rationale="answer from KB")]

    return PlannerOutput(intent=intent, slots=slots, tasks=tasks, confidence=0.75)


def planner_node(state: dict) -> dict:
    upd = step_update(state, "planner")
    start = time.perf_counter()
    dry = os.getenv("JOURNEYX_AGENT_DRY_RUN", "true").lower() in ("1", "true", "yes")
    llm_calls = int(state.get("llm_calls", 0))

    output: PlannerOutput | None = None
    if not dry and llm_calls < MAX_LLM_CALLS and LLMClient().configured:
        llm = LLMClient()
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are JourneyX Planner. Return JSON for slots, intent, and tasks "
                    "using task names from the schema."
                ),
            ),
            ChatMessage(role="user", content=state.get("user_message", "")),
        ]
        for turn in state.get("conversation_prefix") or []:
            messages.insert(-1, ChatMessage(role=turn["role"], content=turn["content"]))
        parsed, _resp, _errs = llm.chat_structured(messages, PlannerOutput, temperature=0.1)
        llm_calls += 1
        output = parsed
        _log_span(state, "planner", (time.perf_counter() - start) * 1000, llm=True)

    if output is None:
        output = _heuristic_planner(
            state.get("user_message", ""),
            state.get("conversation_prefix"),
        )

    status = "clarify" if (output.intent == "clarify" or output.clarifying_question) else state.get("status", "ok")
    return {
        **upd,
        "planner": output.model_dump(),
        "trip_slots": output.slots.model_dump(),
        "status": status,
        "llm_calls": llm_calls,
    }


def executor_node(state: dict) -> dict:
    upd = step_update(state, "executor")
    planner = state.get("planner") or {}
    slots = TripSlots.model_validate(state.get("trip_slots") or {})
    tasks = [TaskPlanItem.model_validate(t) for t in planner.get("tasks", [])]
    user_message = state.get("user_message", "")

    bundle: list[dict[str, Any]] = []
    tool_calls = int(state.get("tool_calls", 0))
    for item in tasks:
        if tool_calls >= 8:
            break
        result = run_task(item, slots, user_message)
        bundle.append(result)
        tool_calls += 1
        _log_span(state, "executor", 0.0, tool_name=item.task, status="error" if result.get("error") else "ok")

    return {**upd, "executor_bundle": bundle, "tool_calls": tool_calls}


def critic_node(state: dict) -> dict:
    upd = step_update(state, "critic")
    notes: list[str] = []
    bundle = state.get("executor_bundle") or []
    planner = state.get("planner") or {}
    intent = planner.get("intent", "")
    revises = int(state.get("critic_revises", 0))

    if revises >= 1:
        return {**upd, "critic_verdict": "APPROVE", "critic_notes": ["best_effort_after_revise"], "critic_revises": revises}

    if not bundle:
        return {**upd, "critic_verdict": "REVISE", "critic_notes": ["executor produced no results"], "critic_revises": revises + 1}

    errors = [b for b in bundle if b.get("error")]
    if len(errors) == len(bundle):
        return {**upd, "critic_verdict": "REVISE", "critic_notes": ["all tasks failed"], "critic_revises": revises + 1}

    # RAG answers must include at least one retrieved chunk.
    if intent == "rag_qa":
        has_citation = any(b.get("chunks") for b in bundle)
        if not has_citation:
            notes.append("rag_qa without retrieved chunks")

    if intent in ("full_plan", "refine"):
        if not any(b.get("days_schedule") for b in bundle):
            return {**upd, "critic_verdict": "REVISE", "critic_notes": ["missing itinerary"], "critic_revises": revises + 1}

    return {**upd, "critic_verdict": "APPROVE", "critic_notes": notes, "critic_revises": revises}


def composer_node(state: dict) -> dict:
    upd = step_update(state, "composer")
    status = state.get("status", "ok")

    if state.get("policy_action") == "refuse":
        text = (
            "I can help with indicative travel planning from our knowledge base, but I cannot "
            "complete bookings, payments, handle personal identity documents, guarantee live fares, "
            "or advise on medical/unsafe matters. Please use official channels for those."
        )
        return {**upd, "final_response": text, "status": "refuse"}

    if status == "clarify":
        q = (state.get("planner") or {}).get("clarifying_question") or "Could you share more trip details?"
        return {**upd, "final_response": q, "status": "clarify"}

    bundle = state.get("executor_bundle") or []
    kb = next((b for b in bundle if b.get("chunks")), None)
    transport = next((b for b in bundle if b.get("modes")), None)
    route = next((b for b in bundle if b.get("distance_km")), None)
    budget = next((b for b in bundle if b.get("total_inr") is not None), None)
    itin = next((b for b in bundle if b.get("days_schedule")), None)

    # Build structured data summary (used as LLM context or fallback)
    parts: list[str] = []
    if route:
        parts.append(f"Route: ~{route.get('distance_km')} km [{route.get('source', 'tool:get_route_info')}]")
    if transport and transport.get("modes"):
        parts.append("Transport options (indicative):")
        for m in transport["modes"][:6]:
            parts.append(
                f"  - {m.get('mode')}: ~\u20b9{m.get('cost_inr_typical')} typical, "
                f"{m.get('duration_hrs')} hrs [{m.get('citation', '')}]"
            )
    if budget:
        parts.append(
            f"Budget estimate: ~\u20b9{budget.get('total_inr')} total "
            f"(transport \u20b9{budget.get('transport_inr', 0)}, "
            f"accommodation \u20b9{budget.get('accommodation_inr', 0)}, "
            f"food \u20b9{budget.get('food_inr', 0)}) [{budget.get('source', 'tool:estimate_budget')}]"
        )
    if itin and itin.get("days_schedule"):
        parts.append(f"Itinerary ({itin.get('days')} days, {itin.get('pace')} pace):")
        for day in itin["days_schedule"][:4]:
            parts.append(f"  Day {day.get('day')}: {', '.join(day.get('activities', [])[:3])}")
    if kb and kb.get("chunks"):
        parts.append("Knowledge base:")
        for chunk in kb["chunks"][:3]:
            parts.append(f"  - {chunk.get('title')} [{chunk.get('citation', '')}]: {chunk.get('text', '')[:150]}")

    structured_data = "\n".join(parts) if parts else "No structured data available."
    user_message = state.get("user_message", "")

    # Try LLM for natural language response
    try:
        llm = LLMClient()
        if llm.configured:
            system = (
                "You are JourneyX, a travel planning assistant. "
                "Write a CONCISE, helpful response using the data provided. "
                "Keep total response under 600 words. Use bullet points, not long paragraphs. "
                "For itineraries: list key activities per day in 1-2 lines each. "
                "For transport: use a short comparison table. "
                "End with one line: '⚠️ All estimates are indicative. Verify before booking.'"
            )
            prompt = f"User asked: {user_message}\n\nAvailable data:\n{structured_data}\n\nWrite a concise travel planning response (max 600 words)."
            resp = llm.chat(
                [ChatMessage(role="user", content=prompt)],
                temperature=0.3,
            )
            if resp.content and resp.content != "{}":
                degraded = int(state.get("step_count", 0)) >= 10
                return {**upd, "final_response": resp.content, "status": "degraded" if degraded else "ok"}
    except Exception:
        pass  # Fall through to structured fallback

    # Structured fallback when LLM unavailable
    fallback_parts: list[str] = ["**Indicative plan (verify before booking)**\n"]
    if parts:
        fallback_parts.extend([f"- {p}\n" for p in parts[:6]])
    else:
        fallback_parts.append("- Limited results from the knowledge base; please refine your question.\n")
    fallback_parts.append("\n\u26a0\ufe0f All estimates are indicative. Please verify before booking.")

    degraded = int(state.get("step_count", 0)) >= 10
    final_status = "degraded" if degraded else "ok"
    return {**upd, "final_response": "".join(fallback_parts), "status": final_status}
