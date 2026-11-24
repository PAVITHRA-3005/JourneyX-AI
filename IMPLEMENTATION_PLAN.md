# JourneyX AI — Consolidated Implementation Plan

**Track:** B — API-Side (Multi-Agent Copilot on hosted ≤8B inference API)  
**Domain:** Travel planning assistant (aligned with capstone suggested domains: travel-and-expense / policy-style copilot over owned corpus)  
**Canonical doc:** This file supersedes scattered architecture notes. `ProjectIdea.md` is the executive summary; **technical and capstone compliance detail lives here.**

**Principles**

1. Only capstone **chat-completions (≤8B)** and **embeddings** at runtime — no fine-tuning, no frontier models in production, no third-party travel/maps/booking/web-search APIs.  
2. Facts come from a **versioned, team-owned knowledge base** (documents + structured tables).  
3. **Evaluate before you agent** — Data validation gate per capstone template.  
4. **Compensate for the small model** in architecture (tools, RAG, schema validation, bounded graph) — graded explicitly in the 12-page report.

This document is planning only; it does not prescribe implementation code.

---

## Capstone Track B — requirement traceability

Every “must build” item from `Capstone-Templates-GenAI-Agent ic-AI.pdf` maps to JourneyX as follows.

| ID | Template requirement | JourneyX delivery | Evidence artifact |
|----|----------------------|-------------------|-------------------|
| **I** | Foundation task spec, refusal policy, correct-answer definition, **60–100 eval queries with gold answers before any code** | `docs/product-spec.md`, `docs/refusal-policy.md`, `data/eval/eval_v1.jsonl` (gradable gold per row: §9.1) | Frozen eval + signed Foundation checkpoint in repo |
| **II** | Foundation single-agent baseline; **≥3 prompting strategies** compared; document how 8B breaks | Strategies A/B/C on frozen subset; `docs/baseline-prompting.md` | Baseline metrics table in report |
| **III** | RAG **500–2,000 documents**; chunking experiments; **hybrid BM25 + dense**; **reranker**; **citation-grounded** answers; **Recall@K separate from E2E** | Owned travel corpus; ingest log; retrieval eval job | `reports/retrieval_eval_v1.json` |
| **IV** | Agentic system; **≥3 tools**; **planner→executor→critic**; **persistent state**; errors: tool failure, malformed JSON, loops, **token budget**; **≤10 steps/query** | LangGraph; see §6–7 | Trace logs + step counters |
| **V** | E2E on frozen eval; task completion; **avg tool calls**; **cost/latency**; failure taxonomy (retrieval miss, reasoning error, tool-call error, hallucination); **Langfuse / LangSmith / OTel** | Eval harness + dashboard | `reports/eval_report.md` |
| **VI** | Release: Streamlit or React; **Docker**; **rate limiting + caching**; responsible AI: **corpus prompt-injection**, **PII**, **refusal**, **HITL boundary** | Docker Compose stack | Red-team log + demo |
| — | Core engineering: **constrained decoding, JSON schema validation, retry logic** | API `response_format`/JSON schema where supported → Pydantic → retry (§6.6) | Unit tests + trace failures |
| — | Graded: **“What did we do to compensate for a small model?”** | §8 + report § | Ablation table |
| — | Guardrail: corpus **≤2,000 documents**; agent **≤10 steps/query** | `manifest.yaml` counts; runtime enforcer | CI + runtime metrics |

**Capstone deliverables (template)**

| Deliverable | Location / owner |
|-------------|------------------|
| Git repository with full agent stack | Root repo |
| Trace dashboard (real executions) | Langfuse self-hosted or JSONL viewer (M5) |
| Evaluation report + failure taxonomy | `reports/eval_report.md` (M5) |
| 12-page technical report | Course submission |
| 10-minute live demo | M6 lead |

**Grading weights (awareness):** technical depth 30%, punctuality 25%, working system 20%, report + demo 25%. Data validation gate and agent reliability are the usual schedule cliffs (template: hardest milestone = agent reliability).

---

## 1. Product scope and correctness

### 1.1 What JourneyX does

- Conversational trip planning over **curated Indian destinations (v1).**  
- Destination discovery, transport **comparison (indicative)**, routes, stays, POIs, **deterministic budget**, day-wise itinerary, multi-turn **refine**.  
- All recommendations **grounded** in KB citations and/or tool outputs.

