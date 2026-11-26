# JourneyX AI: A Multi-Agent Travel Planning Copilot on a Hosted ≤8B LLM

**Programme:** IIT KGP Executive Post Graduate Programme in Generative AI and Agentic AI  
**Track:** Track B — API-Side (hosted ≤8B endpoint, no GPU for teams)  
**Members:** Pavithra V, Suresh Huse, Prabhakar Raturi, Srivishwa T, Pradeep Bastia, Raj Chatterjee  
**GitHub:** https://github.com/PAVITHRA-3005/JourneyX-AI  
**Submission Date:** November 2026

---

## Submission Links

| Item | Link |
|------|------|
| **Demo Video (10 min)** | https://drive.google.com/file/d/1GIuuKraro-uqkAwGQTm9Tn-vBD_EeT-X/view?usp=drive_link |
| **GitHub Repository** | https://github.com/PAVITHRA-3005/JourneyX-AI |
| **Trace Dashboard** | Streamlit UI → "Trace Dashboard" tab (http://localhost:8501 when running locally) |

> **Demo Video:** Permission set to "anyone with the link can view". **GitHub:** Public repository. **Trace Dashboard:** Embedded in Streamlit UI; screenshots in Section 8. **Model Card:** Section 9.4.

---

## Abstract

JourneyX is a conversational travel planning copilot built entirely on a hosted ≤8B language model (Qwen3-8B) with no fine-tuning and no frontier models. The core challenge is that small models hallucinate prices, invent distances, and make arithmetic errors. Our solution is a multi-agent architecture where the LLM handles language understanding and prose composition, while all factual retrieval and numerical computation are handled by deterministic tools and a hybrid RAG pipeline.

The system achieves **91.7% task completion** across 72 frozen evaluation queries, **100% refusal accuracy**, and outperforms a vanilla LLM baseline by **+69% on ROUGE-1** and **+141% on BLEU**.

---

## 1. Introduction

### 1.1 Problem Statement

Trip planning requires reconciling information from transport aggregators, hotel sites, travel blogs, and budget calculators. Small language models (≤8B) are unreliable for this task — they invent prices, hallucinate distances, and produce arithmetic errors. The challenge is to build a production-quality travel assistant using only a small hosted model.

### 1.2 Capstone Context

This project is submitted under **Track B (API-Side)**. All inference uses the hosted capstone chat-completions endpoint (Qwen3-8B, ≤8B parameters). No fine-tuning, no frontier models, no external APIs at runtime. The system demonstrates that a small model can power a production-quality copilot when compensated by strong architecture.

### 1.3 Scope

JourneyX v1 covers 13 Indian destinations. It provides indicative travel planning — destination discovery, transport comparison, accommodation suggestions, budget estimation, and day-wise itinerary assembly. It does **not** book tickets, guarantee live fares, or replace human judgment for payments, visas, or safety decisions.

---

## 2. System Architecture

### 2.1 Five-Layer Architecture

```
[User Interface]  Streamlit Chat + Trace Dashboard (port 8501)
       │
[API Gateway]     FastAPI + Rate Limit (60 rpm) + Cache (port 8000)
       │
[Agent Layer]     Policy Gate → Planner → Executor → Critic → Composer
       │
[Tools & RAG]     8 deterministic tools + Hybrid BM25+FAISS+Reranker
       │
[Knowledge Base]  523 documents + structured JSONL tables (13 cities)
```

### 2.2 Agent Pipeline (Per Query)

| Step | Node | LLM? | Description |
|------|------|------|-------------|
| 1 | **Policy Gate** | ❌ Rules only | Checks refusal policy; refuses booking, PII, unsafe requests |
| 2 | **Planner** | ✅ Call #1 | Classifies intent, extracts slots, produces ordered task list |
| 3 | **Executor** | ❌ Deterministic | Calls tools for retrieval, transport, accommodation, budget |
| 4 | **Critic** | ✅ Call #2 (optional) | Verifies citations, budget totals, slot completeness |
| 5 | **Composer** | ✅ Call #3 | Produces user-facing markdown from approved executor bundle |
| 6 | **Follow-up** | ✅ Call #4 (optional) | Suggests 3 follow-up questions (zero-shot, independent) |

**Intents:** `full_plan`, `transport_compare`, `rag_qa`, `refine`, `clarify`, `refuse`

**Guardrails:** ≤10 graph steps, ≤4 LLM calls, ≤8 tool calls, ≤2 Critic revise loops per query.

### 2.3 Technology Stack

| Component | Technology |
|-----------|-----------|
| LLM | Qwen3-8B (capstone hosted API) |
| Agent orchestration | LangGraph |
| Sparse retrieval | BM25 (rank_bm25) |
| Dense retrieval | FAISS + capstone embeddings |
| Reranker | Cross-encoder (CPU) |
| Backend | FastAPI + uvicorn |
| Frontend | Streamlit |
| Persistence | SQLite (LangGraph checkpoints) |
| Containerization | Docker Compose |
| Testing | pytest (81 tests) |

---

## 3. Knowledge Base and Corpus

### 3.1 Corpus Statistics

The knowledge base is team-owned, curated from public travel information, and **frozen before any agent code was written** (Week 1 gate).

| Asset | Count |
|-------|-------|
| Documents | 523 |
| Cities covered | 13 (Delhi, Jaipur, Goa, Manali, Kochi, Bengaluru, Mumbai, Shimla, Rishikesh, Agra, Mysore, Udaipur, Varanasi) |
| POIs | 23 |
| Accommodations | 10 (budget/mid/premium tiers) |
| Transport routes | 12 city-to-city routes |
| Transport options | 72 mode-specific fares |
| Evaluation queries | 72 (frozen, with gold answers) |

### 3.2 Structured Data Tables

All numerical data (prices, distances, durations) comes from structured JSONL tables — the LLM **never generates numbers**.

| Table | Purpose |
|-------|---------|
| `transport_option` | Mode-specific indicative fares and durations |
| `accommodation` | Tier-based price ranges per city |
| `pois` | Points of interest with visit durations and entry fees |
| `routes` | City-to-city distance matrix |
| `price_assumption` | Daily food and activity cost by tier |

---

## 4. Retrieval Pipeline (RAG)

### 4.1 Hybrid Retrieval

```
Query → BM25 (Top-20) ─┐
                        ├→ RRF Fusion (Top-20) → Cross-Encoder Reranker → Top-5
Query → FAISS (Top-20) ─┘
```

Each retrieved chunk carries a `doc_id`. The Composer includes `[cite:doc_id]` for every factual claim; the Critic rejects responses with missing citations.

### 4.2 Retrieval Evaluation

Evaluated on 38 human-labeled query-document pairs:

| Metric | Value |
|--------|-------|
| Recall@1 | 23.8% |
| Recall@3 | 35.7% |
| **Recall@5 (production)** | **42.9%** |
| Recall@10 | 45.2% |
| MRR@10 | 0.2844 |

Production uses K=5 — best recall with manageable LLM context. Marginal gain from K=10 does not justify the added context cost.

---

## 5. Multi-Agent Orchestration

### 5.1 Tool Registry (8 Tools)

| Tool | Type | Description |
|------|------|-------------|
| `search_travel_kb` | RAG | Hybrid BM25+FAISS+rerank, returns chunks with cite IDs |
| `compare_transport` | Structured | Reads transport_option table |
| `find_accommodations` | Structured | Reads accommodation table by city and tier |
| `list_pois` | Structured | Returns POIs for a city |
| `estimate_budget` | Deterministic Python | Computes total: transport + stays + food + activities |
| `assemble_itinerary` | Deterministic Python | Builds day-wise plan from POIs and pace |
| `get_route_info` | Structured | Returns distance and transport options |
| `get_destination_profile` | Structured | Returns destination attributes and seasonal advice |

### 5.2 Multi-Turn State

`TripContext` is checkpointed to SQLite after each turn (keyed by `thread_id`). Changing the budget on turn 4 updates only budget fields while retaining destination, POIs, and itinerary from prior turns.

---

## 6. Evaluation Results

### 6.1 Methodology

Evaluation set of **72 frozen queries** with gold answers, designed before any agent code was written. Six intent categories covering the full scope of the system.

### 6.2 Overall Agent Metrics

| Metric | Value |
|--------|-------|
| **Task Completion Rate** | **91.7% (66/72)** |
| Refusal Accuracy | 100% (8/8) |
| Average tool calls/query | 1.71 |
| Average graph steps/query | 4.39 (budget: 10) |

### 6.3 By Intent Category

| Category | N | Success Rate |
|----------|---|-------------|
| Refusal | 8 | 100% |
| Clarify | 10 | 100% |
| RAG Q&A | 17 | 94.1% |
| Transport Compare | 14 | 85.7% |
| Full Plan | 16 | 81.3% |
| Refine | 7 | 100% |

### 6.4 Failure Taxonomy

| Class | Count | Description |
|-------|-------|-------------|
| `ok` | 66 | Task completed successfully |
| `incomplete_plan` | 3 | Full plan missing itinerary day(s) |
| `no_tool_result` | 2 | Route not in knowledge base |
| `no_grounding` | 1 | Factual claim without citation |

### 6.5 Prompting Strategy Comparison (Baseline)

Three strategies tested on single-agent baseline before multi-agent build:

| Strategy | Description | Key Finding |
|----------|-------------|-------------|
| A — Structured Few-Shot | 3 worked examples in target JSON schema | Better format, still hallucinated prices |
| B — Chain-of-Thought | Step-by-step reasoning | Better reasoning, still invented numbers |
| C — Decomposition | Break query into sub-tasks | Best structure, still failed on numerical queries |

**Finding:** All three strategies failed on numerical queries. This motivated removing arithmetic from the LLM entirely.

### 6.6 RAG vs Vanilla LLM (Lexical Metrics)

| Metric | RAG Agent | Vanilla LLM | Improvement |
|--------|-----------|-------------|-------------|
| ROUGE-1 | **0.3124** | 0.1847 | **+69.1%** ✅ |
| ROUGE-2 | **0.1456** | 0.0612 | **+137.9%** ✅ |
| ROUGE-L | **0.2891** | 0.1634 | **+76.9%** ✅ |
| BLEU | **0.0823** | 0.0341 | **+141.3%** ✅ |

### 6.7 LLM-as-a-Judge

Questions, ground truth answers, and predicted answers were organized into JSON batches of 10 and sent to a capable judge model (ChatGPT/Claude) for binary correctness scoring. Results are in `docs/eval_report.md`.

---

## 7. Compensating for a Small Model

The ≤8B model cannot reliably recall prices, perform arithmetic, or maintain consistency across long structured responses.

| Compensation | Technique | Impact |
|-------------|-----------|--------|
| Code-First Executor | Deterministic Python for all arithmetic | Budget hallucination: **0%** |
| Structured Source of Truth | All prices from JSONL tables | Factual accuracy: 100% for covered routes |
| Hybrid RAG + Citation Enforcement | Critic rejects uncited claims | Grounding failures: 1/72 |
| Narrow LLM Roles | Each LLM call has one responsibility | Consistency improved |
| Structured Output + Retry | JSON schema enforcement, 3 retries | Planner parse failures: 0% |
| Hard Step/Token Budgets | ≤10 steps, ≤4 LLM calls | Runaway loops: 0 |

---

## 8. Deployment and Observability

### 8.1 Production Stack

```bash
docker compose up --build
# API: http://localhost:8000  (FastAPI, rate limit 60 rpm, TTL cache)
# UI:  http://localhost:8501  (Streamlit chat + trace dashboard)
```

### 8.2 Offline / Demo Mode

```bash
export JOURNEYX_AGENT_DRY_RUN=true        # Heuristic planner (no LLM)
export JOURNEYX_EMBEDDING_FALLBACK=true   # TF-IDF dense retrieval
export JOURNEYX_DISABLE_RERANK=true       # Skip cross-encoder
```

### 8.3 Observability

Every graph execution produces a JSONL trace in `reports/agent_traces.jsonl` with per-node spans (latency, input/output summaries) and per-tool call records. The Streamlit Trace Dashboard provides filtering by node type, intent, and status.

---

## 9. Responsible AI

### 9.1 Refusal Policy

| Category | Enforcement |
|----------|-------------|
| Live booking / payment | Policy Gate (0 LLM calls) |
| Guaranteed real-time fares | Policy Gate (0 LLM calls) |
| PII storage (Aadhaar, passport, credit card) | Policy Gate (0 LLM calls) |
| Illegal or unsafe travel | Policy Gate (0 LLM calls) |
| Corpus prompt injection | Policy Gate + Critic |

**Red-team results:** 20/20 adversarial probes refused correctly (100%).

### 9.2 Human-in-the-Loop Boundary

JourneyX is a **planning and estimation tool only**. Every response includes an "indicative only" disclaimer. Real purchases, visa decisions, and safety-critical choices require human verification off-system.

### 9.3 PII Handling

No PII is stored or logged. Trace logs record query summaries only.

### 9.4 Model Card

| Field | Details |
|-------|---------|
| **Model Name** | Qwen3-8B-Instruct (hosted capstone endpoint) |
| **Model Type** | Decoder-only transformer, ≤8B parameters |
| **Intended Use** | Conversational travel planning — destination discovery, transport comparison, budget estimation, itinerary assembly |
| **Out-of-Scope Use** | Live booking, payment, real-time fares, medical/safety advice, visa decisions |
| **Training Data** | Pre-trained by Alibaba Cloud; no fine-tuning by this team |
| **Evaluation Results** | 91.7% task completion, 100% refusal accuracy, ROUGE-1: 0.3124 (+69% over vanilla) |
| **Limitations** | Cannot recall specific prices without retrieval; arithmetic errors without deterministic tools |
| **Compensations** | Deterministic tools for arithmetic; hybrid RAG for facts; Critic for hallucination detection |
| **Failure Modes** | Incomplete plans (3/72); missing routes in KB (2/72); citation omission (1/72) |
| **Refusal Behaviour** | Booking, payment, PII, illegal travel refused by rule-based Policy Gate (0 LLM calls) |
| **Human-in-the-Loop** | All prices indicative only; real purchases require human verification |
| **Data Provenance** | Team-curated from public travel information; no user data stored |

---

## 10. Conclusion

JourneyX demonstrates that a ≤8B hosted model can power a production-quality travel planning copilot when the architecture compensates for the model's limitations. **Role separation** is the key insight: the LLM handles language; deterministic tools and hybrid RAG handle facts and numbers.

| Achievement | Result |
|-------------|--------|
| Task completion rate | **91.7%** (66/72) |
| Refusal accuracy | **100%** (8/8) |
| Budget hallucination | **0%** |
| ROUGE-1 vs vanilla | **+69.1%** |
| BLEU vs vanilla | **+141.3%** |
| Retrieval Recall@5 | **42.9%** |
| Responsible AI probes | **20/20 passed** |

The capstone constraint of a ≤8B model was not a limitation to work around — it was the design driver that produced a more robust architecture.

---

## 11. References

1. LangGraph — LangChain, Inc. https://github.com/langchain-ai/langgraph
2. FAISS — Johnson et al. (2019). Billion-scale similarity search with GPUs. IEEE Trans. Big Data.
3. BM25 — Robertson & Zaragoza (2009). The Probabilistic Relevance Framework. Foundations and Trends in IR.
4. RRF — Cormack et al. (2009). Reciprocal rank fusion outperforms condorcet. SIGIR.
5. BERT Score — Zhang et al. (2020). BERTScore: Evaluating Text Generation with BERT. ICLR.
6. ROUGE — Lin (2004). ROUGE: A Package for Automatic Evaluation of Summaries. ACL Workshop.
7. FastAPI — https://fastapi.tiangolo.com/
8. Streamlit — https://streamlit.io/
9. Qwen3 — Alibaba Cloud. Qwen3 Technical Report, 2025.
10. BGE Embeddings — BAAI. https://huggingface.co/BAAI/bge-small-en-v1.5

---

## Appendix — Capstone Requirement Traceability

| Requirement (Track B) | Delivery | Status |
|-----------------------|----------|--------|
| Task spec + refusal policy | `docs/product-spec.md` | ✅ |
| 60–100 eval queries with gold answers | `data/eval/eval_v1.jsonl` (72 queries) | ✅ |
| ≥3 prompting strategies compared | `prompts/baseline/` (A, B, C) | ✅ |
| RAG 500–2000 documents | 523 documents | ✅ |
| Hybrid BM25 + dense retrieval | `rag/sparse.py` + `rag/dense.py` + `rag/fusion.py` | ✅ |
| Reranker | `rag/rerank.py` (cross-encoder, CPU) | ✅ |
| Citation-grounded answers | Critic enforces `[cite:doc_id]` | ✅ |
| Recall@K measured separately | `reports/retrieval_eval_v1.json` | ✅ |
| ≥3 tools | 8 tools in `tools/` | ✅ |
| Planner→Executor→Critic loop | `orchestration/graph.py` | ✅ |
| Persistent state across turns | SQLite checkpoints | ✅ |
| Error handling (JSON, loops, budget) | Retry logic + step budget | ✅ |
| ≤10 steps/query | Hard cap enforced | ✅ |
| E2E accuracy + failure taxonomy | `reports/agent_eval_v1.json` | ✅ |
| ROUGE/BLEU metrics | `scripts/run_evaluation_metrics.py` | ✅ |
| RAG vs Vanilla comparison | `reports/baseline_results.json` | ✅ |
| Top-K retrieval comparison | `reports/retrieval_eval_v1.json` | ✅ |
| LLM-as-a-Judge | `docs/eval_report.md` | ✅ |
| Follow-up suggestions in UI | `apps/ui/streamlit_app.py` | ✅ |
| Streamlit UI | `apps/ui/streamlit_app.py` | ✅ |
| Docker containerization | `docker-compose.yml` | ✅ |
| Rate limiting + caching | `apps/api/middleware.py` | ✅ |
| Responsible AI (refusal, PII, HITL) | Policy Gate + `docs/refusal-policy.md` | ✅ |
| GitHub repo with README + launch instructions | `README.md` | ✅ |