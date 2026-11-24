from __future__ import annotations

from typing import Any, Literal

from journeyx.tools.discovery import list_pois


Pace = Literal["relaxed", "moderate", "packed"]


def assemble_itinerary(
    dest_id: str,
    days: int = 3,
    poi_ids: list[str] | None = None,
    pace: Pace = "moderate",
) -> dict[str, Any]:
    days = max(1, min(days, 14))
    hours_cap = {"relaxed": 4.0, "moderate": 6.0, "packed": 9.0}[pace]

    if poi_ids:
        catalog = {p["poi_id"]: p for p in list_pois(dest_id, limit=50)["pois"]}
        selected = [catalog[pid] for pid in poi_ids if pid in catalog]
    else:
        selected = list_pois(dest_id, limit=days * 2)["pois"]

    schedule: list[dict[str, Any]] = []
    idx = 0
    for day in range(1, days + 1):
        used = 0.0
        stops: list[dict[str, Any]] = []
        while idx < len(selected) and used + selected[idx]["typical_duration_hrs"] <= hours_cap:
            poi = selected[idx]
            stops.append(
                {
                    "poi_id": poi["poi_id"],
                    "name": poi["name"],
                    "hours": poi["typical_duration_hrs"],
                    "citation": poi.get("citation"),
                }
            )
            used += poi["typical_duration_hrs"]
            idx += 1
        schedule.append({"day": day, "stops": stops, "hours_planned": round(used, 1)})

    return {
        "dest_id": dest_id,
        "days": days,
        "pace": pace,
        "days_schedule": schedule,
        "disclaimer": "Template itinerary from KB POIs; verify locally.",
        "source": "tool:assemble_itinerary",
    }