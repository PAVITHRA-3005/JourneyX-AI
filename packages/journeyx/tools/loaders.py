from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from journeyx.core.structured import Route, TransportOption


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


@lru_cache(maxsize=1)
def load_routes() -> list[Route]:
    return [Route.model_validate(r) for r in _load_jsonl(_root() / "data/structured/routes.jsonl")]


@lru_cache(maxsize=1)
def load_transport_options() -> list[TransportOption]:
    return [
        TransportOption.model_validate(r)
        for r in _load_jsonl(_root() / "data/structured/transport_option.jsonl")
    ]


def find_route(origin_city_id: str, dest_city_id: str) -> Route | None:
    for route in load_routes():
        if route.origin_city_id == origin_city_id and route.dest_city_id == dest_city_id:
            return route
    return None