### 1.2 What a correct answer looks like

| Query type | Correct behavior |
|------------|------------------|
| Factual (POI, best season) | Answer from RAG/tools; **≥1 citation** per factual claim; “indicative” where prices used |
| Compare transport | **Table from tools**; modes in KB (flight, train, bus, petrol/diesel road, EV road where data exists) |
| Full plan | Slots filled or **one** clarifying question; budget breakdown + itinerary; within stated budget or explicit overrun explanation |
| Refine | Updates **only** changed fields; retains `TripContext`; no full re-plan unless asked |
| Out of scope | **Refusal** per policy; no tools that imply booking |

**Language v1:** English queries and corpus (document in spec); mixed Hindi optional stretch with disclaimer.

### 1.3 Refusal policy (summary)

Refuse or deflect: live booking/payment, guaranteed real-time fares, requests requiring external inventory, illegal or unsafe travel, medical/safety guarantees, storing unnecessary PII.

**Human-in-the-loop boundary:** JourneyX **plans and estimates only**. Any real purchase, visa decision, or safety-critical choice requires human verification off-system. Stated in UI and system prompt.

Full matrix: `docs/refusal-policy.md`.

---

## 2. Dependency policy

### 2.1 Allowed

| Dependency | Use |
|------------|-----|
| Capstone chat-completions (≤8B) | Generation / structured extraction only via thin `llm` adapter |
| Capstone embeddings | Index build + dense retrieval (vectors cached on disk per `corpus_version`) |
| OSS: FastAPI, LangGraph, Pydantic, FAISS/Chroma, BM25, Streamlit, Docker | App stack |
| Local cross-encoder reranker (CPU) | Rerank top-k (template requires a reranker step) |
| Langfuse OSS / OpenTelemetry / JSONL traces | Observability |

### 2.2 Excluded (educational self-contained data)

| Excluded | Replacement |
|----------|-------------|
| Live fare / OTA / hotel APIs | `transport_option`, `accommodation` tables + RAG blurbs |
| Maps / routing APIs | `route` matrix + haversine fallback with uncertainty flag |
| Web search / scraping at runtime | Hybrid RAG + structured lookups |
| Frontier LLMs at inference | Capstone endpoint only |

**Offline note:** Optional use of a larger model **only** for draft dataset text during early corpus curation, with human verification — never in the request path.

### 2.3 How agents “search”

1. **Hybrid RAG** over owned document chunks (citation IDs).  
2. **Structured queries** over SQLite/JSONL tables (cities, routes, POIs, stays).  
3. **Deterministic tools** for comparisons and budgets (no LLM arithmetic).

---

## 3. System architecture

```mermaid
flowchart TB
  subgraph clients["Presentation"]
    UI[Streamlit]
  end

  subgraph edge["FastAPI edge"]
    API[API: auth, rate limit, cache, request_id]
  end

  subgraph graph["LangGraph (≤10 steps, token cap)"]
    REF[Refusal / policy gate]
    PL[Planner node]
    EX[Executor node]
    CR[Critic node]
    RSP[Response composer]
    CKPT[(Checkpoints / TripContext)]
  end

  subgraph capabilities["Local capabilities"]
    RAG[Hybrid RAG + rerank]
    TR[Tool runtime]
    IDX[(Vector index)]
    BM[(BM25)]
    DB[(SQLite structured)]
  end

  subgraph data["Owned dataset"]
    MAN[manifest.yaml corpus_version]
    DOC[documents 500–2000]
    TBL[structured tables]
  end

  subgraph hosted["Capstone only"]
    LLM[Chat ≤8B]
    EMB[Embeddings]
  end

  subgraph quality["Eval & ops"]
    EVAL[Eval harness]
    OBS[Traces / dashboard]
  end

  UI --> API --> graph
  REF --> PL
  PL --> EX --> CR
  CR -->|APPROVE| RSP
  CR -->|REVISE| EX
  PL -->|CLARIFY| RSP
  REF -->|REFUSE| RSP
  PL & EX & CR & RSP --> LLM
  EX --> RAG & TR
  RAG --> IDX & BM & EMB
  TR --> DB
  DOC & TBL --> RAG & DB
  MAN --> RAG & TR
  graph --> CKPT
  API & graph & RAG --> OBS
  EVAL --> graph & RAG
```

