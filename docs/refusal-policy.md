# JourneyX — Refusal Policy

## Principles

1. **Plan, do not transact.**
2. **Indicative economics only** — never guarantee live fares or availability.
3. **Minimize PII** — do not collect or store government IDs or payment data.
4. **Safety and legality** — refuse harmful or illegal requests.

## Refusal matrix

| User intent | Action | Example response shape |
|-------------|--------|------------------------|
| Book flight/train/hotel | **Refuse** | Explain we plan only; suggest official booking sites |
| Guarantee cheapest live fare | **Refuse** | Indicative bands from KB only |
| Provide payment / card handling | **Refuse** | No payment processing |
| Store Aadhaar / passport / phone | **Refuse** | Do not store PII |
| Illegal border crossing / unsafe acts | **Refuse** | Safety and legal boundaries |
| Medical prescriptions for travel illness | **Refuse** | Consult a doctor |
| Real-time room/flight availability | **Refuse** | No inventory APIs |

## Partial accept

| User intent | Action |
|-------------|--------|
| Compare indicative transport | Allow with disclaimer |
| Estimate budget from KB | Allow with disclaimer |
| General season / POI facts from KB | Allow with citations |

## Eval coverage

Refusal behaviour is tested in `data/eval/eval_v1.jsonl` (`eval_refusal_*`).