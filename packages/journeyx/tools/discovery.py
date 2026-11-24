from __future__ import annotations

from typing import Any

from journeyx.core.structured import Accommodation, DestinationProfile, Poi
from journeyx.tools.loaders import _load_jsonl, _root


def _destinations() -> list[DestinationProfile]:
    from journeyx.core.structured import DestinationProfile

    return [DestinationProfile.model_validate(r) for r in _load_jsonl(_root() / "data/structured/destination_profile.jsonl")]


def _accommodations() -> list[Accommodation]:
    return [Accommodation.model_validate(r) for r in _load_jsonl(_root() / "data/structured/accommodations.jsonl")]


def _pois() -> list[Poi]:
    return [Poi.model_validate(r) for r in _load_jsonl(_root() / "data/structured/pois.jsonl")]


def lookup_destinations(
    query: str | None = None,
    tag: str | None = None,
    budget_tier: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    cities = {c["city_id"]: c for c in _load_jsonl(_root() / "data/structured/cities.jsonl")}
    hits: list[dict[str, Any]] = []
    q = (query or "").lower()
    for dest in _destinations():
        city = cities.get(dest.city_id, {})
        name = str(city.get("name", dest.city_id))
        if tag and tag not in dest.tags:
            continue
        if budget_tier and dest.budget_tier != budget_tier:
            continue
        if q and q not in name.lower() and q not in " ".join(dest.tags).lower():
            continue
        hits.append(
            {
                "dest_id": dest.dest_id,
                "city_id": dest.city_id,
                "name": name,
                "tags": dest.tags,
                "budget_tier": dest.budget_tier,
                "summary_doc_id": dest.summary_doc_id,
            }
        )
        if len(hits) >= limit:
            break
    return {"destinations": hits, "count": len(hits), "source": "tool:lookup_destinations"}


def find_accommodations(
    dest_id: str,
    tier: str | None = None,
    max_price_per_night_inr: int | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    rows = []
    for stay in _accommodations():
        if stay.dest_id != dest_id:
            continue
        if tier and stay.tier != tier:
            continue
        if max_price_per_night_inr is not None and stay.price_per_night_inr > max_price_per_night_inr:
            continue
        rows.append(
            {
                "stay_id": stay.stay_id,
                "name": stay.name,
                "tier": stay.tier,
                "price_per_night_inr": stay.price_per_night_inr,
                "area": stay.area,
                "citation": f"tool:find_accommodations:{stay.stay_id}",
            }
        )
        if len(rows) >= limit:
            break
    return {
        "dest_id": dest_id,
        "stays": rows,
        "disclaimer": "Indicative nightly rates from KB.",
        "source": "tool:find_accommodations",
    }


def list_pois(
    dest_id: str,
    categories: list[str] | None = None,
    max_hours: float | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    rows = []
    cats = {c.lower() for c in (categories or [])}
    for poi in _pois():
        if poi.dest_id != dest_id:
            continue
        if cats and poi.category.lower() not in cats:
            continue
        if max_hours is not None and poi.typical_duration_hrs > max_hours:
            continue
        rows.append(
            {
                "poi_id": poi.poi_id,
                "name": poi.name,
                "category": poi.category,
                "typical_duration_hrs": poi.typical_duration_hrs,
                "fee_band_inr": poi.fee_band_inr,
                "citation": f"tool:list_pois:{poi.poi_id}",
            }
        )
        if len(rows) >= limit:
            break
    return {"dest_id": dest_id, "pois": rows, "source": "tool:list_pois"}