### 3.1 Layered modules (repository intent)

```text
journeyx/
  apps/api/              # FastAPI
  apps/ui/               # Streamlit (thin client)
  packages/core/         # TripContext, policies, ID types
  packages/llm/          # Capstone client, structured output + retry
  packages/rag/          # ingest, retrieve, cite
  packages/tools/        # deterministic tools
  packages/orchestration/# LangGraph, agents as nodes
  packages/eval/         # retrieval + E2E harness
  data/manifest.yaml
  data/structured/
  data/documents/
  data/eval/eval_v1.jsonl
  data/provenance/
  prompts/               # versioned prompts
  reports/
  docs/
  infra/docker/
```

### 3.2 Course starter integration

The capstone supplies an **API key, token quota, and starter agent skeleton**. Agent should **extend the provided skeleton** (LLM client, tracing hooks, sample graph) rather than greenfield reinventing it — unless instructors direct otherwise. JourneyX-specific nodes (travel tools, RAG adapter, `TripContext`) plug into that layout; document deltas in `README.md`.

---

## 4. Data architecture

### 4.1 Two layers — single source of truth (SoT)

| Layer | SoT for | Access |
|-------|---------|--------|
| **Structured tables** | **All numbers**: prices, distances, durations, fees | Tools only |
| **Document corpus** | Narrative: culture, tips, seasonal prose, activity descriptions | RAG |

**Consistency rule:** RAG chunks **must not** embed standalone numeric prices without linking `stay_id` / `poi_id` / `route_id`. Narrative references structured IDs (“Amber Fort — `poi_jaipur_amber`”). Ingestion linter flags currency literals without FK (`docs/gates/retrieval-gate.md`).

### 4.2 Entity model (canonical names)

| Entity | Key fields | Relationships |
|--------|------------|---------------|
| `city` | `city_id`, name, state, lat, lon, `airport_code?`, `best_months[]` | 1—N `destination_profile` |
| `destination_profile` | `dest_id`, `city_id`, tags[], `budget_tier`, `summary_doc_id` | Parent for POI/stay content |
| `poi` | `poi_id`, `dest_id`, name, category, `typical_duration_hrs`, `fee_band_inr` | Itinerary builder |
| `accommodation` | `stay_id`, `dest_id`, name, tier, `price_per_night_inr`, area | Budget + ranking |
| `route` | `route_id`, `origin_city_id`, `dest_city_id`, `distance_km` | Connectivity |
| `transport_option` | `opt_id`, `route_id`, `mode`, `duration_hrs`, `cost_inr_min`, `cost_inr_typical`, `cost_inr_max`, notes | Compare transport (flight, train, bus, road_petrol, road_diesel, road_ev) |
| `price_assumption` | `key`, value, unit, disclaimer | `estimate_budget` |
| `faq_map` | `faq_id`, paraphrases[], `target_doc_id` | High-precision routing |

**Citation format:** `cite:{doc_id}` for chunks; tool outputs cite `tool:{name}:{record_id}`.

### 4.3 Corpus sizing (template III)

| Term | Definition | Target v1 |
|------|------------|-----------|
| **Document** | One logical record (`doc_id`) before chunking | **500–2,000** (capstone cap) |
| **Chunk** | Retrieval unit (POI cards often 1:1) | Report chunk count in manifest |

**Geography v1:** 15–25 destinations; **hold-out 3 destinations** not used for chunking tuning (generalization in report). Expand only from eval gaps.

**manifest.yaml** fields: `corpus_version`, `document_count`, `chunk_count`, checksums, `embedding_model_ref`, `chunking_winner`, `built_at`.

### 4.4 Routes without maps APIs

Precompute for in-scope city pairs (30–80 pairs growing with scope): `distance_km`, mode durations, cost bands. Missing pair: haversine + **heuristic** road multiplier; output `confidence: low` and disclaimer — never imply exact GPS routing.

### 4.5 Curation workflow (runtime agents do not write prod KB in v1)

