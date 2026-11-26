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
    "new delhi": "city_delhi",
    "jaipur": "city_jaipur",
    "goa": "city_goa",
    "manali": "city_manali",
    "kochi": "city_kochi",
    "cochin": "city_kochi",
    "kerala": "city_kochi",  # Kerala → Kochi (nearest major city)
    "trivandrum": "city_kochi",
    "thiruvananthapuram": "city_kochi",
    "bangalore": "city_bangalore",
    "bengaluru": "city_bangalore",
    "mumbai": "city_mumbai",
    "bombay": "city_mumbai",
    "shimla": "city_shimla",
    "rishikesh": "city_rishikesh",
    "haridwar": "city_rishikesh",
    "agra": "city_agra",
    "mysore": "city_mysore",
    "mysuru": "city_mysore",
    "udaipur": "city_udaipur",
    "varanasi": "city_varanasi",
    "banaras": "city_varanasi",
    "kolkata": "city_kolkata",
    "calcutta": "city_kolkata",
    "hyderabad": "city_hyderabad",
    "chennai": "city_chennai",
    "madras": "city_chennai",
    "pune": "city_pune",
    "ahmedabad": "city_ahmedabad",
    "chandigarh": "city_chandigarh",
    "amritsar": "city_amritsar",
}

# Human-readable list of supported destinations for user-facing messages
SUPPORTED_CITIES_DISPLAY = (
    "Delhi, Jaipur, Goa, Manali, Kochi, Bengaluru, Mumbai, "
    "Shimla, Rishikesh, Agra, Mysore, Udaipur, Varanasi"
)

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

# Rich descriptions for known POIs — used in fallback itinerary display
POI_DESCRIPTIONS: dict[str, str] = {
    "poi_jaipur_amber": "Magnificent 16th-century hilltop fort with Rajput architecture, mirror-work interiors, and panoramic views of Maota Lake.",
    "poi_jaipur_hawa": "Iconic 'Palace of Winds' — 5-storey pink sandstone facade with 953 windows, built for royal ladies to observe street life.",
    "poi_jaipur_citypalace": "Grand royal complex blending Mughal and Rajput styles; museums house royal artifacts, textiles, and weapons.",
    "poi_jaipur_jantar": "UNESCO World Heritage astronomical observatory (1734) with 19 giant instruments for measuring time and celestial positions.",
    "poi_goa_baga": "Popular north Goa beach known for water sports, beach shacks, and vibrant nightlife.",
    "poi_goa_old": "UNESCO-listed 16th-century Portuguese churches including Basilica of Bom Jesus, housing St. Francis Xavier's relics.",
    "poi_goa_dudhsagar": "Spectacular 4-tiered waterfall on the Goa-Karnataka border; best visited October–May.",
    "poi_manali_solang": "High-altitude valley offering skiing in winter and paragliding, zorbing, and cable car rides in summer.",
    "poi_manali_hadimba": "Ancient wooden temple dedicated to Hadimba Devi, set in a cedar forest; unique pagoda-style architecture.",
    "poi_kochi_fort": "Colonial-era heritage district with Dutch, Portuguese, and British architecture, Chinese fishing nets, and art galleries.",
    "poi_kochi_backwater": "Scenic houseboat cruise through Kerala's tranquil backwater canals, paddy fields, and coconut groves.",
    "poi_delhi_qutub": "UNESCO-listed 73m minaret (1193), surrounded by India's oldest mosque and the famous Iron Pillar.",
    "poi_delhi_redfort": "Massive 17th-century Mughal fort and UNESCO site — symbolic heart of India, venue for Independence Day.",
    "poi_agra_taj": "UNESCO World Heritage ivory-white marble mausoleum — one of the world's most iconic monuments, built 1632–1653.",
    "poi_agra_fort": "UNESCO-listed red sandstone Mughal fort with palaces, mosques, and audience halls used by Akbar and Shah Jahan.",
    "poi_rishikesh_rafting": "White-water rafting on the Ganges through rapids like Roller Coaster and Golf Course — best September to June.",
    "poi_rishikesh_laxman": "Iconic suspension bridge over the Ganges, surrounded by ashrams, yoga centres, and riverside cafes.",
    "poi_shimla_mall": "Colonial-era pedestrian promenade lined with Victorian buildings, shops, cafes, and the historic Christ Church.",
    "poi_shimla_kufri": "Hill resort 16 km from Shimla offering skiing, tobogganing, and Himalayan views at 2,622m altitude.",
    "poi_mumbai_gateway": "Iconic 26m basalt arch (1924) on the Apollo Bunder waterfront — Mumbai's most recognisable landmark.",
    "poi_mumbai_marine": "3.6 km crescent-shaped promenade along the Arabian Sea — best at sunset for the 'Queen's Necklace' night view.",
    "poi_bangalore_lalbagh": "240-acre botanical garden with a 19th-century glass house, 1,000+ plant species, and a 3,000-million-year-old rock.",
}

