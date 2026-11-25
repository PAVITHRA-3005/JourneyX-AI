# JourneyX AI — Mentor Presentation Summary

> A narrative walkthrough of the project — what we built, why we built it this way, and how to demonstrate it.

---

## Opening: The Problem We Solved

Imagine you want to plan a 4-day trip from Delhi to Jaipur for two people under ₹25,000. You open Google, then MakeMyTrip, then a travel blog, then a budget calculator — and you're still not done. Information is scattered, inconsistent, and you have to manually reconcile transport costs, hotel prices, and itinerary timing.

**JourneyX solves this in one conversation.**

It is an intelligent travel planning copilot that understands your trip requirements, retrieves relevant knowledge from a curated knowledge base, runs deterministic calculations, and delivers a grounded, cited, day-wise plan — all through natural chat.

---

## What We Built

JourneyX is a **Track B capstone project** — meaning we built everything on the API side using a hosted ≤8B language model (Qwen3-8B). No fine-tuning. No frontier models. No external booking or maps APIs.

The system has three layers:

### Layer 1 — The Knowledge Base (Our Data)
We built and own a travel knowledge base covering Indian destinations. It has two parts:
- **Document corpus** — narrative travel guides, destination tips, seasonal advice, POI descriptions
- **Structured tables** — cities, transport options with indicative fares, accommodation tiers, routes, points of interest with durations, budget assumptions

Everything the system says is grounded in this owned data. The model never invents prices or distances.

### Layer 2 — Hybrid RAG (How We Retrieve)
When a user asks a question, we don't just send it to the LLM. We first retrieve relevant knowledge using:
- **BM25** (keyword-based sparse retrieval)
- **FAISS** (dense vector retrieval using embeddings)
- **Cross-encoder reranker** (picks the best 5 chunks from the top 20)

This hybrid approach ensures we get both exact keyword matches and semantic similarity. Every factual claim in the answer carries a `[cite:doc_id]` reference traceable back to the source.

### Layer 3 — Multi-Agent Orchestration (How We Think)
This is the heart of the system. We use **LangGraph** to orchestrate three agents:

1. **Planner** — Understands what the user wants. Extracts intent (full plan, transport comparison, refine, Q&A), fills trip slots (origin, destination, dates, budget, party size), and creates a task list for the Executor. If information is missing, it asks one focused clarifying question.

2. **Executor** — Does the actual work. Runs tools deterministically: compare transport modes, search the knowledge base, list POIs, estimate budget (pure Python math — not LLM arithmetic), assemble a day-wise itinerary. The LLM's role here is minimal — it follows the task list.

3. **Critic** — Quality gate before the user sees anything. Checks that budget totals match the tool output, factual claims have citations, the user's preferences are reflected, and numbers in prose match tool results. On complex plans, an LLM critic pass runs after the rule checks. It either approves, sends back for revision (max 2 loops), or returns a partial answer with a disclaimer.

4. **Composer** — The only node that writes the final user-facing answer. It takes the approved, structured bundle from the Critic and turns it into readable markdown with a day-by-day plan, cost table, and citation list.

---

## The Key Design Decision: Why Three Agents?

The capstone uses a ≤8B model. Small models hallucinate prices, invent distances, and make arithmetic errors. Our architecture compensates for this:

| What could go wrong | How we fixed it |
|---|---|
| LLM invents fares | `compare_transport` reads from structured table — LLM never touches numbers |
| LLM makes budget errors | `estimate_budget` is pure Python math |
| LLM hallucinates facts | Critic checks every claim has a citation |
| LLM goes in circles | Hard cap: ≤10 graph steps, ≤2 revise loops |
| LLM attempts booking | Policy Gate refuses before any LLM call |

The LLM's job is narrow: understand language, plan tasks, and compose readable prose. Everything else is code.

---

## The Full Request Flow (One Query)

Let's trace what happens when a user types:
> *"Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000 by train"*

1. **Streamlit UI** sends the message to **FastAPI** (which assigns a trace ID and applies rate limiting)
2. **Policy Gate** checks — no booking, no live fares → allowed
3. **Planner** (LLM call): extracts intent = `full_plan`, slots = Delhi→Jaipur, 3 days, 2 people, ₹20k, train preference; creates task list
4. **Executor** runs tools in sequence:
   - `compare_transport` → train vs bus vs road from structured data
   - `search_travel_kb` → Jaipur POIs, tips, best areas with citations
   - `list_pois` → attractions with visit durations
   - `estimate_budget` → deterministic: (train×2) + (hotel×3) + food + activities = total
   - `assemble_itinerary` → day-wise plan from POIs and pace
5. **Critic** checks: budget totals match? citations present? train preference reflected? → APPROVE
6. **Composer** (LLM call): writes the final markdown answer with day-by-day plan, cost table, "indicative only" note, and citation list
7. **Checkpoint** saves the `TripContext` to SQLite for multi-turn continuity
8. **UI** renders the response

