from __future__ import annotations

from typing import Any, Literal

from journeyx.tools.loaders import load_transport_options
from journeyx.tools.discovery import _accommodations


FoodTier = Literal["budget", "mid"]


def estimate_budget(
    dest_id: str,
    nights: int = 1,
    party_size: int = 1,
    stay_id: str | None = None,
    transport_opt_id: str | None = None,
    food_tier: FoodTier = "mid",
) -> dict[str, Any]:
    nights = max(1, nights)
    party_size = max(1, party_size)

    stay_row = None
    for s in _accommodations():
        if s.dest_id == dest_id and (stay_id is None or s.stay_id == stay_id):
            stay_row = s
            if stay_id:
                break
    nightly = stay_row.price_per_night_inr if stay_row else 2500

    transport_cost = 0
    transport_note = "no transport option selected"
    if transport_opt_id:
        for opt in load_transport_options():
            if opt.opt_id == transport_opt_id:
                transport_cost = opt.cost_inr_typical * party_size
                transport_note = f"{opt.mode.value} typical"
                break

    food_per_day = 600 if food_tier == "budget" else 1200
    food_total = food_per_day * party_size * nights
    stay_total = nightly * nights
    misc = 500 * nights

    line_items = [
        {"label": "stay", "inr": stay_total, "detail": stay_row.stay_id if stay_row else "default_mid"},
        {"label": "transport", "inr": transport_cost, "detail": transport_note},
        {"label": "food", "inr": food_total, "detail": food_tier},
        {"label": "misc", "inr": misc, "detail": "activities buffer"},
    ]
    total = sum(x["inr"] for x in line_items)

    return {
        "dest_id": dest_id,
        "nights": nights,
        "party_size": party_size,
        "line_items": line_items,
        "total_inr": total,
        "assumptions": [
            "Indicative KB prices only; not live booking.",
            f"Stay basis: {nightly} INR/night",
        ],
        "source": "tool:estimate_budget",
    }