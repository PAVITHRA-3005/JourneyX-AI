from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


IntentType = Literal[
    "discover",
    "rag_qa",
    "compare_transport",
    "full_plan",
    "refine",
    "clarify",
    "unknown",
]

TaskType = Literal[
    "search_travel_kb",
    "lookup_destinations",
    "compare_transport",
    "get_route_info",
    "find_accommodations",
    "list_pois",
    "estimate_budget",
    "assemble_itinerary",
]


class TripSlots(BaseModel):
    origin_city_id: str | None = None
    dest_city_id: str | None = None
    dest_id: str | None = None
    days: int | None = Field(default=None, ge=1, le=30)
    party_size: int | None = Field(default=None, ge=1, le=20)
    budget_inr: int | None = Field(default=None, ge=0)
    preferred_modes: list[str] = Field(default_factory=list)
    pace: Literal["relaxed", "moderate", "packed"] | None = None
    month: str | None = None


class TaskPlanItem(BaseModel):
    task: TaskType
    rationale: str = ""


class PlannerOutput(BaseModel):
    intent: IntentType
    slots: TripSlots
    tasks: list[TaskPlanItem] = Field(default_factory=list)
    clarifying_question: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)