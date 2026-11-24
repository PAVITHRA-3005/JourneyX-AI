from __future__ import annotations

import math
from typing import Any

from journeyx.core.structured import TransportMode
from journeyx.tools.loaders import find_route, load_routes, load_transport_options


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _city_coords() -> dict[str, tuple[float, float]]:
    from journeyx.tools.loaders import _load_jsonl, _root

    rows = _load_jsonl(_root() / "data/structured/cities.jsonl")
    return {r["city_id"]: (r["lat"], r["lon"]) for r in rows}


def get_route_info(origin_city_id: str, dest_city_id: str) -> dict[str, Any]:
    route = find_route(origin_city_id, dest_city_id)
    if route:
        return {
            "origin_city_id": origin_city_id,
            "dest_city_id": dest_city_id,
            "route_id": route.route_id,
            "distance_km": route.distance_km,
            "confidence": "high",
            "disclaimer": "Indicative route from curated KB; not GPS.",
            "source": f"tool:get_route_info:{route.route_id}",
        }

    coords = _city_coords()
    if origin_city_id in coords and dest_city_id in coords:
        lat1, lon1 = coords[origin_city_id]
        lat2, lon2 = coords[dest_city_id]
        dist = _haversine_km(lat1, lon1, lat2, lon2)
        return {
            "origin_city_id": origin_city_id,
            "dest_city_id": dest_city_id,
            "route_id": None,
            "distance_km": round(dist, 1),
            "confidence": "low",
            "disclaimer": "Haversine estimate only; road distance may differ.",
            "source": "tool:get_route_info:haversine",
        }

    return {
        "error": "route_not_found",
        "origin_city_id": origin_city_id,
        "dest_city_id": dest_city_id,
    }


def compare_transport(
    origin_city_id: str,
    dest_city_id: str,
    party_size: int = 1,
) -> dict[str, Any]:
    route = find_route(origin_city_id, dest_city_id)
    if not route:
        info = get_route_info(origin_city_id, dest_city_id)
        if info.get("error"):
            return info
        route_id = None
    else:
        route_id = route.route_id

    options = load_transport_options()
    rows = [o for o in options if o.route_id == route_id] if route_id else []

    if not rows and route_id is None:
        return {
            "error": "no_transport_data",
            "message": "Pair not in KB; expand routes table.",
            "route": get_route_info(origin_city_id, dest_city_id),
        }

    table = []
    for opt in rows:
        mode = opt.mode.value if isinstance(opt.mode, TransportMode) else str(opt.mode)
        typical = opt.cost_inr_typical
        if mode in ("flight", "train", "bus"):
            typical *= max(party_size, 1)
        table.append(
            {
                "mode": mode,
                "duration_hrs": opt.duration_hrs,
                "cost_inr_typical": typical,
                "cost_inr_min": opt.cost_inr_min,
                "cost_inr_max": opt.cost_inr_max,
                "notes": opt.notes,
                "opt_id": opt.opt_id,
                "citation": f"tool:compare_transport:{opt.opt_id}",
            }
        )

    return {
        "origin_city_id": origin_city_id,
        "dest_city_id": dest_city_id,
        "party_size": party_size,
        "route_id": route_id,
        "modes": table,
        "disclaimer": "All fares indicative from KB; not live prices.",
        "source": "tool:compare_transport",
    }


def list_routes_count() -> int:
    return len(load_routes())