Intake (schema validate) → QA (M1+M4) → chunk/index (M2) → retrieval regression (M5) → merge on version bump. Optional stretch: `propose_kb_patch` → human staging queue (HITL).

### 4.6 Foundation data MVP (avoid overload)

| By end Foundation(minimum) | By end RAG(template) |
|---------------------------|---------------------------|
| 10 destinations, core structured rows | 15–25 destinations |
| 150–200 documents (grow to 500+) | **≥500 documents** |
| Eval **≥60** queries frozen | Same set + retrieval labels 30–50 |
| 3 prompting baselines on **≥30** queries | Full baseline on all eval |

---

## 5. RAG pipeline (template III)

| Stage | Experiments to log (report) | Implementation notes |
|-------|----------------------------|----------------------|
| Chunking | Fixed size vs structure-aware (per `doc_type`); overlap | Pick **winner** before final index |
| Dense | Capstone embeddings; **embed once** per `corpus_version` | Store vectors in `data/indexes/` |
| Sparse | BM25 on same chunks | Same tokenization policy |
| Fusion | RRF vs weighted hybrid | **Ablation** on labeled set |
| Rerank | Local cross-encoder: retrieve 20 → rerank 5 | Required reranker step |
| Grounding | Inject `[cite:doc_id]`; UI shows title, type, indicative flag | Critic validates resolvable cites |

**Retrieval router (by intent):** `discover` → `lookup_destinations` + filtered RAG; `fact_qa` → metadata filters + hybrid; `plan` → RAG for POIs + tools for numbers.

**Metrics (separate from E2E):** Recall@5, Recall@10, MRR on 30–50 `query → relevant_doc_ids` labels tied to `corpus_version`. Run via `packages/eval/retrieval_eval.py` after every index rebuild.

**Citation correctness (operational):** Sample 20 E2E answers; human or rubric checks % claims with valid `cite:*` resolving to manifest.

---

## 6. Agent orchestration (template IV)

### 6.1 Planner → Executor → Critic (logical roles)

Present three agents in report/demo. **Implementation uses LangGraph nodes** with a **hybrid Critic** (deterministic checks first; LLM when the template “critic agent” must be visible).

| Node | Responsibility | LLM calls (typical) |
|------|----------------|---------------------|
| **Refusal / policy** | Rule-based + blocked patterns | 0 |
| **Planner** | Intent, slot extraction, `TaskPlan[]`, clarifying question | 1 structured call |
| **Executor** | Run tools/RAG per plan; **code-first** when slots complete | 0–1 (only if ambiguous tool routing) |
| **Critic** | Schema, budget, cite coverage, consistency tool↔text | See **Critic policy** below |
| **Response composer** | Natural language over **approved** structured bundle | 1 |

**Critic policy (demo + grading):**

| Task class | Critic mode |
|------------|-------------|
| `full_plan`, `refine` | **Always LLM Critic** after deterministic pre-checks (grounding, budget match) |
| `rag_qa`, `transport_compare`, `clarify` | Deterministic rules where possible; LLM optional |
| All paths | Traces MUST include `node=planner`, `node=executor`, `node=critic` spans for dashboard filter |

**Target happy path:** 2–3 LLM calls per turn (Planner + compose; Critic LLM on complex plans), not three redundant full-agent monologues per turn.

### 6.2 Graph invariants

```text
- Executor MUST NOT run until required_slots met OR user confirmed partial plan
- Numeric claims in final text MUST match tool outputs or cited chunks linked to structured IDs
- Critic REVISE loops back to Executor only (max 2); else APPROVE_PARTIAL with disclaimer
- Refine intents patch TripContext via reducer — do not wipe itinerary/history
- CLARIFY and REFUSE exit without Executor
```

### 6.3 Persistent state

**TripContext (checkpointed):** intents, slots (origin, dest, dates, party, budget, prefs), artifacts (itinerary, budget_breakdown, citations, tool_trace), `corpus_version`, `missing_slots[]`.

**Ephemeral (per turn):** `TaskPlan`, `executor_bundle`, `critic_verdict`, `step_count`, `token_usage`, `errors[]`.

**Memory compression:** When history exceeds token threshold, summarize to `TripContext` snapshot + last 2 user/assistant turns.

**Storage:** LangGraph checkpoints in SQLite (same DB or separate file).

