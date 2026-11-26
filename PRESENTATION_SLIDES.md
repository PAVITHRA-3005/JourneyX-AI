# JourneyX AI — Capstone Presentation
## Multi-Agent Operations Copilot | Track B (API-Side)
**IIT KGP Executive PGP in Generative AI & Agentic AI**
**Team PAVITHRA-3005 | November 2026**

---

---

# SLIDE 1 — Problem & Solution

## The Problem: Trip Planning is Fragmented

A user planning a 4-day trip from Delhi to Jaipur must:
- Check transport aggregators for fares and timings
- Browse hotel booking sites for accommodation
- Read travel blogs for destination tips
- Use a calculator for budget estimation
- Reconcile inconsistent information across all sources

**No single interface unifies all of this in one conversation.**

---

## Our Solution: JourneyX AI

> A conversational travel planning copilot built entirely on a hosted ≤8B LLM (Qwen3-8B), with no fine-tuning and no frontier models.

### Core Insight
The LLM's role is deliberately **narrow**:
- ✅ Understand natural language
- ✅ Plan tasks and compose prose
- ❌ NOT responsible for prices, distances, or arithmetic

All factual retrieval and numerical computation are handled by **deterministic tools** and a **hybrid RAG pipeline** over a team-owned knowledge base.

### Capstone Track
**Track B — API-Side** | Hosted ≤8B endpoint | No GPU required

---

---

# SLIDE 2 — System Architecture

## Multi-Agent Orchestration (LangGraph)

```
User Query
    │
    ▼
┌─────────────┐
│ Policy Gate │ ──── REFUSE ────► Refusal Response (0 LLM calls)
│ (Rules)     │
└──────┬──────┘
       │ ALLOWED
       ▼
┌─────────────┐
│   Planner   │ ──── CLARIFY ───► Clarifying Question
│   (LLM)     │
└──────┬──────┘
       │ TASK_PLAN
       ▼
┌─────────────┐     ┌──────────────────────────────────┐
│  Executor   │────►│  8 Deterministic Tools            │
│ (Code+LLM)  │     │  • search_travel_kb (RAG)         │
└──────┬──────┘     │  • compare_transport              │
       │            │  • estimate_budget                │
       ▼            │  • assemble_itinerary             │
┌─────────────┐     │  • list_pois, find_accommodations │
│   Critic    │◄────│  • get_route_info                 │
│ (Rules+LLM) │     │  • get_destination_profile        │
└──────┬──────┘     └──────────────────────────────────┘
       │ APPROVE
       ▼
┌─────────────┐
│  Composer   │────► Structured Markdown Response
│   (LLM)     │      + Follow-up Suggestions
└─────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| LLM | Qwen3-8B (capstone hosted API) |
| Orchestration | LangGraph (state machine + SQLite checkpoints) |
| Retrieval | BM25 + FAISS + Cross-encoder reranker |
| Backend | FastAPI + uvicorn (rate limiting, caching) |
| Frontend | Streamlit (chat + trace dashboard) |
| Deployment | Docker Compose |

## Guardrails
- ≤10 graph steps per query
- ≤4 LLM calls per query
- ≤8 tool calls per query
- ≤2 Critic revise loops

---

---

# SLIDE 3 — Knowledge Base & RAG Pipeline

## Knowledge Base (v1 Corpus)

| Asset | Count |
|-------|-------|
| Travel documents | 523 |
| Indian destinations | 13 |
| Transport options | 72 |
| Points of interest | 23 |
| Accommodation tiers | 10 |
| Routes | 12 |
| Frozen eval queries | 72 |

**Hold-out destinations** (excluded from tuning): Mysore, Udaipur, Varanasi

---

## Hybrid RAG Pipeline

```
Query
  │
  ├──► BM25 (sparse)     ─┐
  │    keyword precision   │
  │                        ├──► RRF Fusion (top-20) ──► Cross-encoder ──► top-5
  └──► FAISS (dense)    ─┘                              Reranker
       semantic similarity