# Category emoji map for itinerary display
POI_CATEGORY_EMOJI: dict[str, str] = {
    "fort": "🏰", "landmark": "🏛️", "museum": "🏛️", "heritage": "🏺",
    "beach": "🏖️", "nature": "🌿", "adventure": "🧗", "temple": "⛩️",
    "cruise": "⛵", "leisure": "🚶", "default": "📍",
}

# Day summary templates — filled in by _day_summary()
_DAY_TEMPLATES: dict[int | str, str] = {
    1: (
        "Begin your **{dest}** adventure with a focus on {theme}. "
        "Start early at **{first_poi}** to beat the crowds and enjoy the morning light. "
        "{second_poi_text}"
        "This day introduces you to {dest}'s most iconic landmarks — "
        "comfortable walking shoes and sun protection are recommended."
    ),
    2: (
        "Dive deeper into **{dest}'s** {theme} on day two. "
        "Today's {pace} pace takes you through {poi_list}. "
        "A great day for photography and soaking in the local atmosphere. "
        "Consider a local lunch break between visits to recharge and explore nearby street food."
    ),
    3: (
        "A more relaxed day to explore **{dest}** at your own pace or revisit favourite spots. "
        "{poi_text}"
        "Consider exploring local markets, trying street food, or simply enjoying the city's "
        "ambiance before your journey home."
    ),
    "default": (
        "Extended exploration day — perfect for discovering hidden gems in **{dest}**. "
        "{poi_text}"
        "A great opportunity to interact with locals and experience authentic culture. "
        "Check with your accommodation for recommended local experiences not in the standard itinerary."
    ),
}


# Destination-aware follow-up suggestion templates
# Only include questions that the RAG system can answer well from the KB corpus.
# Avoid: accommodation-specific, food-specific, or live-data questions.
_FOLLOWUP_TEMPLATES: dict[str, list[str]] = {
    "full_plan": [
        "What is the best time of year to visit {dest}?",
        "What are the top attractions in {dest}?",
        "What are the must-see heritage sites in {dest}?",
    ],
    "compare_transport": [
        "Plan a {days}-day trip to {dest} from {origin}",
        "What are the top attractions in {dest}?",
        "What is the best time to visit {dest}?",
    ],
    "rag_qa": [
        "Plan a 3-day trip to {dest}",
        "What are the top attractions in {dest}?",
        "What is the best time to visit {dest}?",
    ],
    "refine": [
        "What is the best time to visit {dest}?",
        "What are the top attractions in {dest}?",
        "What are the must-see heritage sites in {dest}?",
    ],
    "default": [
        "Plan a 3-day trip to {dest}",
        "What are the top attractions in {dest}?",
        "What is the best time to visit {dest}?",
    ],
}


def _static_followup_suggestions(intent: str, trip_slots: dict) -> list[str]:
    """Generate destination-aware follow-up suggestions without LLM."""
    dest = (trip_slots.get("dest_city_id") or "").replace("city_", "").title() or "your destination"
    origin = (trip_slots.get("origin_city_id") or "").replace("city_", "").title() or dest
    days = trip_slots.get("days") or 3
    month = trip_slots.get("month") or "October"

    templates = _FOLLOWUP_TEMPLATES.get(intent, _FOLLOWUP_TEMPLATES["default"])
    return [
        t.format(dest=dest, origin=origin, days=days, month=month)
        for t in templates
    ]


