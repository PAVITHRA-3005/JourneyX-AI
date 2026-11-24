# Tool contracts

Runtime: `packages/journeyx/tools/` + code-first dispatch in `packages/journeyx/tools/registry.py` (Executor). Schemas align with `packages/journeyx/core/planner_output.py`.

## Tools (≥3 for capstone)

### `search_travel_kb`

```json
{
  "query": "string",
  "dest_id": "string|null",
  "doc_types": ["string"],
  "top_k": 5
}
```

Returns: `{ "chunks": [{ "doc_id", "title", "excerpt", "score" }] }`

### `compare_transport`

```json
{
  "origin_city_id": "string",
  "dest_city_id": "string",
  "party_size": 1
}
```

Returns: mode rows from `transport_option` with indicative disclaimer.

### `get_route_info`

```json
{ "origin_city_id": "string", "dest_city_id": "string" }
```

### `find_accommodations`

```json
{
  "dest_id": "string",
  "tier": "budget|mid|premium|null",
  "max_price_per_night_inr": 0
}
```

### `list_pois`

```json
{
  "dest_id": "string",
  "categories": ["string"],
  "max_hours": 0
}
```

### `estimate_budget` (deterministic)

```json
{
  "dest_id": "string",
  "nights": 1,
  "party_size": 1,
  "stay_id": "string|null",
  "transport_opt_id": "string|null",
  "food_tier": "budget|mid"
}
```

### `assemble_itinerary`

```json
{
  "dest_id": "string",
  "days": 1,
  "poi_ids": ["string"],
  "pace": "relaxed|moderate|packed"
}
```

## Orchestration step counting (appendix)

See `IMPLEMENTATION_PLAN.md` §6.4 — each graph node visit increments step count; target happy path ≤6, hard cap 10.

## Planner output schema

`PlannerOutput`: `intent`, `slots` (`TripSlots`), `tasks[]`, optional `clarifying_question`.