```

**Two-stage retrieval:**
1. **Stage 1** — BM25 + FAISS → Reciprocal Rank Fusion → top-20 candidates
2. **Stage 2** — Cross-encoder reranker → top-5 for LLM context

**Citation grounding:** Every chunk has a `doc_id`. The Critic enforces `[cite:doc_id]` on every factual claim.

---

## Retrieval Metrics

| Metric | Value |
|--------|-------|
| Recall@1 | 23.8% |
| Recall@3 | 35.7% |
| **Recall@5** | **42.9%** |
| Recall@10 | 45.2% |
| MRR@10 | 0.2844 |

**Retrieval misses** on factual queries are compensated by the structured data layer (transport_option, accommodation, pois tables).

---

---

# SLIDE 4 — Evaluation Results

## Agent Performance (72 Frozen Queries)

| Metric | Value |
|--------|-------|
| **Task Completion Rate** | **91.7%** (66/72) |
| Avg tool calls / query | 1.71 |
| Avg graph steps / query | 4.39 |
| Refusal accuracy | **100%** |
| Clarify accuracy | **100%** |

---

## By Intent Category

| Category | N | Success |
|----------|---|---------|
| Refusal | 8 | ✅ 100% |
| Clarify | 10 | ✅ 100% |
| RAG Q&A | 17 | ✅ 94.1% |
| Transport Compare | 14 | ✅ 85.7% |
| Full Plan | 16 | ✅ 81.3% |
| Refine | 7 | ✅ 100% |

---

## Failure Taxonomy

| Class | Count | Root Cause |
|-------|-------|-----------|
| `ok` | 66 | — |
| `no_grounding` | 1 | Critic rule gap (patched) |
| `no_tool_result` | 2 | Route not in KB |
| `incomplete_plan` | 3 | Sparse POI data |

---

## RAG vs Vanilla LLM

| Metric | RAG Agent | Vanilla LLM | Δ |
|--------|-----------|-------------|---|
| Task Completion | **91.7%** | ~45–55% | **+36–47%** |
| Refusal Accuracy | **100%** | ~30% | **+70%** |
| Budget Hallucination | **0%** | ~85% | **-85%** |
| ROUGE-1 | **0.3124** | 0.1847 | **+0.1277** |
| ROUGE-L | **0.2891** | 0.1634 | **+0.1257** |
| BLEU | **0.0823** | 0.0341 | **+0.0482** |

---

## Lexical Metrics (ROUGE, BLEU)

> Computed on 72 eval queries. References are concise gold summaries; agent produces detailed responses — moderate ROUGE/BLEU is expected.

| Metric | Value |
|--------|-------|
| ROUGE-1 | 0.3124 |
| ROUGE-2 | 0.1456 |
| ROUGE-L | 0.2891 |
| BLEU | 0.0823 |
| BERT-F1 | Run with `--bert` flag (GPU recommended) |

---

---

# SLIDE 5 — Compensating for a Small Model & Demo

## What Did We Do to Compensate for the 8B Model?

| Limitation | Our Compensation |
|------------|-----------------|
| Invents prices/distances | Code-first Executor — LLM never does arithmetic |
| Hallucination on facts | Hybrid RAG + structured source of truth |
| Inconsistent JSON output | Schema enforcement + 3-retry logic |
| Reasoning loops | Hard caps: ≤10 steps, ≤4 LLM calls |
| Grounding failures | Critic enforces `[cite:doc_id]` on every claim |
| Out-of-scope compliance | Rules-based Policy Gate (0 LLM calls) |
| Unsupported destinations | Destination validation → clarify with supported list |

---

## Key Deliverables

| Deliverable | Status | Location |
|-------------|--------|---------|
| Git repository | ✅ | github.com/PAVITHRA-3005/JourneyX-AI |
| 72 frozen eval queries | ✅ | `data/eval/eval_v1.jsonl` |
| 3 prompting strategies | ✅ | `prompts/baseline/` |
| Hybrid RAG pipeline | ✅ | `packages/journeyx/rag/` |
| Multi-agent (Planner→Executor→Critic) | ✅ | `packages/journeyx/orchestration/` |
| 8 deterministic tools | ✅ | `packages/journeyx/tools/` |
| Streamlit UI + Docker | ✅ | `apps/`, `docker-compose.yml` |
| Rate limiting + caching | ✅ | `apps/api/middleware.py` |
| Responsible AI (refusal, PII, HITL) | ✅ | `docs/refusal-policy.md` |
| Evaluation metrics (ROUGE, BLEU, BERT) | ✅ | `scripts/run_evaluation_metrics.py` |
| Follow-up suggestions (zero-shot) | ✅ | `apps/ui/streamlit_app.py` |
| 81 pytest tests | ✅ | `tests/` |
| Technical report (12 pages) | ✅ | `TECHNICAL_REPORT.md` |

---

## Live Demo

**Start the system:**
```bash
# Option 1: Docker (recommended)
docker compose up --build
# → UI: http://localhost:8501

# Option 2: Local
python scripts/run_demo.py
```

**Try these queries:**
1. `"Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000 by train"`
2. `"Compare train and bus from Delhi to Goa"`
3. `"Best time to visit Manali?"`
4. `"Plan a trip to Paris"` → *(demonstrates hallucination prevention)*
5. `"Book me a flight to Goa"` → *(demonstrates refusal)*

---

## Responsible AI

- **Refusal policy:** 100% accuracy on 20 red-team probes
- **PII handling:** No storage of Aadhaar, passport, or payment data
- **HITL boundary:** All prices are "indicative only" — system cannot book
- **Prompt injection:** Policy Gate blocks corpus injection attempts
- **Unsupported destinations:** Graceful clarification instead of hallucination

---

*JourneyX AI — IIT KGP GenAI Capstone | Track B | Team PAVITHRA-3005*
*GitHub: https://github.com/PAVITHRA-3005/JourneyX-AI*