### 6.4 Step and budget definitions (template guardrails)

**What counts as one step (capstone ≤10):** Each graph node visit (`refusal`, `planner`, `executor`, `critic`, `response_composer`), each **Critic REVISE** loop, and each distinct **tool batch** inside Executor (one batch = up to N tools in one Executor pass).

**Design target:** Happy path **≤6 steps** (e.g. refusal → planner → executor → critic → composer) so **2 revises** still stay under 10.

| Budget | Limit | On exceed |
|--------|-------|-----------|
| **Graph steps** | **≤10** per user query (capstone) | Hard stop → partial plan + `status: degraded` |
| **LLM calls** | ≤4 per query | Stop; return partial + `status: degraded` |
| **Tool calls** | ≤8 per query | Executor skips optional enrichment |
| **Tokens** | Per-team quota aware; per-turn cap in config | Trim context; refuse very long pasted docs |
| **Critic revise** | ≤2 | Best-effort approve with warnings |

Document step-counting rules in `docs/tool-contracts.md` (orchestration appendix) so traces match the capstone guardrail in review.

### 6.5 Error handling (template IV — required)

| Failure | Handling |
|---------|----------|
| Tool exception | Typed error → Executor marks task failed → Critic partial response |
| Malformed JSON from LLM | Pydantic validate → **retry ≤2** with error feedback → fallback clarifying question |
| Infinite graph loops | Step counter hard stop |
| Token budget | Truncate history; deterministic summary |
| Weak 8B tool choice | **Code-first Executor** maps `TaskPlan` enum to tools without LLM arg generation |

### 6.6 Structured output and retry (template core engineering)

Use the full stack in order (template: **constrained decoding**, JSON schema validation, retry logic):

1. **Constrained decoding** — OpenAI-compatible **`response_format`** / JSON schema / structured-output mode on the capstone endpoint when available.  
2. **Validation** — Parse with **Pydantic** models shared by runtime and eval harness.  
3. **Retry** — On failure, **≤2** retries with validator error text fed back to the model; then fall back to CLARIFY or degraded partial response.

Applies to Planner and LLM Critic outputs at minimum. Log every validation failure in traces (feeds `tool_call_error` / `schema_invalid`). Document 8B failure modes in `docs/baseline-prompting.md`.

---

## 7. Tools (template: ≥3 tools)

### 7.1 LLM-visible vs internal (8B compensation)

**Exposed to model (≤3 function definitions):** e.g.  
`search_travel_kb`, `execute_plan_step` (or `plan_trip`), — keep descriptions stable and minimal.

**Internal Executor capabilities (≥3, traced as tool spans):**

| Tool | Purpose |
|------|---------|
| `search_travel_kb` | Hybrid retrieval + citations |
| `lookup_destinations` | Tag/month/budget discovery |
| `compare_transport` | Mode table from `transport_option` |
| `get_route_info` | Route row or haversine fallback |
| `find_accommodations` | Filter stays by budget/tier |
| `list_pois` | POI list + optional RAG blurbs |
| `estimate_budget` | **Deterministic** BudgetModel v1 |
| `assemble_itinerary` | Template + rules from POIs and pace |

Capstone requires **≥3 tools** — satisfied by traced internal tools even if only 1–2 are LLM-invoked.

**Metrics (template V):** Report **avg tool calls per task** using `tool_invocations_total` (all traced tool spans). Optionally also log `llm_tool_calls` (tools the model invoked directly) in the report — both numbers are useful for 8B analysis.

### 7.2 BudgetModel v1 (deterministic)

**Inputs:** nights, party_size, selected `transport_option`, `stay_id` or tier price, food tier enum, sum of `poi.fee_band_inr`, line items from `price_assumption`.  
**Output:** JSON breakdown + total + assumptions list.  
**Critic:** Final total must match `estimate_budget` when budget question asked.

Golden vectors in eval unit tests (`docs/gates/agent-gate.md`).

---

## 8. Compensating for ≤8B (graded report section)

Document in 12-page report with **ablation table** (baseline prompt vs +RAG vs +tools vs full graph ± critic).

