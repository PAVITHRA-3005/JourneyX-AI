# JourneyX AI — Presentation & Runbook

> **Audience:** Capstone graders, teammates, and anyone presenting or running JourneyX for the first time.  
> **Purpose:** Understand the system flow, run it end-to-end, and deliver a confident 10-minute demo.

---

## Table of Contents

1. [What is JourneyX?](#1-what-is-journeyx)
2. [System Architecture Flow](#2-system-architecture-flow)
3. [Agent Flow (Step-by-Step)](#3-agent-flow-step-by-step)
4. [How to Run JourneyX](#4-how-to-run-journeyx)
5. [How to Present JourneyX (10-Minute Demo)](#5-how-to-present-journeyx-10-minute-demo)
6. [Sample Queries to Use in Demo](#6-sample-queries-to-use-in-demo)
7. [What to Show on Screen](#7-what-to-show-on-screen)
8. [Answering Tough Questions](#8-answering-tough-questions)
9. [Quick Reference Card](#9-quick-reference-card)

---

## 1. What is JourneyX?

**JourneyX AI** is an intelligent travel planning copilot built for the IIT KGP GenAI Capstone (Track B — API-side).

| What it does | What it does NOT do |
|---|---|
| Discovers destinations, compares transport | Book tickets or hotels |
| Builds day-wise itineraries with budget | Guarantee live/real-time fares |
| Answers travel questions with citations | Use external APIs (Google Maps, OTAs) |
| Refines plans across multiple turns | Replace human judgment for payments/visas |
| Grounds all answers in an owned knowledge base | Hallucinate prices or distances |

**Tech Stack at a glance:**
- **LLM:** Qwen3-8B (hosted capstone API, ≤8B)
- **Orchestration:** LangGraph (Planner → Executor → Critic)
- **Retrieval:** Hybrid BM25 + FAISS + Cross-encoder reranker
- **Backend:** FastAPI with rate limiting & caching
- **Frontend:** Streamlit chat + trace dashboard
- **Deployment:** Docker Compose

---

## 2. System Architecture Flow

```
User Message
     │
     ▼
┌─────────────┐
│ Streamlit UI │  ← Chat interface + Trace dashboard
└──────┬──────┘
       │ POST /v1/chat
       ▼
┌─────────────┐
│  FastAPI    │  ← Rate limiting (60 rpm), caching, trace_id assignment
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│              LangGraph Orchestration                  │
│                                                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│  │  Policy  │───▶│ Planner  │───▶│ Executor │        │
│  │   Gate   │    │  (LLM)   │    │ (Code+LLM│        │
│  └──────────┘    └──────────┘    └────┬─────┘        │
│       │               │               │               │
│    REFUSE          CLARIFY            ▼               │
│       │               │         ┌──────────┐          │
│       │               │         │  Critic  │          │
│       │               │         │(Rules+LLM│          │
│       │               │         └────┬─────┘          │
│       │               │         REVISE│  APPROVE       │
│       │               │              │      │          │
│       │               │              ▼      ▼          │
│       │               │         ┌──────────────┐       │
│       │               │         │   Composer   │       │
│       │               │         │    (LLM)     │       │
│       │               │         └──────┬───────┘       │
└───────┼───────────────┼────────────────┼───────────────┘
        │               │                │
        ▼               ▼                ▼
    Refusal msg    Clarify question   Final answer
                                    + citations
                                    + budget table
                                    + itinerary
```

**Knowledge & Tools (used by Executor):**
```
┌─────────────────────────────────────────────────────┐
│  Hybrid RAG                  Deterministic Tools     │
│  ┌──────────────────┐        ┌───────────────────┐  │
│  │ BM25 (sparse)    │        │ compare_transport  │  │
│  │ FAISS (dense)    │        │ estimate_budget    │  │
│  │ Cross-encoder    │        │ assemble_itinerary │  │
│  │ reranker         │        │ list_pois          │  │
│  └──────────────────┘        │ find_accommodations│  │
│         │                    │ search_travel_kb   │  │
│         ▼                    └───────────────────┘  │
│  Owned Knowledge Base                                │
│  ┌──────────────────────────────────────────────┐   │
│  │ Documents (travel corpus)                    │   │
│  │ Structured tables (cities, routes, fares,    │   │
│  │   stays, POIs, transport options)            │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 3. Agent Flow (Step-by-Step)

### Example Query: *"Plan 4 days in Jaipur from Delhi for 2 people under ₹25,000 by train"*

| Step | Agent/Node | What Happens |
|------|-----------|--------------|
| **1** | **FastAPI** | Assigns `trace_id`, loads `TripContext` for this conversation thread |
| **2** | **Policy Gate** | Checks refusal rules — no booking, no live fares → ✅ ALLOWED |
| **3** | **Planner (LLM)** | Extracts: intent=`full_plan`, origin=Delhi, dest=Jaipur, days=4, people=2, budget=₹25k, mode=train. Creates task list for Executor |
| **4** | **Executor** | Runs `compare_transport` (Delhi→Jaipur, train vs others from structured data) |
| **5** | **Executor** | Runs `search_travel_kb` (Jaipur POIs, tips, best areas) → returns chunks with `[cite:doc_id]` |
| **6** | **Executor** | Runs `list_pois` (Jaipur attractions with durations) |
| **7** | **Executor** | Runs `estimate_budget` (deterministic Python: transport×2 + stays×4 + food + activities) |
| **8** | **Executor** | Runs `assemble_itinerary` (day-wise plan from POIs + pace) |
| **9** | **Critic** | Checks: budget totals match? citations present? train preference reflected? → ✅ APPROVE |
| **10** | **Composer (LLM)** | Writes readable markdown: day-by-day plan, cost table, "indicative only" note, citation list |
| **11** | **Checkpoint** | Saves updated `TripContext` (itinerary v1, budget, citations) for next turn |
| **12** | **UI** | Renders markdown, tables, source links |

**Total graph steps: ~6–8 (cap: 10)**

### Early Exit Flows

| Situation | Path | Result |
|-----------|------|--------|
| "Book my flight" | Policy Gate → REFUSE | Polite refusal + HITL disclaimer |
| "Where to go in March?" (no budget) | Planner → CLARIFY | One focused question to user |
| "Best time to visit Kerala?" | Planner → Executor (search_kb only) → Critic → Composer | RAG answer with citations |
| Tool failure | Executor marks partial → Critic → APPROVE_PARTIAL | Best-effort answer + disclaimer |

### Multi-Turn Refinement

```
Turn 1: "Suggest a 3-day trip from Bangalore under ₹15k"
        → Planner: CLARIFY → "Which month and travel style?"

Turn 2: "December, relaxed"
        → Executor: lookup_destinations + RAG
        → Composer: shortlist Coorg / Hampi with citations

Turn 3: "Plan Coorg in detail, 2 people"
        → Executor: POIs + budget + itinerary
        → TripContext: locked destination = Coorg, itinerary v1

Turn 4: "Switch to bus instead of car"
        → Planner: REFINE (only transport changes)
        → Executor: compare_transport + patch budget
        → TripContext: merged — Coorg POIs retained, transport updated
```

---

## 4. How to Run JourneyX

### Prerequisites

- Python 3.10+
- Windows (PowerShell) or Linux/macOS
- Optional: Docker Desktop
- Optional: VPN for live LLM API access

### Step 1 — Setup (One Time)

```powershell
# Navigate to the JourneyX project folder
cd <path-to-JourneyX>

# Create virtual environment and install all dependencies
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_venv.ps1
```

### Step 2 — Configure Credentials (for Live LLM)

The `.env` file already contains the group API keys. For `credentials.local.yaml`:

```powershell
copy config\credentials.example.yaml config\credentials.local.yaml
# Keys are already in .env — this step is only needed for Docker
```

### Step 3 — Verify Everything Works

```powershell
# Run all validation gates (data, retrieval, agent, release)
powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1

# Run full test suite (81 tests)
powershell -ExecutionPolicy Bypass -File scripts\run_test_suite.ps1
```

Expected: All 4 gates exit **0**, all tests pass.

---

### Option A — Console Demo (Fastest, No Server Needed)

```powershell
# Interactive terminal chat
powershell -ExecutionPolicy Bypass -File scripts\demo_console.ps1

# Single query
powershell -File scripts\demo_console.ps1 -m "Compare Delhi to Jaipur transport for 2 people"

# Run all sample queries automatically
powershell -File scripts\demo_console.ps1 --samples
```

Console commands: `/help`, `/samples`, `/new` (new session), `/quit`

---

### Option B — FastAPI + Streamlit (Full UI)

**Terminal 1 — Start the API:**
```powershell
$env:PYTHONPATH = "$PWD\packages;$PWD\apps"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir apps --host 127.0.0.1 --port 8000
```

**Terminal 2 — Start the UI:**
```powershell
$env:JOURNEYX_API_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\streamlit run apps\ui\streamlit_app.py
```

Open browser: **http://localhost:8501**

- **Chat tab** — type travel queries
- **Trace dashboard tab** — see Planner/Executor/Critic spans

---

### Option C — Docker Compose (Cleanest)

```powershell
docker compose up --build
```

- API: http://localhost:8000
- UI: http://localhost:8501

---

### Offline Mode (No VPN / No API Keys)

```powershell
$env:JOURNEYX_AGENT_DRY_RUN = "true"
$env:JOURNEYX_EMBEDDING_FALLBACK = "true"
```

The heuristic planner runs the same LangGraph graph and all tools — just without live LLM calls. **Perfect for demos when VPN is unavailable.**

---

### Run Evaluations

```powershell
# Baseline prompting comparison (strategies A/B/C)
.\.venv\Scripts\python.exe scripts\run_baseline.py --limit 30

# Retrieval evaluation (Recall@K)
.\.venv\Scripts\python.exe scripts\run_retrieval_eval.py

# Agent evaluation (task completion, failure taxonomy)
.\.venv\Scripts\python.exe scripts\run_agent_eval.py

# Red-team / security probes
.\.venv\Scripts\python.exe scripts\run_redteam.py
```

---

## 5. How to Present JourneyX (10-Minute Demo)

### Before the Audience Arrives

- [ ] VPN connected (if using live LLM)
- [ ] `docker compose up --build` **or** FastAPI + Streamlit running
- [ ] Browser open at **http://localhost:8501**
- [ ] Trace dashboard tab visible
- [ ] `reports/agent_eval_v1.json` open in a text editor as backup
- [ ] Offline fallback ready: `$env:JOURNEYX_AGENT_DRY_RUN = "true"`

---

### Minute-by-Minute Script

#### **Min 0–1 — Introduction (Talk, no typing)**

> *"JourneyX is a travel planning copilot built on a ≤8B hosted LLM. The key design challenge: small models hallucinate prices and distances. Our solution: the LLM only plans and composes — all numbers come from our owned knowledge base through deterministic tools and hybrid RAG."*

**Show:** Architecture diagram (from `docs/IDEA_AND_AGENT_FLOW.md` or a slide)
- Point out: Planner → Executor → Critic flow
- Emphasize: No booking APIs, no Google Maps, no web search — everything from owned data

---

#### **Min 1–2 — Refusal Demo**

Type in chat:
```
Book a flight on my credit card from Delhi to Mumbai
```

**What to say:**
> *"The Policy Gate catches this before any LLM call. JourneyX plans and estimates — it never books or handles payments. This is our HITL boundary."*

**Point out:** The refusal message includes a disclaimer directing users to verify with real booking platforms.

---

#### **Min 2–4 — Transport Comparison**

Type in chat:
```
Compare Delhi to Jaipur transport options for 2 people
```

**What to say:**
> *"The Executor calls `compare_transport` — a deterministic Python tool reading our structured transport table. The LLM doesn't invent these numbers. Notice the 'indicative' label — we're honest about data freshness."*

**Point out:** Multiple modes shown (train, bus, road), cost per person, duration.

---

#### **Min 4–5 — RAG with Citations**

Type in chat:
```
What are the best months to visit Jaipur and why?
```

**What to say:**
> *"This is a pure RAG query. Hybrid BM25 + FAISS retrieval, cross-encoder reranked, top-5 chunks fed to the Composer. Every factual claim has a citation ID — graders can trace it back to the source document."*

**Point out:** `[cite:doc_id]` references in the answer.

---

#### **Min 5–7 — Full Plan**

Type in chat:
```
Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000
```

**What to say:**
> *"This triggers the full Planner → Executor → Critic → Composer pipeline. The Executor runs 5+ tools: transport, POIs, RAG search, budget estimation, itinerary assembly. The Critic validates budget totals and citations before the Composer writes the final answer."*

**Point out:**
- Day-wise itinerary
- Budget breakdown table
- "Indicative only" disclaimer
- Citation list at the bottom

---

#### **Min 7–8 — Trace Dashboard**

Switch to the **Trace dashboard** tab in Streamlit.

**What to say:**
> *"Every node and tool call is traced. Filter by 'executor' to see the tool spans — compare_transport, search_kb, estimate_budget. This is our observability layer — critical for debugging and the capstone evaluation report."*

**Point out:** Step count (should be ≤10), tool call count, latency per node.

---

#### **Min 8–9 — Evaluation Results**

Open `reports/agent_eval_v1.json` or show the terminal output.

**What to say:**
> *"We ran 60+ frozen eval queries with gold answers before building the agent. Here's our task completion rate, average tool calls per query, and failure taxonomy — retrieval misses, reasoning errors, tool failures, and hallucinations. This is the capstone evaluation framework."*

---

#### **Min 9–10 — Guardrails & Wrap-up**

**What to say:**
> *"Key guardrails: ≤10 graph steps per query, ≤4 LLM calls, ≤8 tool calls, ≤2 Critic revise loops. Rate limiting at 60 rpm. Retrieval cache keyed by corpus fingerprint. The system is designed to be reliable and auditable — not just impressive in a demo."*

**Close with:**
> *"JourneyX demonstrates that a small 8B model can power a production-quality copilot when you compensate with strong architecture: narrow LLM roles, deterministic tools, hybrid RAG, and a multi-agent quality gate."*

---

## 6. Sample Queries to Use in Demo

### Refusal Queries (Policy Gate)
```
Book a flight on my credit card
What's the live price for a hotel in Goa tonight?
Can you guarantee the train fare won't change?
```

### Transport Comparison
```
Compare Delhi to Jaipur transport for 2 people
What's the fastest way from Mumbai to Pune?
Train vs road from Bangalore to Mysore — which is cheaper?
```

### RAG / Knowledge Queries
```
Best months to visit Kerala?
What are the top things to do in Udaipur?
Tell me about the food scene in Jaipur
```

### Full Planning
```
Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000
4-day Goa trip from Mumbai for a couple, budget ₹30,000
Weekend trip from Bangalore, relaxed pace, under ₹10,000
```

### Multi-Turn Refinement
```
[After a full plan] Make it ₹15,000 instead
[After a full plan] Switch from train to bus
[After a full plan] Add one more day
```

### Clarification Flow
```
Suggest a trip for March
[System asks: from where, budget, how many days?]
From Delhi, 5 days, ₹25,000
```

---

## 7. What to Show on Screen

| Demo Moment | What to Show |
|-------------|-------------|
| Architecture intro | `docs/IDEA_AND_AGENT_FLOW.md` Mermaid diagrams |
| Refusal | Streamlit chat — refusal message |
| Transport | Streamlit chat — comparison table |
| RAG | Streamlit chat — answer with `[cite:...]` |
| Full plan | Streamlit chat — day-wise itinerary + budget table |
| Traces | Streamlit **Trace dashboard** tab — executor spans |
| Eval results | `reports/agent_eval_v1.json` or terminal output |
| Gate status | `docs/gates/` — all 4 gates PASSED |
| Test suite | Terminal: `scripts/run_test_suite.ps1` output |

---

## 8. Answering Tough Questions

| Question | Answer |
|----------|--------|
| *"Why not use GPT-4?"* | Capstone constraint: ≤8B hosted model only. Our architecture compensates with tools, RAG, and multi-agent quality gates. |
| *"Are the prices real?"* | No — indicative only from our owned dataset. We label everything "indicative" and include a disclaimer. |
| *"What if the LLM hallucinates?"* | The Critic checks that all numbers match tool outputs and all facts have citations. Hallucinated numbers fail the Critic and trigger a REVISE loop. |
| *"How many documents in the KB?"* | Check `data/manifest.yaml` — corpus is within the 500–2,000 document capstone limit. |
| *"Can it handle Hindi?"* | English v1. Mixed Hindi is a stretch goal with disclaimer. |
| *"What's the step limit?"* | ≤10 graph steps per query, enforced at runtime. The happy path is ~6 steps. |
| *"How does multi-turn work?"* | `TripContext` is checkpointed in SQLite per `thread_id`. Each turn loads the prior context and merges updates. |
| *"What's the failure taxonomy?"* | Retrieval miss, reasoning error, tool-call error, hallucination — see `reports/agent_eval_v1.json`. |

---

## 9. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    JOURNEYX QUICK REFERENCE                  │
├─────────────────────────────────────────────────────────────┤
│  START (console)   powershell -File scripts\demo_console.ps1 │
│  START (UI)        docker compose up --build                 │
│                    → http://localhost:8501                   │
│  VERIFY ALL        powershell -File scripts\verify_all.ps1  │
│  RUN TESTS         powershell -File scripts\run_test_suite.ps1│
│  OFFLINE MODE      $env:JOURNEYX_AGENT_DRY_RUN = "true"     │
├─────────────────────────────────────────────────────────────┤
│  AGENT FLOW        Policy → Planner → Executor → Critic      │
│                    → Composer → User                         │
│  GUARDRAILS        ≤10 steps, ≤4 LLM calls, ≤8 tool calls   │
│  TOOLS             compare_transport, estimate_budget,       │
│                    search_travel_kb, list_pois,              │
│                    find_accommodations, assemble_itinerary   │
│  RAG               BM25 + FAISS + cross-encoder reranker     │
│  LLM               Qwen3-8B (capstone hosted API)            │
├─────────────────────────────────────────────────────────────┤
│  KEY DOCS          USER_GUIDE.md — setup & run               │
│                    docs/IDEA_AND_AGENT_FLOW.md — flow        │
│                    docs/DEMO_SCRIPT.md — demo script         │
│                    docs/gates/ — all 4 gates PASSED          │
│                    reports/ — eval JSON files                │
└─────────────────────────────────────────────────────────────┘
```

---

*JourneyX — indicative travel planning copilot. All prices and itineraries are for planning only; not booking or payment.*