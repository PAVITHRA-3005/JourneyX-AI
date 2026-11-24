# JourneyX AI — Complete system explained (read-through guide)

This document explains **every major part** of the Capstone repo so you can understand, demo, and extend it without guessing. It complements (does not replace):

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) — canonical architecture & compliance  
- [IDEA_AND_AGENT_FLOW.md](IDEA_AND_AGENT_FLOW.md) — agent narrative & diagrams  
- [PRINCIPAL_ENGINEER_REVIEW.md](PRINCIPAL_ENGINEER_REVIEW.md) — readiness review & gaps  
- [TEST_SUITE.md](TEST_SUITE.md) — 44 automated use-case tests  

**Reading order:** Sections 1–4 (big picture) → 5 (data) → 6–8 (code by week) → 9–12 (ops) → 13 (cheat sheet).

---

## Table of contents

1. [What you built in one story](#1-what-you-built-in-one-story)  
2. [Four capstone weeks → code map](#2-four-capstone-weeks--code-map)  
3. [How a user message becomes an answer](#3-how-a-user-message-becomes-an-answer)  
4. [Repository tree (every folder)](#4-repository-tree-every-folder)  
5. [Data layer — files and meaning](#5-data-layer--files-and-meaning)  
6. [Package `journeyx` — module by module](#6-package-journeyx--module-by-module)  
7. [Foundation in depth — eval & baseline](#7-in-depth--eval--baseline)  
8. [RAG in depth — RAG pipeline](#8-in-depth--rag-pipeline)  
9. [Agent in depth — agents & API](#9-in-depth--agents--api)  
10. [Scripts — what each does](#10-scripts--what-each-does)  
11. [Configuration & secrets](#11-configuration--secrets)  
12. [Prompts & LLM behavior](#12-prompts--llm-behavior)  
13. [Tests & verification](#13-tests--verification)  
14. [Reports & runtime artifacts](#14-reports--runtime-artifacts)  
15. [Environment variables reference](#15-environment-variables-reference)  
16. [How to read the codebase (study plan)](#16-how-to-read-the-codebase-study-plan)  
17. [Quick commands cheat sheet](#17-quick-commands-cheat-sheet)  

---

## 1. What you built in one story

**JourneyX** is a **travel planning copilot** for IIT KGP Track B:

- It **does not** book flights, take payment, or call Google Maps / MakeMyTrip.  
- It **does** answer from **your own** documents + structured tables (cities, routes, fares, POIs, hotels).  
- It uses the **hosted capstone LLM** (Qwen3-8B, ≤8B) and **embeddings API** (bge-small-en-v1.5).  
- After Agent a user message goes through **policy → planner → executor (tools) → critic → composer**, implemented as **LangGraph nodes**, exposed via **FastAPI** `POST /v1/chat`.

**Design philosophy:**

| Principle | What it means in code |
|-----------|----------------------|
| **Ground numbers in structured data** | `compare_transport`, `estimate_budget` read JSONL, not LLM fantasy prices |
| **Ground facts in RAG** | `search_travel_kb` returns chunks with `[cite:…]` markers |
| **8B is weak at tool JSON** | Executor is **code-first**: planner emits task **names**; Python fills args |
| **Measure before agents** | Foundation baseline A/B/C on frozen eval |
| **Measure retrieval separately** | RAGRecall@K on labeled queries |
| **Bounded agent** | ≤10 graph steps, ≤8 tool calls per turn |

---

## 2. Capstone requirements → code map

| Layer | Template | Main deliverable | Primary locations |
|------|-----------|------------------|-------------------|
| **Data & baseline** | I + II | Specs, corpus, frozen eval, **single-agent** baseline | `data/`, `docs/*spec*`, `packages/journeyx/eval/baseline.py`, `prompts/baseline/` |
| **Retrieval** | III | **RAG** index + **≥3 tools** | `packages/journeyx/rag/`, `tools/search_kb.py`, `tools/transport.py` |
| **Agent** | IV | **LangGraph** P→E→C, checkpoints, FastAPI | `packages/journeyx/orchestration/`, `apps/api/main.py` |
| **Release** | V + VI | Full eval, UI, Docker, demo | Streamlit, `docker-compose.yml` |

**Gate checklists:** `docs/gates/data-gate.md`, `docs/gates/retrieval-gate.md`, `docs/gates/agent-gate.md`.

---

## 3. How a user message becomes an answer

### 3.1 Entry points

| Entry | When |
|-------|------|
| `POST /v1/chat` | Production-style HTTP (`apps/api/main.py`) |
| `run_turn(message)` | Python / tests (`orchestration/graph.py`) |
| `run_baseline.py` | Foundation only — **no graph**, single LLM calls |

### 3.2 Graph nodes (Agent

```
                    ┌─────────┐
                    │ policy  │  Regex refusal (booking, PII, pay, IRCTC, …)
                    └────┬────┘
           refuse        │ continue
              ┌──────────┴──────────┐
              ▼                     ▼
        ┌─────────┐           ┌─────────┐
        │composer │           │ planner │  Heuristic OR LLM → PlannerOutput
        └────┬────┘           └────┬────┘
             END            clarify│ plan
                            ┌──────┴──────┐
                            ▼             ▼
                      ┌─────────┐   ┌─────────┐
                      │composer │   │executor │  run_task() per TaskPlanItem
                      └────┬────┘   └────┬────┘
                           END           ▼
                                     ┌─────────┐
                                     │ critic  │  Rules + max 2 REVISE
                                     └────┬────┘
                                          ▼
                                     ┌─────────┐
                                     │composer │  Markdown from tool outputs
                                     └────┬────┘
                                          END
```

**Files:** `orchestration/graph.py` (wiring), `orchestration/nodes.py` (logic), `tools/registry.py` (tools).

### 3.3 What gets saved

| Artifact | Purpose |
|----------|---------|
| `data/checkpoints.sqlite` | LangGraph thread memory (`thread_id`) |
| `reports/agent_traces.jsonl` | Per-node spans for demo/debug |
| `reports/traces.jsonl` | Foundation baseline spans |

---

## 4. Repository tree (every folder)

```text
Capstone/
├── apps/api/                 FastAPI application
├── packages/journeyx/        All importable Python (pip install -e .)
├── data/                     Knowledge base + eval + indexes (not all in git: indexes may be local)
├── config/                   rag.yaml, credentials.example.yaml, credentials.local.yaml (gitignored)
├── certs/                    vm05 (chat TLS), vm02 (embeddings TLS)
├── prompts/baseline/           Foundation strategy prompts
├── docs/                     Specs + guides (this file)
├── scripts/                    CLIs, gates, verify, test suite
├── tests/                      pytest (44 tests)
├── reports/                    Generated metrics & traces
├── pyproject.toml              Package deps + pytest config
├── requirements.txt            Pip mirror of main deps
├── IMPLEMENTATION_PLAN.md    Master plan
├── ProjectIdea.md            Executive summary for report intro
└── docs/gates/*-gate.md             validation checklists
```

**Import rule:** From repo root, `PYTHONPATH` includes `packages` (and `apps` for FastAPI). Tests set this in `pyproject.toml` `[tool.pytest.ini_options]`.

---

## 5. Data layer — files and meaning

### 5.1 `data/manifest.yaml` — “what version is the KB?”

Single source of **counts and provenance**: `corpus_version`, `document_count`, `chunk_count`, `chunking_winner`, `embedding_fallback`, `indexed_at`, eval counts, hold-out cities.

**Why it matters:** Every report slide on corpus size should cite manifest + `EVAL_FROZEN.md`.

### 5.2 Structured JSONL (`data/structured/`) — numbers you trust

| File | Contents | Used by |
|------|----------|---------|
| `cities.jsonl` | lat/lon, airport, best months | Route haversine, discovery |
| `destination_profile.jsonl` | dest_id, tags, budget tier | `lookup_destinations` |
| `pois.jsonl` | POI hours, fees | `list_pois`, `assemble_itinerary` |
| `accommodations.jsonl` | price per night, tier | `find_accommodations`, budget |
| `routes.jsonl` | origin/dest, distance_km | `get_route_info`, transport filter |
| `transport_option.jsonl` | mode, cost bands, **road_diesel** | `compare_transport` |
| `price_assumption.jsonl` | Food/misc assumptions | Budget logic (extensible) |

Pydantic models live in `packages/journeyx/core/structured.py`. **Data validation gate** validates every row parses.

### 5.3 `data/documents/documents.jsonl` — text you retrieve

Each row is a `TravelDocument`: `doc_id`, `dest_id`, `doc_type`, `title`, `body`. These become **chunks** in RAG. Doc types include `destination_guide`, `faq`, `poi_card`, `transport_guide`, etc.

### 5.4 Eval (`data/eval/`)

| File | Role |
|------|------|
| `eval_v1.jsonl` | 72 tasks: `category`, `query`, `gold_facts`, `expected_refusal`, `conversation_prefix` (refine), `relevant_doc_ids` |
| `retrieval_labels_v1.jsonl` | 38 queries → expected doc IDs for Recall@K |
| `EVAL_FROZEN.md` | Hash lock — don’t change eval without versioning |

**Eval categories** (must all exist): `refusal`, `clarify`, `rag_qa`, `transport_compare`, `full_plan`, `refine`.

### 5.5 Indexes (`data/indexes/v1/`) — built by ingest

| File | Role |
|------|------|
| `chunks.jsonl` | Chunk text + metadata for each indexed piece |
| `bm25.pkl` | Sparse index |
| `dense.faiss` + `dense.npy` / `embeddings_v1.npy` | Vector search |
| `ingest_report.json` | Last ingest stats |

Regenerate: `scripts/ingest_corpus.py`.

### 5.6 Other runtime data

| File | Role |
|------|------|
| `data/checkpoints.sqlite` | LangGraph conversation checkpoints |
| `VM02_Embeddings_Access/` | Course materials: embedding key file, vm02 CA cert |

---

## 6. Package `journeyx` — module by module

Install: `pip install -e .` from repo root (into `.venv`).

### 6.1 `journeyx.core`

| File | Purpose |
|------|---------|
| `structured.py` | Pydantic models for all KB tables + `TravelDocument` |
| `eval_item.py` | `EvalItem` schema for eval JSONL |
| `planner_output.py` | `PlannerOutput`, `TripSlots`, `TaskPlanItem`, task **enum** |

**Mental model:** `core` = **contracts** shared by eval, planner, and report.

### 6.2 `journeyx.config`

| File | Purpose |
|------|---------|
| `capstone.py` | Load `config/credentials.local.yaml` + `.env`; build `httpx` client with CA cert paths |

Functions: `get_settings()`, `reload_settings()`, `build_http_client()`, `mask_key()`.

### 6.3 `journeyx.llm`

| File | Purpose |
|------|---------|
| `client.py` | `LLMClient.chat()`, `chat_structured()` with JSON schema + retries; respects `JOURNEYX_BASELINE_DRY_RUN` |

Used by: Foundation baseline, live planner (when `JOURNEYX_AGENT_DRY_RUN=false`).

### 6.4 `journeyx.rag`

| Module | Role |
|--------|------|
| `chunking.py` | Split documents into chunks (`structure_aware` winner) |
| `embeddings.py` | VM02 API or deterministic fallback vectors |
| `sparse.py` | BM25 index build/search |
| `dense.py` | FAISS build/search |
| `fusion.py` | Reciprocal Rank Fusion |
| `rerank.py` | Cross-encoder (optional off in CI) |
| `retrieve.py` | `HybridRetriever`, `load_retriever()` |
| `ingest.py` | Full pipeline orchestration, manifest update |
| `linter.py` | Corpus consistency checks |
| `models.py` | `ChunkRecord`, `SearchRequest`, `RetrievalHit` |

**Config:** `config/rag.yaml`.

### 6.5 `journeyx.tools`

| Module | Tool(s) |
|--------|---------|
| `search_kb.py` | `search_travel_kb` |
| `transport.py` | `get_route_info`, `compare_transport` |
| `discovery.py` | `lookup_destinations`, `find_accommodations`, `list_pois` |
| `budget.py` | `estimate_budget` (deterministic) |
| `itinerary.py` | `assemble_itinerary` |
| `registry.py` | `run_task()` — Executor dispatch |
| `loaders.py` | Cached JSONL loaders for routes/transport |

### 6.6 `journeyx.orchestration`

| Module | Role |
|--------|------|
| `state.py` | `AgentState` TypedDict fields |
| `budgets.py` | `MAX_GRAPH_STEPS=10`, `MAX_TOOL_CALLS=8`, step bump |
| `nodes.py` | `policy_node`, `planner_node`, `executor_node`, `critic_node`, `composer_node` |
| `graph.py` | `build_graph()`, `run_turn()` |
| `__init__.py` | Re-exports `run_turn` |

### 6.7 `journeyx.eval`

| Module | Role |
|--------|------|
| `baseline.py` | Run strategies A/B/C on eval items |
| `retrieval_eval.py` | Recall@K, MRR from labels |
| `kb_context.py` | Optional KB digest for baseline ablation |

### 6.8 `journeyx.observability`

| Module | Role |
|--------|------|
| `trace.py` | `TraceSpan`, `TraceWriter` → append JSONL |

---

## 7. Foundation in depth — eval & baseline

### 7.1 Why Foundation exists

Capstone template **II** says: characterize the **8B model** with prompting **before** building agents. That gives you report material (“invalid JSON”, “hallucinated prices”) and a frozen test set.

### 7.2 Baseline flow

1. `run_baseline.py` loads `eval_v1.jsonl`.  
2. For each item, builds messages: system + strategy prompt (`prompts/baseline/*.md`) + user query.  
3. Calls `LLMClient` (or dry-run `{}`).  
4. Scores: schema validity, gold fact overlap, refusal detection.  
5. Writes `reports/baseline_results.json` and traces.

**Strategies:**

- **A_structured** — JSON slots few-shot  
- **B_cot** — think then answer  
- **C_decomposition** — sub-questions first  

### 7.3 Docs you own (Foundation

| Doc | You explain in report… |
|-----|-------------------------|
| `product-spec.md` | Scope, non-goals |
| `refusal-policy.md` | What we never do |
| `dataset-schemas.md` | Field definitions |
| `tool-contracts.md` | Tool I/O (now implemented in Agent |

### 7.4 Data validation gate

`scripts/validate_data_gate.py` — checks file existence, eval categories, `road_diesel`, manifest ≥500. Warns if baseline summary is dry-run only.

---

## 8. RAG in depth — RAG pipeline

### 8.1 Why hybrid retrieval?

Sparse (BM25) finds exact keyword matches (“Amber Fort”). Dense (embeddings) finds paraphrases (“best time Jaipur”). **RRF** merges ranked lists without tuning a single score scale. **Reranker** re-orders top candidates with a cross-encoder.

### 8.2 Ingest (offline job)

```powershell
.\.venv\Scripts\python.exe scripts/ingest_corpus.py
.\.venv\Scripts\python.exe scripts/ingest_corpus.py --experiment   # chunking ablation table
```

Updates `data/indexes/v1/` and `manifest.yaml`.

### 8.3 Query-time path

`search_travel_kb` → `load_retriever()` → `HybridRetriever.search()`:

1. Embed query (API or fallback).  
2. BM25 top-k + dense top-k.  
3. RRF → fused list.  
4. Optional rerank → `RetrievalHit` with `cite_marker`.  

### 8.4 Retrieval metrics (not chat quality)

`run_retrieval_eval.py` compares retrieved doc IDs to `retrieval_labels_v1.jsonl`. Output: `reports/retrieval_eval_v1.json`.

**Interpretation:** ~0.37 Recall@5 on fallback embeddings is a **development** number; re-run after VM02 ingest for the report.

### 8.5 Retrieval validation gate

Validates index files, `search_travel_kb` returns chunks, transport includes `road_diesel`.

---

## 9. Agent in depth — agents & API

### 9.1 Planner

**Output schema:** `PlannerOutput` (`core/planner_output.py`).

- **`intent`:** e.g. `compare_transport`, `full_plan`, `rag_qa`, `clarify`, `refusal`.  
- **`slots`:** `TripSlots` — cities, dest_id, days, party_size, pace, budget.  
- **`tasks`:** ordered list of `TaskPlanItem` — each `task` is a **string enum** matching a tool name.

**Modes:**

- **Heuristic** (`nodes._heuristic_planner`): keyword rules — used when `JOURNEYX_AGENT_DRY_RUN=true` (tests, CI).  
- **LLM:** `chat_structured(..., PlannerOutput)` when dry-run false and credentials work.

### 9.2 Executor

Loops `planner.tasks` and calls `registry.run_task(task, slots, user_message)`. No LLM chooses tool arguments in the happy path.

**Tool call budget:** stops at 8 tools per turn (`MAX_TOOL_CALLS`).

### 9.3 Critic

Checks executor bundle: non-empty, not all errors, `full_plan` should have itinerary object. Can return **REVISE** → executor again (max 2 revises). Then **APPROVE**.

### 9.4 Composer

Builds user-visible markdown: disclaimer, KB line, transport line, budget line, itinerary line. Not an LLM chain-of-thought dump.

### 9.5 Policy (refusal)

Regex list in `nodes.REFUSAL_PATTERNS` — booking, purchase, IRCTC, Aadhaar, card payment, etc. Matches `docs/refusal-policy.md` themes. Short-circuit: **policy → composer**, skip planner.

### 9.6 FastAPI (`apps/api/main.py`)

```json
POST /v1/chat
{
  "message": "Compare Delhi Jaipur transport for 2",
  "thread_id": "optional-uuid",
  "conversation_prefix": [{"role":"user","content":"..."},{"role":"assistant","content":"..."}]
}
```

Response includes `step_count`, `tool_calls`, `status`, `planner_intent`.

---

## 10. Scripts — what each does

| Script | Purpose |
|--------|---------|
| `seed_eval_data.py` | Regenerate corpus + eval (destructive; use carefully) |
| `validate_data_gate.py` | Foundation acceptance |
| `validate_retrieval_gate.py` | RAG acceptance |
| `validate_agent_gate.py` | Agent acceptance |
| `ingest_corpus.py` | Build/rebuild RAG indexes |
| `run_retrieval_eval.py` | Write `retrieval_eval_v1.json` |
| `run_baseline.py` | FoundationA/B/C on eval |
| `export_baseline_summary.py` | Markdown summary for docs |
| `setup_credentials.py` | Copy CA certs, scaffold `credentials.local.yaml` |
| `test_capstone_api.py` | Live chat + embed smoke (VPN) |
| `complete_live_baseline.ps1` | Smoke → production ingest → baseline (VPN) |
| `verify_all.ps1` | compileall + gates + pytest + Agent validation gate + tool smoke |
| `run_test_suite.ps1` | pytest 44 use-case tests |
| `bootstrap_venv.ps1` | Create `.venv` + install deps |
| `capstone-python.ps1` | Run any command with repo venv |
| `lib/CapstoneVenv.ps1` | Resolve `.venv` / `.venv-review` |

---

## 11. Configuration & secrets

### 11.1 `config/credentials.local.yaml` (gitignored)

```yaml
chat:
  api_base: https://103.42.50.41:1033/v1
  api_key: sk-...
  model: Qwen/Qwen3-8B
  ca_cert: certs/vm05-ca.crt
embeddings:
  api_base: https://103.42.50.41:1035/v1
  api_key: sk-...
  model: bge-small-en-v1.5
  ca_cert: certs/vm02-ca.crt
```

Template: `config/credentials.example.yaml`. Guide: `docs/capstone-api-setup.md`.

### 11.2 `config/rag.yaml`

Chunk sizes, retrieval top-k, RRF `k`, reranker model name.

### 11.3 `.env` (optional, gitignored)

Overrides like `CAPSTONE_CHAT_API_KEY`. Primary store is still YAML.

---

## 12. Prompts & LLM behavior

### 12.1 Baseline prompts (`prompts/baseline/`)

Used **only** by `run_baseline.py`. Three strategies + shared system prompt (`system_travel.md` if present).

### 12.2 Agent prompts

Planner system text is **inline** in `planner_node` today. **Improvement for Production** move to `prompts/planner/system.md` for versioning in report.

### 12.3 Constrained decoding

`llm/client.py` sends OpenAI-compatible `response_format` with Pydantic `model_json_schema()` for `PlannerOutput` when live.

---

## 13. Tests & verification

| Command | What it proves |
|---------|----------------|
| `scripts/run_test_suite.ps1` | **44** use-case tests (offline) |
| `scripts/verify_all.ps1` | Gates + ingest + pytest + smoke |
| Individual `validate_*_gate.py` | component acceptance only |

**Test layout:** see [TEST_SUITE.md](TEST_SUITE.md).

**Important:** Tests set `JOURNEYX_EMBEDDING_FALLBACK=true` and `JOURNEYX_AGENT_DRY_RUN=true` — they prove **logic**, not live API quality.

---

## 14. Reports & runtime artifacts

| Path | Generated by | Use in report |
|------|--------------|---------------|
| `reports/retrieval_eval_v1.json` | retrieval eval | RAG metrics table |
| `reports/baseline_results.json` | baseline runner | Prompting comparison |
| `docs/baseline_results_summary.md` | export script | Foundation summary |
| `reports/traces.jsonl` | baseline | Trace examples |
| `reports/agent_traces.jsonl` | agent nodes | Demo of P/E/C |

---

## 15. Environment variables reference

| Variable | Default in tests | Effect |
|----------|------------------|--------|
| `JOURNEYX_EMBEDDING_FALLBACK` | `true` in CI | Hash vectors vs VM02 API |
| `JOURNEYX_DISABLE_RERANK` | `true` in CI | Skip cross-encoder download |
| `JOURNEYX_AGENT_DRY_RUN` | `true` in CI | Heuristic planner |
| `JOURNEYX_BASELINE_DRY_RUN` | `true` in tests | Baseline without API |

Set all `false` on VPN for **live** demo (respect rate limits: 1 concurrent req/key).

---

## 16. How to read the codebase (study plan)

**Session 1 — Data (30 min)**  
Read `manifest.yaml`, one line each from structured JSONL, one `TravelDocument`, one `eval_v1` row.

**Session 2 — RAG (45 min)**  
Trace: `ingest_corpus.py` → `rag/ingest.py` → `retrieve.py` → `search_kb.py`.

**Session 3 — Tools (30 min)**  
Read `transport.py`, `registry.py`, run mentally: Delhi–Jaipur compare.

**Session 4 — Agent (60 min)**  
Read `graph.py` → each function in `nodes.py` → `run_turn` in REPL.

**Session 5 — Eval & report (45 min)**  
Skim `baseline.py`, run `run_test_suite.ps1`, open `retrieval_eval_v1.json`.

---

## 17. Quick commands cheat sheet

```powershell
# Repository root (folder containing scripts/, packages/, data/)
cd <path-to-repo>

# Environment
powershell -File scripts\bootstrap_venv.ps1

# Full verification
powershell -File scripts\verify_all.ps1

# Use-case tests only
powershell -File scripts\run_test_suite.ps1

# RAG rebuild
.\.venv\Scripts\python.exe scripts\ingest_corpus.py

# Agent one-liner
.\.venv\Scripts\python.exe -c "from journeyx.orchestration import run_turn; print(run_turn('Plan 3 days Jaipur')['response'])"

# API server
$env:PYTHONPATH='packages;apps'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir apps --port 8000

# Live capstone APIs (VPN)
.\.venv\Scripts\python.exe scripts\test_capstone_api.py
```

---

## Related documents (pick by need)

| Need | Read |
|------|------|
| Viva / demo script | [PRINCIPAL_ENGINEER_REVIEW.md](PRINCIPAL_ENGINEER_REVIEW.md) §16 |
| Agent narrative & mermaid | [IDEA_AND_AGENT_FLOW.md](IDEA_AND_AGENT_FLOW.md) |
| RAG commands only | [rag-pipeline.md](rag-pipeline.md) |
| API keys & VPN | [capstone-api-setup.md](capstone-api-setup.md) |
| Test matrix | [TEST_SUITE.md](TEST_SUITE.md) |
| Compliance checklist | [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §16 |