| Technique | Purpose |
|-----------|---------|
| Facts in structured KB + RAG, not parametric memory | Reduce hallucination |
| Deterministic budget/route tools | Remove arithmetic from LLM |
| Code-first Executor | Reduce malformed tool calls |
| Hybrid retrieval + rerank | Lift recall for weak generator |
| Small LLM-visible tool surface | Simpler function calling |
| Hybrid Critic (rules + optional LLM) | Quality without triple-agent cost |
| Narrow geography + FAQ map | Higher precision |
| Cite-or-refuse for prices/distances | Grounding enforcement |
| JSON schema + 2 retries | Template core engineering |

Include honest **failure log** from Foundation baseline carried forward.

---

## 9. Evaluation and observability (template V)

### 9.1 Data validation gate (before agent / LangGraph code)

**Gate policy (staged build):** the evaluation set and prompting baseline preceded the LangGraph agent. RAG ingest and indexing were developed in parallel with data-layer deliverables; the multi-node planner → executor → critic graph and checkpoints ship after the data gate checklist below is satisfied.

**Gate checklist:**

- [ ] `docs/product-spec.md` + `docs/refusal-policy.md`  
- [ ] `data/eval/eval_v1.jsonl` — **60–100** items (schema below)  
- [ ] Baseline single-agent: **3 strategies** (structured few-shot; CoT or self-consistency; decomposition)  
- [ ] Baseline metrics on **≥30** queries by gate day; **full 60–100** by early RAG 
- [ ] Planned tool JSON schemas / Pydantic models documented  

**Eval row schema (gradable gold — satisfies template “gold answers” without 100 prose itineraries):**

| Field | Required | Purpose |
|-------|----------|---------|
| `id`, `query`, `category` | Yes | Identity |
| `gold_facts[]` | Yes | Must-mention facts, entity/POI/route IDs, or refusal expectation |
| `reference_answer_short` | Yes for `rag_qa`, `clarify`, refusal items | 2–4 sentence grader target |
| `gold_rubric[]`, `expected_tools[]`, `must_not[]` | As needed | Task completion |
| `expected_refusal`, `refusal_rationale` | For refusal items | Refusal eval |
| `relevant_doc_ids[]` | For retrieval-labeled items | Recall@K |
| `corpus_version` | Yes | Frozen at `v1` |

Full plans: grade via `gold_facts` + rubric (budget line present, cites KB, uses `compare_transport`) rather than a single gold paragraph.

### 9.2 Eval categories (suggested mix)

| Category | Share | Task completion criterion |
|----------|-------|---------------------------|
| Refusal | 10–15% | Correct refuse; no booking tools |
| Clarify | 15% | One targeted question |
| RAG QA | 25% | Correct fact + citations |
| Transport compare | 20% | Tool table matches KB |
| Full plan | 25% | Budget + itinerary + grounding |
| Refine | 10% | Context preserved, field updated |

### 9.3 Metrics (reporting)

| Metric | Source |
|--------|--------|
| E2E accuracy / rubric score | Checklist on `gold_facts` + rubric; optional LLM-as-judge (temp 0) — include ≥1 non-judge metric in report |
| Task completion rate | Per category pass/fail |
| Recall@K, MRR | Retrieval-only harness |
| Citation validity | Sample audit + automatic ID resolution |
| Schema validity | % valid planner/critic payloads |
| Tool success rate | Traces |
| **Avg tool calls per task** | Traces (`tool_invocations_total`; optional `llm_tool_calls`) |
| **Latency & token cost per query** | Traces + capstone billing |
| Failure taxonomy counts | Manual tag on failures |

### 9.4 Failure taxonomy (template — use these primary tags)

**Report roll-up (template PDF):** Every failure maps to one of **`retrieval_miss` | `reasoning_error` | `tool_call_error` | `hallucination`**. Extended tags below are for debug; in `eval_report.md` always show the four-bucket counts first.

| Tag | Definition | PDF bucket |
|-----|------------|------------|
| `retrieval_miss` | Gold doc not in top-K | retrieval_miss |
| `reasoning_error` | Retrieved OK but wrong plan/conclusion | reasoning_error |
| `tool_call_error` | Tool failure or bad tool args | tool_call_error |
| `hallucination` | Unsupported fact | hallucination |
| `refusal_miss` | Should refuse, didn’t (or inverse) | reasoning_error |
| `schema_invalid` | Structured output failed after retries | tool_call_error |
| `timeout` | Step/token/quota limit | tool_call_error or reasoning_error (note in report) |

