from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TransportMode(str, Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    ROAD_PETROL = "road_petrol"
    ROAD_DIESEL = "road_diesel"
    ROAD_EV = "road_ev"


class City(BaseModel):
    city_id: str
    name: str
    state: str
    lat: float
    lon: float
    airport_code: str | None = None
    best_months: list[str] = Field(default_factory=list)


class DestinationProfile(BaseModel):
    dest_id: str
    city_id: str
    tags: list[str]
    budget_tier: Literal["budget", "mid", "premium"]
    summary_doc_id: str


class Poi(BaseModel):
    poi_id: str
    dest_id: str
    name: str
    category: str
    typical_duration_hrs: float
    fee_band_inr: int = 0


class Accommodation(BaseModel):
    stay_id: str
    dest_id: str
    name: str
    tier: Literal["budget", "mid", "premium", "luxury"]
    price_per_night_inr: int
    area: str
    price_min_inr: int | None = None
    price_max_inr: int | None = None
    booking_url: str | None = None
    description: str | None = None


class Route(BaseModel):
    route_id: str
    origin_city_id: str
    dest_city_id: str
    distance_km: float


class TransportOption(BaseModel):
    opt_id: str
    route_id: str
    mode: TransportMode
    duration_hrs: float
    cost_inr_min: int
    cost_inr_typical: int
    cost_inr_max: int
    notes: str = ""


class PriceAssumption(BaseModel):
    key: str
    value: float
    unit: str
    disclaimer: str


class TravelDocument(BaseModel):
    doc_id: str
    dest_id: str
    doc_type: Literal[
        "destination_guide",
        "activity",
        "accommodation_blurb",
        "transport_guide",
        "itinerary_template",
        "faq",
        "poi_card",
    ]
    title: str
    body: str
    source_attribution: str = "team_curated_v1"
    last_reviewed: str = "2025-11-01"
    linked_poi_id: str | None = None
    linked_stay_id: str | None = None