def _day_summary(day_num: int, dest: str, stops: list[dict], pace: str, poi_lookup: dict) -> str:
    """Generate a 3-4 line contextual summary for a day in the itinerary."""
    names = [s.get("name", "") for s in stops if s.get("name")]
    categories = [poi_lookup.get(s.get("poi_id", ""), {}).get("category", "") for s in stops]
    cat_set = {c for c in categories if c}

    if "fort" in cat_set or "heritage" in cat_set or "museum" in cat_set:
        theme = "heritage and royal history"
    elif "beach" in cat_set or "nature" in cat_set:
        theme = "natural beauty and outdoor experiences"
    elif "adventure" in cat_set:
        theme = "adventure and outdoor activities"
    elif "temple" in cat_set:
        theme = "spiritual and cultural heritage"
    elif "landmark" in cat_set:
        theme = "iconic landmarks and city culture"
    else:
        theme = "culture and sightseeing"

    first_poi = names[0] if names else "the main attractions"
    second_poi_text = f"Then head to **{names[1]}** in the afternoon. " if len(names) > 1 else ""
    poi_list = " and ".join(f"**{n}**" for n in names) if names else "the day's attractions"
    poi_text = f"Today features {poi_list}. " if names else ""

    key: int | str = day_num if day_num in _DAY_TEMPLATES else "default"
    return _DAY_TEMPLATES[key].format(
        dest=dest,
        theme=theme,
        first_poi=first_poi,
        second_poi_text=second_poi_text,
        poi_list=poi_list,
        poi_text=poi_text,
        pace=pace or "moderate",
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

    # Origin city response: user replied with just a city name after being asked "where from?"
    # e.g., previous: "plan 4 days to manali" → clarify → user: "from delhi" or "delhi"
    if prefix:
        parsed_current = _parse_slots(text)
        # When only one city is mentioned with "from X", _parse_slots sets both origin AND dest
        # to the same city. Treat this as an origin-only response.
        has_only_origin = (
            parsed_current.get("origin_city_id")
            and len(text.split()) <= 5  # short reply like "from delhi" or "delhi"
            and (
                not parsed_current.get("dest_city_id")
                or parsed_current.get("dest_city_id") == parsed_current.get("origin_city_id")
            )
        )
        if has_only_origin:
            # Look for a previous trip plan destination in conversation history
            base_text = " ".join(t.get("content", "") for t in prefix if t.get("role") == "user")
            base = _parse_slots(base_text)
            if base.get("dest_city_id"):
                # Merge: destination from history + origin from current reply
                merged = {**base, "origin_city_id": parsed_current["origin_city_id"]}
                slots = _slots_model(merged)
                tasks = [
                    TaskPlanItem(task="get_route_info", rationale="route distance and context"),
                    TaskPlanItem(task="compare_transport", rationale="transport options for the route"),
                    TaskPlanItem(task="search_travel_kb", rationale="destination facts and highlights"),
                    TaskPlanItem(task="list_pois", rationale="sightseeing attractions"),
                    TaskPlanItem(task="assemble_itinerary", rationale="day-wise plan"),
                    TaskPlanItem(task="find_accommodations", rationale="stay options"),
                    TaskPlanItem(task="estimate_budget", rationale="indicative total budget"),
                ]
                return PlannerOutput(intent="full_plan", slots=slots, tasks=tasks, confidence=0.85)

    # Clarify when no destination can be resolved from the message.
    if not _has_location(text):
        return _clarify_output(
            "Could you share the destination city (and ideally origin, dates, and budget) so I can plan?"
        )

    parsed = _parse_slots(text)
    slots = _slots_model(parsed)

    # Reject queries about destinations not in our knowledge base
    if not parsed.get("dest_city_id"):
        if _COUNTRY_WORDS.search(text):
            return _clarify_output(
                f"JourneyX v1 covers Indian destinations only. "
                f"Supported cities: {SUPPORTED_CITIES_DISPLAY}. "
                f"Which of these would you like to plan?"
            )
        # Location preposition matched (e.g. 'in Pune', 'to Chennai') but no known city
        if _LOCATION_PREPOSITIONS.search(text) and not any(
            re.search(rf"\b{name}\b", text) for name in CITY_NAME_TO_ID
        ):
            return _clarify_output(
                f"That destination isn't in our knowledge base yet. "
                f"Supported cities: {SUPPORTED_CITIES_DISPLAY}. "
                f"Which of these would you like to plan?"
            )

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
            TaskPlanItem(task="get_route_info", rationale="route distance and context"),
            TaskPlanItem(task="compare_transport", rationale="transport options for the route"),
            TaskPlanItem(task="search_travel_kb", rationale="destination facts and highlights"),
            TaskPlanItem(task="list_pois", rationale="sightseeing attractions"),
            TaskPlanItem(task="assemble_itinerary", rationale="day-wise plan"),
            TaskPlanItem(task="find_accommodations", rationale="stay options"),
            TaskPlanItem(task="estimate_budget", rationale="indicative total budget"),
        ]
    else:
        intent = "rag_qa"
        tasks = [TaskPlanItem(task="search_travel_kb", rationale="answer from KB")]

    # If full_plan but no supported destination resolved, ask for clarification
    if intent == "full_plan" and not slots.dest_id:
        return _clarify_output(
            f"I couldn't identify a supported destination in your request. "
            f"Supported cities: {SUPPORTED_CITIES_DISPLAY}. "
            f"Which would you like to plan?"
        )

    # If full_plan but no origin city provided, ask for it
    if intent == "full_plan" and slots.dest_id and not slots.origin_city_id:
        dest_name = (slots.dest_city_id or slots.dest_id or "").replace("dest_", "").replace("city_", "").title()
        return _clarify_output(
            f"Where will you be travelling from? "
            f"Please share your departure city so I can include transport options and route details for your {dest_name} trip."
        )

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
    stays = next((b for b in bundle if b.get("stays")), None)
    pois_data = next((b for b in bundle if b.get("pois")), None)
    # Build POI lookup: poi_id → {category, fee, duration}
    poi_lookup: dict[str, dict] = {}
    if pois_data and pois_data.get("pois"):
        for p in pois_data["pois"]:
            poi_lookup[p["poi_id"]] = p

    # Build structured data summary (used as LLM context or fallback)
    parts: list[str] = []
    if route:
        parts.append(f"Route: ~{route.get('distance_km')} km [{route.get('source', 'tool:get_route_info')}]")
    if transport and transport.get("modes"):
        parts.append("Transport options — USE THESE EXACT VALUES:")
        parts.append("Mode | Duration (hrs) | Cost ₹ min | Cost ₹ typical | Cost ₹ max | Notes")
        for m in transport["modes"][:6]:
            parts.append(
                f"{m.get('mode','').title()} | {m.get('duration_hrs')} hrs | "
                f"₹{m.get('cost_inr_min')} | ₹{m.get('cost_inr_typical')} | "
                f"₹{m.get('cost_inr_max')} | {m.get('notes','')}"
            )
    if budget:
        total = budget.get("total_inr", 0)
        line_items = budget.get("line_items", [])
        breakdown = ", ".join(
            f"{item['label']} \u20b9{item['inr']}"
            for item in line_items
            if item.get("inr", 0) > 0
        )
        parts.append(
            f"Budget estimate: ~\u20b9{total} total "
            f"({breakdown or 'see line items'}) [{budget.get('source', 'tool:estimate_budget')}]"
        )
    if pois_data and pois_data.get("pois"):
        parts.append("Attractions/POIs — USE THESE EXACT ENTRY FEES (₹0 means FREE):")
        for p in pois_data["pois"][:10]:
            fee = p.get("fee_band_inr", 0)
            fee_str = "FREE" if fee == 0 else f"₹{fee}"
            parts.append(
                f"  - {p.get('name')} | {p.get('category','').title()} | "
                f"Duration: {p.get('typical_duration_hrs')} hrs | Entry: {fee_str}"
            )
    if itin and itin.get("days_schedule"):
        parts.append(f"Itinerary ({itin.get('days')} days, {itin.get('pace')} pace):")
        for day in itin["days_schedule"][:4]:
            stops = day.get("stops", [])
            activity_names = [s.get("name", "") for s in stops if s.get("name")]
            day_text = ", ".join(activity_names[:3]) if activity_names else "Free day / travel"
            parts.append(f"  Day {day.get('day')}: {day_text}")
    if stays and stays.get("stays"):
        parts.append("Accommodation options — USE THESE EXACT NAMES AND PRICES:")
        for s in stays["stays"][:4]:
            price_min = s.get("price_min_inr", s.get("price_per_night_inr", 0))
            price_max = s.get("price_max_inr", s.get("price_per_night_inr", 0))
            parts.append(
                f"  - {s.get('name')} | {s.get('tier','').title()} | "
                f"₹{price_min:,}–₹{price_max:,}/night | {s.get('area', '')}"
            )
    if kb and kb.get("chunks"):
        parts.append("Knowledge base context (background info only, do NOT cite):")
        for chunk in kb["chunks"][:3]:
            parts.append(f"  - {chunk.get('excerpt', '')[:200]}")

    structured_data = "\n".join(parts) if parts else "No structured data available."
    user_message = state.get("user_message", "")

    # NOTE: LLM call in composer is disabled for full_plan/refine to prevent hallucination.
    # For rag_qa queries, we extract answers directly from KB chunks (no LLM needed).
    followup_suggestions: list[str] = []

    # ── Resolve trip slots and intent early (needed by both RAG Q&A and full_plan) ──
    trip_slots = state.get("trip_slots") or {}
    planner_intent = (state.get("planner") or {}).get("intent", "")
    dest_city = (trip_slots.get("dest_city_id") or "").replace("city_", "").title()
    origin_city = (trip_slots.get("origin_city_id") or "").replace("city_", "").title()
    days_count = trip_slots.get("days") or (itin.get("days") if itin else None)
    party = trip_slots.get("party_size") or 1

    # ── RAG Q&A: extract answer directly from KB chunks ──────────────────────
    if planner_intent == "rag_qa" and kb and kb.get("chunks"):
        qa_sections: list[str] = []
        # Build a header from the user question
        question = user_message.strip().rstrip("?").title()
        dest_label = f" {dest_city}" if dest_city else ""
        qa_sections.append(f"## 💡 {question}?")

        # Extract relevant excerpts from KB chunks
        seen_excerpts: set[str] = set()
        excerpt_bullets: list[str] = []

        def _clean_kb_excerpt(raw: str) -> str:
            """Strip internal metadata from a KB excerpt."""
            s = re.sub(r"\[cite:[^\]]*\]", "", raw).strip()
            s = re.sub(r"\[doc:[^\]]*\]", "", s).strip()
            # Strip internal metadata prefix: "Name (poi_id) category=X, typical_duration_hrs=Y. "
            s = re.sub(r"^[^.]+\(poi_\w+\)\s+category=\w+,\s*typical_duration_hrs=[\d.]+\.\s*", "", s).strip()
            # Strip inline POI/city/stay ID references
            s = re.sub(r"\(poi_\w+\)", "", s)
            s = re.sub(r"\bper\s+city_\w+\b", "", s)
            s = re.sub(r"\be\.g\.\s+stay_\w+\b[^;.]*", "", s)
            s = re.sub(r"\bstay_\w+\b", "", s)
            s = re.sub(r"\bcity_\w+\b", "", s)
            s = re.sub(r"\bpoi_\w+\b", "", s)
            # Strip trailing internal metadata phrases
            s = re.sub(r";\s*(numeric fees via poi records|confirm indicative budgets via estimate_budget tool|use tools for indicative prices)[^.]*\.", ".", s).strip()
            s = re.sub(r"\s*—\s*use tools for indicative prices\.?", ".", s).strip()
            # Clean up double spaces and punctuation artifacts
            s = re.sub(r"\s{2,}", " ", s).strip()
            s = re.sub(r"\s+([,;.])", r"\1", s).strip()
            return s

        def _bold_key_facts(text: str) -> str:
            """Bold month ranges, season names, and key travel facts."""
            # Bold month ranges like "October to March", "October–January"
            text = re.sub(
                r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
                r"(\s*[–\-to]+\s*"
                r"(January|February|March|April|May|June|July|August|September|October|November|December))",
                lambda m: f"**{m.group(0)}**", text
            )
            # Bold "Best X to Y" phrases
            text = re.sub(r"\bBest\s+\w+\s+to\s+\w+\b", lambda m: f"**{m.group(0)}**", text)
            # Bold "weather is pleasant/ideal/good"
            text = re.sub(r"\bweather is (pleasant|ideal|good|excellent|perfect)\b", lambda m: f"**{m.group(0)}**", text, flags=re.IGNORECASE)
            # Bold "avoid X" or "peak season"
            text = re.sub(r"\b(peak season|monsoon season|avoid [A-Z][a-z]+)\b", lambda m: f"**{m.group(0)}**", text)
            return text

        # ── Detect question type for targeted filtering ────────────────────
        q_lower = user_message.lower()
        is_best_time_q = any(w in q_lower for w in (
            "best time", "when to visit", "best month", "season", "weather", "time of year", "time to visit"
        ))
        is_attractions_q = any(w in q_lower for w in (
            "attraction", "place", "see", "visit", "top", "must", "heritage", "landmark", "things to do"
        ))

        # ── Re-rank chunks by relevance to the question type ──────────────
        def _chunk_relevance_score(chunk: dict) -> int:
            """Score a chunk's relevance to the question. Higher = more relevant."""
            excerpt = (chunk.get("excerpt", "") + " " + chunk.get("title", "")).lower()
            score = 0
            if is_best_time_q:
                if any(w in excerpt for w in ("best", "month", "october", "november", "december", "january", "february", "march", "april", "season", "weather", "visit", "avoid", "monsoon", "winter", "summer", "pleasant")):
                    score += 10
                if "destination guide" in excerpt:
                    score += 5
                # Heavily penalise POI visitor cards that have no season info
                if "visitor card" in excerpt and not any(w in excerpt for w in ("best", "month", "season", "weather", "october", "november", "december", "january", "february", "march")):
                    score -= 15
            elif is_attractions_q:
                if "visitor card" in excerpt:
                    score += 10
                if any(w in excerpt for w in ("fort", "palace", "temple", "beach", "museum", "monument", "waterfall", "lake")):
                    score += 5
                # Destination guide is useful but secondary for attractions
                if "destination guide" in excerpt:
                    score += 2
            else:
                if "destination guide" in excerpt:
                    score += 3
            return score

        sorted_chunks = sorted(
            kb["chunks"][:8],
            key=_chunk_relevance_score,
            reverse=True,
        )

        # For "best time" questions: only show chunks that actually contain time/season info
        if is_best_time_q:
            time_keywords = {"best", "month", "october", "november", "december", "january", "february", "march", "april", "season", "weather", "monsoon", "winter", "summer", "pleasant", "avoid"}
            sorted_chunks = [
                c for c in sorted_chunks
                if any(w in (c.get("excerpt", "") + c.get("title", "")).lower() for w in time_keywords)
            ] or sorted_chunks[:2]  # fallback to top 2 if nothing matches

        for chunk in sorted_chunks[:4]:
            excerpt = chunk.get("excerpt", "").strip()
            title = chunk.get("title", "").strip()
            if not excerpt:
                continue
            clean_excerpt = _clean_kb_excerpt(excerpt)
            # Skip internal note excerpts entirely
            if re.search(r"dest_\w+\s+museum half-day note|unique doc \d+|fee_band_inr from structured record", clean_excerpt, re.IGNORECASE):
                continue
            # Skip very short excerpts
            if len(clean_excerpt) < 30:
                continue
            if clean_excerpt in seen_excerpts:
                continue
            seen_excerpts.add(clean_excerpt)
            # Clean the title for display
            clean_title = re.sub(r"\[cite:[^\]]*\]", "", title).strip()
            clean_title = re.sub(r"\[doc:[^\]]*\]", "", clean_title).strip()
            # Strip title repetition from beginning of excerpt (e.g. "Kochi destination guide\nKochi / Kerala...")
            if clean_title and clean_excerpt.startswith(clean_title):
                clean_excerpt = clean_excerpt[len(clean_title):].lstrip("\n :—-").strip()
            # Bold key facts in the excerpt
            formatted_excerpt = _bold_key_facts(clean_excerpt)
            # Merge adjacent bold markers: "**X** **Y**" → "**X Y**"
            formatted_excerpt = re.sub(r"\*\*\s*\*\*", " ", formatted_excerpt)
            # Format as a labeled bullet point with bold source label
            if clean_title and len(clean_title) >= 5 and not re.match(r"^(dest_|doc_|poi_|stay_|city_|chunk_|note_|#\d+)", clean_title, re.IGNORECASE):
                excerpt_bullets.append(f"- **{clean_title}**: {formatted_excerpt}")
            else:
                excerpt_bullets.append(f"- {formatted_excerpt}")

        if excerpt_bullets:
            qa_sections.append("### 📌 From our knowledge base:\n\n" + "\n\n".join(excerpt_bullets))

        # Add KB sources
        src_lines = []
        seen_titles: set[str] = set()
        _INTERNAL_PATTERNS_QA = re.compile(
            r"^(dest_|doc_|poi_|stay_|city_|chunk_|note_|#\d+|.*#\d+$)",
            re.IGNORECASE,
        )
        for chunk in kb["chunks"][:5]:
            raw_title = chunk.get("title", "")
            clean_title = re.sub(r"\[cite:[^\]]*\]", "", raw_title).strip()
            clean_title = re.sub(r"\[doc:[^\]]*\]", "", clean_title).strip()
            if not clean_title or clean_title in seen_titles:
                continue
            if _INTERNAL_PATTERNS_QA.match(clean_title):
                continue
            if len(clean_title) < 5 or clean_title.replace("_", "").replace("-", "").isalnum():
                continue
            seen_titles.add(clean_title)
            src_lines.append(f"- 📖 {clean_title}")
        _TOURISM_LINKS_QA: dict[str, str] = {
            "jaipur": "https://www.rajasthantourism.gov.in/",
            "delhi": "https://www.delhitourism.gov.in/",
            "goa": "https://www.goatourism.gov.in/",
            "manali": "https://www.hptdc.in/",
            "kochi": "https://www.keralatourism.org/",
            "bangalore": "https://www.karnatakatourism.org/",
            "bengaluru": "https://www.karnatakatourism.org/",
            "mumbai": "https://www.maharashtratourism.gov.in/",
            "shimla": "https://www.hptdc.in/",
            "rishikesh": "https://uttarakhandtourism.gov.in/",
            "agra": "https://www.uptourism.gov.in/",
            "mysore": "https://www.karnatakatourism.org/",
            "udaipur": "https://www.rajasthantourism.gov.in/",
            "varanasi": "https://www.uptourism.gov.in/",
        }
        dest_key = dest_city.lower() if dest_city else ""
        tourism_url = _TOURISM_LINKS_QA.get(dest_key)
        if tourism_url:
            src_lines.append(f"- 🔗 [Official{dest_label} Tourism]({tourism_url})")
        if src_lines:
            qa_sections.append("### 📚 Sources\n\n" + "\n".join(src_lines))

        qa_sections.append("---\n⚠️ *All estimates are indicative only. Verify with official sources before booking.*")
        final_response = "\n\n".join(qa_sections)
        static_suggestions = _static_followup_suggestions(planner_intent, trip_slots)
        return {**upd, "final_response": final_response, "followup_suggestions": static_suggestions, "status": "ok"}

    # Structured fallback when LLM unavailable — build a readable markdown response
    # Use \n\n between sections for proper markdown paragraph breaks
    sections: list[str] = []

    # Build a clear header from trip slots — only for full_plan / refine intents
    if dest_city and planner_intent in ("full_plan", "refine") and days_count:
        header_parts = [f"## 🗺️ {days_count}-Day {dest_city} Trip Plan"]
        if origin_city:
            header_parts.append(f"**From:** {origin_city} → {dest_city}")
        header_parts.append(f"**Party size:** {party} person{'s' if party > 1 else ''}")
        sections.append("\n\n".join(header_parts))

    if route:
        origin = route.get("origin_city_id", "").replace("city_", "").title()
        dest_name = route.get("dest_city_id", "").replace("city_", "").title()
        sections.append(f"### 🗺️ Route\n\n- {origin} → {dest_name}: ~{route.get('distance_km')} km")

    if transport and transport.get("modes"):
        rows = ["| Mode | Duration (hrs) | Cost ₹ (indicative) |",
                "|------|---------------|---------------------|"]
        for m in transport["modes"][:5]:
            rows.append(f"| {m.get('mode','').title()} | {m.get('duration_hrs')} | ₹{m.get('cost_inr_typical')} |")
        sections.append("### 🚌 Transport Options (indicative)\n\n" + "\n".join(rows))

    if itin and itin.get("days_schedule"):
        day_sections = []
        for day in itin["days_schedule"]:
            stops = day.get("stops", [])
            hours_planned = day.get("hours_planned", 0)
            day_header = f"**Day {day.get('day')}**" + (f" *(~{hours_planned} hrs planned)*" if hours_planned > 0 else "")
            stop_lines = []
            for stop in stops:
                poi_id = stop.get("poi_id", "")
                name = stop.get("name", "")
                hours = stop.get("hours", "")
                poi_info = poi_lookup.get(poi_id, {})
                category = poi_info.get("category", "")
                fee = poi_info.get("fee_band_inr", "")
                desc = POI_DESCRIPTIONS.get(poi_id, "")
                emoji = POI_CATEGORY_EMOJI.get(category, POI_CATEGORY_EMOJI["default"])
                meta_parts = []
                if category:
                    meta_parts.append(category.title())
                if hours:
                    meta_parts.append(f"{hours} hrs")
                if fee:
                    meta_parts.append(f"Entry: ~\u20b9{fee}")
                meta_str = " | ".join(meta_parts)
                line = f"- {emoji} **{name}**"
                if meta_str:
                    line += f" — *{meta_str}*"
                if desc:
                    line += f"\n  > {desc}"
                stop_lines.append(line)
            if not stop_lines:
                stop_lines.append("- 🚶 Free day / travel or leisure")
            # Generate contextual day summary using template
            summary = _day_summary(
                day_num=int(day.get("day", 1)),
                dest=dest_city or "the destination",
                stops=stops,
                pace=itin.get("pace", "moderate"),
                poi_lookup=poi_lookup,
            )
            day_sections.append(
                day_header + "\n\n"
                + f"*{summary}*\n\n"
                + "\n\n".join(stop_lines)
            )
        sections.append(
            f"### 📅 Itinerary ({itin.get('days')} days, {itin.get('pace')} pace)\n\n"
            + "\n\n".join(day_sections)
        )

    if budget:
        total = budget.get("total_inr", 0)
        line_items = budget.get("line_items", [])
        rows = ["| Category | Amount ₹ |", "|----------|----------|"]
        for item in line_items:
            if item.get("inr", 0) > 0:
                rows.append(f"| {item['label'].title()} | ₹{item['inr']:,} |")
        rows.append(f"| **Total** | **₹{total:,}** |")
        sections.append("### 💰 Budget Estimate (indicative)\n\n" + "\n".join(rows))

    if stays and stays.get("stays"):
        stay_cards = []
        for s in stays["stays"][:4]:
            name = s.get("name", "")
            tier = s.get("tier", "").title()
            price = s.get("price_per_night_inr", 0)
            price_min = s.get("price_min_inr")
            price_max = s.get("price_max_inr")
            area = s.get("area", "")
            desc = s.get("description", "")
            url = s.get("booking_url", "")

            # Price range display
            if price_min and price_max:
                price_str = f"₹{price_min:,} – ₹{price_max:,}/night"
            else:
                price_str = f"₹{price:,}/night"

            tier_emoji = {"luxury": "⭐⭐⭐⭐⭐", "premium": "⭐⭐⭐⭐", "mid": "⭐⭐⭐", "budget": "⭐⭐"}.get(s.get("tier", ""), "⭐⭐⭐")
            card = f"**{name}** {tier_emoji}\n*{tier} · {area} · {price_str}*"
            if desc:
                card += f"\n{desc}"
            if url:
                card += f"\n🔗 [View & Book]({url})"
            stay_cards.append(card)

        if stay_cards:
            sections.append("### 🏨 Accommodation Options (indicative)\n\n" + "\n\n---\n\n".join(stay_cards))

    if kb and kb.get("chunks"):
        src_lines = []
        seen_titles: set[str] = set()
        # Internal doc ID patterns to skip
        _INTERNAL_PATTERNS = re.compile(
            r"^(dest_|doc_|poi_|stay_|city_|chunk_|note_|#\d+|.*#\d+$)",
            re.IGNORECASE,
        )
        for chunk in kb["chunks"][:5]:
            raw_title = chunk.get("title", "")
            # Strip citation patterns
            clean_title = re.sub(r"\[cite:[^\]]*\]", "", raw_title).strip()
            clean_title = re.sub(r"\[doc:[^\]]*\]", "", clean_title).strip()
            # Skip empty, duplicate, or internal doc IDs
            if not clean_title:
                continue
            if clean_title in seen_titles:
                continue
            if _INTERNAL_PATTERNS.match(clean_title):
                continue
            # Only show human-readable titles (contain spaces or capital letters)
            if len(clean_title) < 5 or clean_title.replace("_", "").replace("-", "").isalnum():
                continue
            seen_titles.add(clean_title)
            src_lines.append(f"- 📖 {clean_title}")
        # Add destination-specific tourism link (not from KB reference_links which may be wrong)
        _TOURISM_LINKS: dict[str, str] = {
            "jaipur": "https://www.rajasthantourism.gov.in/",
            "delhi": "https://www.delhitourism.gov.in/",
            "goa": "https://www.goatourism.gov.in/",
            "manali": "https://www.hptdc.in/",
            "kochi": "https://www.keralatourism.org/",
            "bangalore": "https://www.karnatakatourism.org/",
            "bengaluru": "https://www.karnatakatourism.org/",
            "mumbai": "https://www.maharashtratourism.gov.in/",
            "shimla": "https://www.hptdc.in/",
            "rishikesh": "https://uttarakhandtourism.gov.in/",
            "agra": "https://www.uptourism.gov.in/",
            "mysore": "https://www.karnatakatourism.org/",
            "udaipur": "https://www.rajasthantourism.gov.in/",
            "varanasi": "https://www.uptourism.gov.in/",
        }
        dest_key = dest_city.lower() if dest_city else ""
        tourism_url = _TOURISM_LINKS.get(dest_key)
        if tourism_url:
            src_lines.append(f"- 🔗 [Official {dest_city} Tourism]({tourism_url})")
        if src_lines:
            sections.append("### 📚 Knowledge Base Sources\n\n" + "\n".join(src_lines))

    if not sections:
        sections.append(
            "Limited results from the knowledge base. Please specify a destination from: "
            "Delhi, Jaipur, Goa, Manali, Kochi, Bengaluru, Mumbai, Shimla, Rishikesh, Agra."
        )

    sections.append("---\n⚠️ *All estimates are indicative only. Verify with official sources before booking.*")
    final_response = "\n\n".join(sections)

    # Generate destination-aware follow-up suggestions (no LLM needed)
    static_suggestions = _static_followup_suggestions(planner_intent, trip_slots)

    degraded = int(state.get("step_count", 0)) >= 10
    final_status = "degraded" if degraded else "ok"
    return {**upd, "final_response": final_response, "followup_suggestions": static_suggestions, "status": final_status}