### 9.5 Trace schema (minimum viable dashboard)

Per span: `trace_id`, `thread_id`, `corpus_version`, `prompt_version`, `node` (`planner`|`executor`|`critic`|…), `tool_name?`, `step_index`, `latency_ms`, `tokens_in`, `tokens_out`, `status`, `error_class?`.

**Demo:** Dashboard filterable by `node` so Planner → Executor → Critic is visible on live traces (deliverable).

**Backends:** Langfuse (self-hosted in Docker) **or** JSONL export + simple Streamlit trace viewer — must show **real query executions** for deliverable.

---

## 10. Ship, security, responsible AI (template VI)

### 10.1 Deployment

- **Streamlit** UI → **FastAPI** (all agent logic server-side).  
- **Docker Compose:** `api`, `ui`, optional `langfuse`, optional `redis` for rate limit/cache.  
- **Rate limiting:** token bucket per API key/IP (slowapi or middleware).  
- **Caching:**  
  - **Do cache:** retrieval results `(corpus_version, normalized_query, filters)` TTL.  
  - **Do not cache:** full multi-turn agent responses without `thread_id` + turn index.

### 10.2 Threat model (short)

| Asset | Risk | Mitigation |
|-------|------|------------|
| System prompt | User/jailbreak | Instruction hierarchy; refusal node |
| Retrieved chunks | **Corpus prompt injection** | Treat RAG as untrusted; cite-only quoting; **≥20 injection tests** in KB + user messages |
| Tool args | Injection via user text | Pydantic bounds; enum IDs; no shell |
| Checkpoints/traces | PII leakage | No store of phone/Aadhaar; redact logs |

### 10.3 Responsible AI checklist

- [ ] Prompt-injection test log against document corpus  
- [ ] PII detection/refusal on input  
- [ ] Refusal matrix tested on eval refusal items  
- [ ] HITL boundary in UI: “Indicative plan — verify before booking”  
- [ ] Tool output validation (sanity bounds on prices/distances)

---

## 11. Prompt engineering baseline (template II)

Run **before** LangGraph on frozen eval subset using **single-agent** script:

| Strategy | Description |
|----------|-------------|
| **A — Structured few-shot** | System + JSON examples for itinerary slots |
| **B — CoT or self-consistency** | Think-step variant (document cost/latency) |
| **C — Decomposition** | Explicit sub-questions before answer |

Record: pass rate per category, common JSON errors, hallucinated prices, verbosity. Feeds §8 and report “how the model breaks.”

---

## 12. Technology stack

| Component | Choice |
|-----------|--------|
| LLM / embeddings | Capstone hosted APIs only |
| API + agents | FastAPI, LangGraph, Pydantic |
| Structured data | SQLite |
| Vector | FAISS or Chroma (on-disk) |
| Sparse | BM25 (e.g. `rank_bm25`) |
| Rerank | Local sentence-transformers cross-encoder (CPU) |
| UI | Streamlit |
| Cache | In-process or Redis |
| Observability | Langfuse OSS or OTel or JSONL |
| Deploy | Docker Compose |

---

## 13. Four-week schedule (aligned to template I–VI)

### Foundation— I + II (gate)

| Deliverable | Owner |
|-------------|-------|
| Product spec, refusal policy, data dictionary (§4.2) | M1 |
| Eval v1 ≥60 with `gold_facts` + `reference_answer_short` where required (§9.1); 3 hold-out destinations | M1 |
| Corpus MVP + structured MVP (§4.6) | M1, M4 |
| Baseline prompting A/B/C + failure characterization | M2, M3 |
| LLM adapter + JSON retry pattern spike | M3 |
| Trace schema stub | M5 |

**Gate:** Eval frozen + baseline numbers → **then** agent graph work.

### RAG— III

| Deliverable | Owner |
|-------------|-------|
| **≥500 documents**; chunking experiments; winning strategy | M2 |
| Hybrid index + rerank; `search_travel_kb` | M2 |
| Recall@K report (separate from E2E) | M5 |
| Ingestion linter (numeric SoT) | M2, M4 |
| Tools: route, transport compare | M4 |

