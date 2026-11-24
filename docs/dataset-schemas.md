# Dataset schemas (Foundation

Canonical Pydantic models live in `packages/journeyx/core/structured.py` and `eval_item.py`.

## ER overview

```text
city 1---N destination_profile
destination_profile 1---N poi
destination_profile 1---N accommodation
city (origin) + city (dest) -> route 1---N transport_option
travel_document -> dest_id (optional links: linked_poi_id)
```

## Structured tables (`data/structured/*.jsonl`)

| File | Model |
|------|--------|
| `cities.jsonl` | `City` |
| `destination_profile.jsonl` | `DestinationProfile` |
| `pois.jsonl` | `Poi` |
| `accommodations.jsonl` | `Accommodation` |
| `routes.jsonl` | `Route` |
| `transport_option.jsonl` | `TransportOption` |
| `price_assumption.jsonl` | `PriceAssumption` |
| `faq_map.jsonl` | FAQ paraphrase → `target_doc_id` |

Eval: `conversation_prefix` on `refine` items (`ConversationTurn`). Freeze record: `data/eval/EVAL_FROZEN.md`.
Retrieval labels: `data/eval/retrieval_labels_v1.jsonl`.

## Document corpus (`data/documents/documents.jsonl`)

| Field | Notes |
|-------|--------|
| `doc_id` | Stable citation ID |
| `doc_type` | guide, poi_card, faq, activity, … |
| `body` | Narrative; numeric prices only via linked IDs |

## Single source of truth

- **Numbers** → structured tables (tools).
- **Prose** → documents (RAG).

## Hold-out destinations (eval generalization)

`city_mysore`, `city_udaipur`, `city_varanasi` — minimal stub docs; not for RAG chunk tuning.

## Manifest

See `data/manifest.yaml` for `corpus_version`, counts, and hold-out list.