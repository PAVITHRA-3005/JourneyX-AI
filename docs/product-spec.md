# JourneyX AI — Product specification

## Purpose

JourneyX is a conversational **indicative** travel planning copilot for Indian destinations. It helps users discover places, compare transport modes, estimate budgets, and build day-wise outlines using a **team-owned knowledge base** and a hosted ≤8B LLM.

## In scope

- English queries (v1).
- Ten core destinations (thirteen cities in structured data, including hold-outs).
- Destination discovery, RAG Q&A, transport comparison, budget estimate, itinerary skeleton, and multi-turn refine.
- Citations and “indicative only” pricing.

## Out of scope

- Live booking, payment, inventory, or real-time fare guarantees.
- Maps, routing, OTA, or web APIs at runtime.
- Medical, visa, or safety guarantees.
- Storing user PII (Aadhaar, passport numbers, payment cards).

## Correct answer (by category)

| Category | Pass criteria |
|----------|----------------|
| `refusal` | Clear refuse + HITL / indicative boundary; no booking |
| `clarify` | One focused question when slots missing |
| `rag_qa` | Fact aligned with KB; citation or entity ID |
| `transport_compare` | Modes from structured `transport_option`; indicative disclaimer |
| `full_plan` | Slots, budget breakdown, day outline, grounding |
| `refine` | Updates changed field; retains prior context |

## Compliance references

Per `IMPLEMENTATION_PLAN.md` §9.1: product spec, refusal policy, frozen eval, schemas, LLM adapter, baseline, traces, hybrid RAG, and LangGraph agent are versioned in this repository.

## Human-in-the-loop

Any real purchase, visa decision, or safety-critical choice requires human verification off-system. Stated in UI and system prompt.