### Agent— IV (hardest milestone)

| Deliverable | Owner |
|-------------|-------|
| LangGraph on **course starter skeleton** (§3.2) + checkpoints + TripContext reducers | M3 |
| Planner / Executor / Critic + invariants (§6) | M3, M4 |
| Budget + itinerary tools + golden tests | M4 |
| Step/token enforcer | M3 |
| E2E eval 20+ cases + taxonomy tagging | M5 |
| FastAPI chat endpoint | M6 |

### Release — V + VI

| Deliverable | Owner |
|-------------|-------|
| Full eval run on all 60–100; ablation table | M5 |
| Trace dashboard with real traces | M5 |
| Streamlit + Docker + rate limit + retrieval cache | M6 |
| Injection/PII tests; eval report | M5 |
| Demo script; report outline (12 pp) | All |

---

## 14. Team roles (template ↔ JourneyX)

| Capstone role | Member | Focus |
|---------------|--------|-------|
| Domain spec & eval | M1 | Spec, eval, provenance, structured data QA |
| Prompt engineering | M2 (+M3 baseline) | Baseline strategies, prompt versions |
| RAG / retrieval | M2 | Ingest, hybrid, rerank, citations |
| Agent orchestration & tools | M3, M4 | LangGraph, Executor tools, BudgetModel |
| Observability & safety | M5 | Traces, taxonomy, injection, eval report |
| Front-end & deployment | M6 | API, UI, Docker, cache, demo |

**Integration contract:** M4 owns `data/structured/`; M2 owns index build scripts; shared `city_id` / `dest_id` namespace; PR review across boundary.

---

## 15. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Foundation overload | §4.6 staged MVP |
| Triple-LLM cost/latency | §6.1 hybrid critic, 2–3 calls |
| Dual-layer price drift | §4.1 SoT + linter |
| 8B tool failures | Code-first Executor, ≤3 LLM tools |
| Embedding quota burn | Embed once per manifest |
| Eval overfitting | 3 hold-out destinations |
| Cache wrong plan | §10.1 cache rules |

---

## 16. Deliverables checklist

**Capstone**

- [ ] Git repo — full agent stack + dataset build scripts  
- [ ] Trace dashboard — real executions  
- [ ] Evaluation report — metrics + **failure taxonomy**  
- [ ] 12-page technical report — includes **compensating for 8B** + RAG ablation  
- [ ] 10-minute live demo  

**JourneyX**

- [ ] `manifest.yaml` + schema-validated corpus  
- [ ] Hybrid RAG + rerank + citations  
- [ ] Planner → Executor → Critic LangGraph, persistent state, ≤10 steps  
- [ ] ≥3 tools, JSON validation + retries  
- [ ] Frozen `eval_v1.jsonl`  
- [ ] Docker + rate limiting + caching  
- [ ] Red-team / injection log  

---

## 17. Supporting docs to create (Foundation

| File | Content |
|------|---------|
| `docs/product-spec.md` | Scope, correct-answer rubrics |
| `docs/refusal-policy.md` | Full matrix + examples |
| `docs/baseline-prompting.md` | Strategies A/B/C results |
| `docs/dataset-schemas.md` | §4.2 expanded + ER diagram |
| `docs/tool-contracts.md` | JSON Schema per tool |
| `data/eval/eval_v1.jsonl` | Frozen queries |

---

## 18. Summary

JourneyX is a **Track B–compliant multi-agent travel copilot**: frozen Foundation evaluation, prompting baseline, **500–2,000** document RAG with hybrid retrieval and reranking, LangGraph **planner→executor→critic** with bounded steps and robust tool/JSON handling, full eval and tracing, and a containerized UI with rate limits and caching. The system is **self-contained** (no travel APIs), relies only on the **capstone ≤8B + embeddings**, and uses architecture — not larger models — to deliver grounded, measurable planning.

*Last consolidated: aligns with `Capstone-Templates-GenAI-Agent ic-AI.pdf` Track B requirements I–VI, guardrails, deliverables, and grading context. Pre-implementation architect review patches applied (eval gold schema, Data validation gate, constrained decoding, critic policy, step budget, starter skeleton, taxonomy roll-up).*