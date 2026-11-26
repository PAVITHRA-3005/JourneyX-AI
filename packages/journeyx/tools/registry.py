from __future__ import annotations

from typing import Any, Callable

from journeyx.core.planner_output import TaskPlanItem, TaskType, TripSlots
from journeyx.tools.budget import estimate_budget
from journeyx.tools.discovery import find_accommodations, list_pois, lookup_destinations
from journeyx.tools.itinerary import assemble_itinerary
from journeyx.tools.search_kb import search_travel_kb
from journeyx.tools.transport import compare_transport, get_route_info

ToolFn = Callable[..., dict[str, Any]]


def run_task(task: TaskPlanItem, slots: TripSlots, user_message: str) -> dict[str, Any]:
    """Dispatch planner tasks to tools using trip slots and the user message."""
    name: TaskType = task.task
    handlers: dict[str, ToolFn] = {
        "search_travel_kb": lambda: search_travel_kb(
            user_message,
            dest_id=slots.dest_id,
            top_k=5,
        ),
        "lookup_destinations": lambda: lookup_destinations(query=user_message),
        "compare_transport": lambda: compare_transport(
            slots.origin_city_id or "city_delhi",
            slots.dest_city_id or "city_jaipur",
            slots.party_size or 1,
        ),
        "get_route_info": lambda: get_route_info(
            slots.origin_city_id or "city_delhi",
            slots.dest_city_id or "city_jaipur",
        ),
        "find_accommodations": lambda: find_accommodations(
            slots.dest_id or "dest_jaipur",
            # No tier filter — show all tiers (luxury, mid, budget) for full choice
        ),
        "list_pois": lambda: list_pois(slots.dest_id or "dest_jaipur"),
        "estimate_budget": lambda: estimate_budget(
            slots.dest_id or "dest_jaipur",
            nights=slots.days or 3,
            party_size=slots.party_size or 1,
        ),
        "assemble_itinerary": lambda: assemble_itinerary(
            slots.dest_id or "dest_jaipur",
            days=slots.days or 3,
            pace=slots.pace or "moderate",
        ),
    }
    fn = handlers.get(name)
    if not fn:
        return {"error": "unknown_task", "task": name}
    try:
        result = fn()
        result["_task"] = name
        return result
    except Exception as exc:  # noqa: BLE001
        return {"error": "tool_exception", "task": name, "message": str(exc)}


def tool_catalog() -> list[str]:
    return [
        "search_travel_kb",
        "lookup_destinations",
        "compare_transport",
        "get_route_info",
        "find_accommodations",
        "list_pois",
        "estimate_budget",
        "assemble_itinerary",
    ]