Total: ~6–8 graph steps (hard cap: 10)

---

## Multi-Turn Conversation

The system maintains conversation state through `TripContext` — a structured object checkpointed in SQLite per conversation thread. This means:

- Turn 1: "Suggest a 3-day trip from Bangalore under ₹15k" → Planner asks: "Which month and travel style?"
- Turn 2: "December, relaxed" → System suggests Coorg and Hampi with citations
- Turn 3: "Plan Coorg in detail for 2 people" → Full plan generated, TripContext locked to Coorg
- Turn 4: "Switch to bus instead of car" → Only transport is re-run; the Coorg POIs and itinerary are retained

This is real multi-turn refinement — not just chat history.

---

## Evaluation Framework

We followed the capstone template strictly: **evaluate before you build the agent**.

- **60+ frozen eval queries** with gold answers written before any agent code
- **3 prompting strategies** (A: structured few-shot, B: chain-of-thought, C: decomposition) compared on the baseline single-agent
- **Retrieval evaluation**: Recall@K measured separately from E2E performance
- **Agent evaluation**: task completion rate, average tool calls per query, failure taxonomy (retrieval miss, reasoning error, tool-call error, hallucination)
- **Red-team probes**: corpus prompt injection, PII handling, refusal boundary testing

All results are in `reports/` as JSON files. All 4 capstone gates (data, retrieval, agent, release) are documented as PASSED in `docs/gates/`.

---

## What We Deployed

The full production stack:

| Component | Technology |
|---|---|
| Chat UI + Trace dashboard | Streamlit |
| REST API | FastAPI with rate limiting (60 rpm) and retrieval caching |
| Agent orchestration | LangGraph state machine |
| Containerization | Docker Compose (API + UI) |
| Observability | JSONL trace logs per node and tool call |
| Tests | 81 pytest tests across smoke, integration, and use-case suites |

---

## Demo Walkthrough (Live)

*The following is what we show during the demo — in this order:*

### 1. Refusal (30 seconds)
Type: `"Book a flight on my credit card from Delhi to Mumbai"`

The Policy Gate catches this before any LLM call and returns a polite refusal with a HITL disclaimer. This shows our responsible AI boundary — JourneyX plans, it never books.

### 2. Transport Comparison (1 minute)
Type: `"Compare Delhi to Jaipur transport options for 2 people"`

The Executor calls `compare_transport` — a deterministic Python tool reading our structured table. Multiple modes appear (train, bus, road) with indicative costs and durations. The LLM did not generate these numbers.

### 3. RAG with Citations (1 minute)
Type: `"What are the best months to visit Jaipur and why?"`

A pure RAG query. The answer includes `[cite:doc_id]` references. We can click through to show the source document. This demonstrates hybrid retrieval and citation grounding.

### 4. Full Plan (2 minutes)
Type: `"Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000"`

This triggers the complete pipeline. The response includes:
- Day-wise itinerary (Day 1, Day 2, Day 3)
- Budget breakdown table (transport, accommodation, food, activities, total)
- "Indicative only" disclaimer
- Citation list at the bottom

### 5. Trace Dashboard (1 minute)
Switch to the **Trace dashboard** tab in Streamlit. Filter by `executor`. Show the tool spans — `compare_transport`, `search_kb`, `estimate_budget` — with step count (≤10) and latency per node. This is our observability layer.

### 6. Evaluation Results (1 minute)
Open `reports/agent_eval_v1.json`. Show task completion rate, average tool calls, and the failure taxonomy. This demonstrates that we measured the system rigorously, not just demoed the happy path.

---

## Key Numbers to Remember

| Metric | Value |
|---|---|
| LLM model | Qwen3-8B (≤8B, hosted capstone API) |
| Max graph steps per query | 10 (hard cap) |
| Max LLM calls per query | 4 |
| Max tool calls per query | 8 |
| Max Critic revise loops | 2 |
| Eval queries (frozen) | 60+ with gold answers |
| Prompting strategies compared | 3 (A, B, C) |
| Pytest tests | 81 |
| Capstone gates passed | 4 of 4 |
| Files in codebase | 135 |
| GitHub | https://github.com/PAVITHRA-3005/JourneyX-AI |

---

## One-Line Summary for the Mentor

> *"JourneyX is a multi-agent travel planning copilot that compensates for a small 8B model by keeping the LLM's role narrow — it only plans and composes — while all facts, numbers, and calculations come from a team-owned knowledge base through deterministic tools and hybrid RAG, with a Critic agent as a quality gate before every response."*

---

*JourneyX — indicative travel planning copilot. All prices and itineraries are for planning only; not booking or payment.*