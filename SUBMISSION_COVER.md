# JourneyX AI — Capstone Submission Cover Document

**Course:** IIT KGP GenAI Capstone  
**Track:** B — API-Side Multi-Agent Copilot  
**Team:** PAVITHRA-3005  
**Submission Date:** November 2026

---

## Project Overview

**JourneyX AI** is a conversational travel planning copilot that helps users discover destinations, compare transport options, estimate budgets, and build day-wise itineraries — all through natural chat, grounded in a team-owned knowledge base, using a hosted ≤8B language model (Qwen3-8B).

---

## Deliverable 1 — Git Repository with Full Agent Stack

| Item | Details |
|---|---|
| **GitHub URL** | https://github.com/PAVITHRA-3005/JourneyX-AI |
| **Branch** | `main` |
| **Total files** | 135 |
| **Setup instructions** | See `USER_GUIDE.md` in the repository |
| **Quick start** | `powershell -File scripts\bootstrap_venv.ps1` then `powershell -File scripts\verify_all.ps1` |
| **Docker start** | `docker compose up --build` → UI at http://localhost:8501 |

### What the repository contains:

| Component | Location | Description |
|---|---|---|
| Core agent library | `packages/journeyx/` | 43 Python files: config, core, eval, llm, observability, orchestration, rag, security, tools |
| Multi-agent orchestration | `packages/journeyx/orchestration/` | LangGraph graph, Planner/Executor/Critic nodes, state, budgets |
| 8 deterministic tools | `packages/journeyx/tools/` | compare_transport, estimate_budget, search_travel_kb, list_pois, find_accommodations, assemble_itinerary, get_route_info, get_destination_profile |
| Hybrid RAG pipeline | `packages/journeyx/rag/` | BM25 + FAISS + cross-encoder reranker |
| FastAPI backend | `apps/api/` | Rate limiting, caching, `/v1/chat` endpoint |
| Streamlit UI | `apps/ui/streamlit_app.py` | Chat tab + Trace Dashboard tab |
| Travel knowledge base | `data/` | 523 documents, 7 structured tables, 72 eval queries |
| Validation scripts | `scripts/` | 20+ scripts for bootstrap, validation, eval, demo |
| Test suite | `tests/` | 81 pytest tests (smoke, integration, use-case) |
| Documentation | `docs/`, `*.md` | Product spec, gates, RAG pipeline, test matrix, user guide |
| Docker deployment | `docker-compose.yml`, `infra/` | Containerized API + UI |
| Evaluation reports | `reports/` | agent_eval_v1.json, retrieval_eval_v1.json |

### Verification commands (for graders):
```powershell
# Clone and setup
git clone https://github.com/PAVITHRA-3005/JourneyX-AI.git
cd JourneyX-AI
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_venv.ps1

# Verify all 4 gates pass
powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1

# Run 81 tests
powershell -ExecutionPolicy Bypass -File scripts\run_test_suite.ps1

# Interactive demo (no server needed)
powershell -ExecutionPolicy Bypass -File scripts\demo_console.ps1
```

---

## Deliverable 2 — Trace Dashboard Showing Real Query Execution

| Item | Details |
|---|---|
| **Location** | Streamlit UI → "Trace Dashboard" tab |
| **URL (when running)** | http://localhost:8501 |
| **How to access** | Start the system, execute queries in Chat tab, switch to Trace Dashboard tab |

### How to generate real traces:

**Option A — Docker (recommended):**
```powershell
docker compose up --build
# Open http://localhost:8501
# Type a query in Chat tab (e.g., "Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000")
# Switch to Trace Dashboard tab to see real execution
```

**Option B — Local:**
```powershell
# Terminal 1
$env:PYTHONPATH = "$PWD\packages;$PWD\apps"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir apps --host 127.0.0.1 --port 8000

# Terminal 2
$env:JOURNEYX_API_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\streamlit run apps\ui\streamlit_app.py
```

### What the trace dashboard shows:
- **Node spans:** planner, executor, critic, composer — with input/output summaries and latency
- **Tool calls within executor:** compare_transport, search_travel_kb, estimate_budget, etc.
- **Step count** per query (should be ≤10)
- **Status:** ok / refuse / clarify / partial
- **Filtering** by node type, intent category, and status

### Recommended demo queries for trace generation:
```
1. "Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000"
   → Shows full pipeline: Planner → Executor (5 tools) → Critic → Composer

2. "Compare Delhi to Jaipur transport for 2 people"
   → Shows Executor calling compare_transport tool

3. "Book a flight on my credit card"
   → Shows Policy Gate refusal (0 LLM calls, 2 steps)
```

---

## Deliverable 3 — Evaluation Report Including Failure Taxonomy

| Item | Location |
|---|---|
| **Primary evaluation report** | `docs/eval_report.md` in the repository |
| **Agent evaluation data** | `reports/agent_eval_v1.json` |
| **Retrieval evaluation data** | `reports/retrieval_eval_v1.json` |
| **Evaluation metrics script** | `scripts/run_evaluation_metrics.py` |
| **Evaluation metrics output** | `reports/evaluation_metrics.json` |
| **Baseline comparison** | `docs/baseline_results_summary.md` |
| **Prompting strategies** | `prompts/baseline/` (strategy_a, strategy_b, strategy_c) |

### Key evaluation results:

**Agent Evaluation (72 frozen queries):**

| Metric | Value |
|---|---|
| Task completion rate | **91.7%** (66/72) |
| Average tool calls per query | 1.71 |
| Average graph steps per query | 4.39 |

**By intent category:**

| Category | N | Success Rate |
|---|---|---|
| Refusal | 8 | 100% |
| Clarify | 10 | 100% |
| RAG Q&A | 17 | 94.1% |
| Transport compare | 14 | 85.7% |
| Full plan | 16 | 81.3% |
| Refine | 7 | 100% |

**Failure Taxonomy:**

| Failure Class | Count | Description |
|---|---|---|
| `ok` | 66 | Task completed successfully |
| `no_grounding` | 1 | Factual claim without citation |
| `no_tool_result` | 2 | Route not in knowledge base |
| `incomplete_plan` | 3 | Full plan missing itinerary days |

**Retrieval Evaluation (38 labeled queries):**

| Metric | Value |
|---|---|
| Recall@1 | 23.8% |
| Recall@3 | 35.7% |
| Recall@5 | **42.9%** |
| Recall@10 | 45.2% |
| MRR@10 | 0.2844 |

**Lexical Metrics (ROUGE, BLEU) — RAG vs Vanilla LLM:**

| Metric | RAG Agent | Vanilla LLM | Improvement |
|--------|-----------|-------------|-------------|
| ROUGE-1 | 0.3124 | 0.1847 | +0.1277 ✅ |
| ROUGE-2 | 0.1456 | 0.0612 | +0.0844 ✅ |
| ROUGE-L | 0.2891 | 0.1634 | +0.1257 ✅ |
| BLEU | 0.0823 | 0.0341 | +0.0482 ✅ |

**Run evaluation:**
```bash
pip install rouge-score nltk bert-score
python scripts/run_evaluation_metrics.py --dry-run --topk
python scripts/run_evaluation_metrics.py --topk --vanilla   # requires live LLM
python scripts/run_evaluation_metrics.py --bert --dry-run   # requires GPU
```

---

## Deliverable 4 — 12-Page Technical Report

| Item | Details |
|---|---|
| **File** | `TECHNICAL_REPORT.md` in the repository |
| **PDF version** | Convert `TECHNICAL_REPORT.md` to PDF using Pandoc or Word |
| **Sections** | Abstract, Introduction, Architecture, Knowledge Base, RAG, Multi-Agent Orchestration, Evaluation (incl. ROUGE/BLEU/BERT/RAG-vs-Vanilla), Compensating for Small Models, Deployment, Results, Responsible AI, Conclusion, References, Appendices |

### To convert to PDF:
```bash
# Using Pandoc (if installed)
pandoc TECHNICAL_REPORT.md -o TECHNICAL_REPORT.pdf --pdf-engine=xelatex

# Or open in VS Code → right-click → "Open Preview" → Print to PDF
# Or copy content into Word and export as PDF
```

---

## Deliverable 5 — Presentation Deck (4–5 Slides)

| Item | Details |
|---|---|
| **File** | `PRESENTATION_SLIDES.md` in the repository |
| **Slides** | 5 slides: Problem & Solution, Architecture, Knowledge Base & RAG, Evaluation Results, Compensating for Small Model & Demo |
| **PDF version** | Convert `PRESENTATION_SLIDES.md` to PDF or import into Google Slides / PowerPoint |

### Slide summary:
1. **Slide 1** — Problem (fragmented trip planning) + Solution (JourneyX architecture)
2. **Slide 2** — Multi-agent orchestration diagram + technology stack
3. **Slide 3** — Knowledge base corpus + hybrid RAG pipeline + retrieval metrics
4. **Slide 4** — Evaluation results (task completion, ROUGE/BLEU, RAG vs Vanilla LLM)
5. **Slide 5** — Compensating for 8B model + deliverables checklist + demo queries

---

## Capstone Requirement Traceability Summary

| Requirement | Status | Evidence |
|---|---|---|
| Foundation: task spec + refusal policy | ✅ | `docs/product-spec.md`, `docs/refusal-policy.md` |
| 60–100 frozen eval queries with gold answers | ✅ 72 queries | `data/eval/eval_v1.jsonl` |
| ≥3 prompting strategies compared | ✅ 3 strategies | `prompts/baseline/` A, B, C |
| RAG 500–2000 documents | ✅ 523 docs | `data/manifest.yaml` |
| Hybrid BM25 + dense retrieval | ✅ | `packages/journeyx/rag/` |
| Reranker | ✅ Cross-encoder | `rag/rerank.py` |
| Citation-grounded answers | ✅ | Critic enforces `[cite:doc_id]` |
| Recall@K separate from E2E | ✅ Recall@5=42.9% | `reports/retrieval_eval_v1.json` |
| Top-K retrieval comparison (K=1,3,5) | ✅ | `scripts/run_evaluation_metrics.py --topk` |
| ROUGE + BLEU lexical metrics | ✅ | `scripts/run_evaluation_metrics.py` |
| BERT score semantic metric | ✅ | `scripts/run_evaluation_metrics.py --bert` |
| RAG vs Vanilla LLM comparison | ✅ | `scripts/run_evaluation_metrics.py --vanilla` |
| ≥3 tools | ✅ 8 tools | `packages/journeyx/tools/` |
| Planner → Executor → Critic | ✅ | `orchestration/graph.py` |
| Persistent state (multi-turn) | ✅ | SQLite checkpoints |
| ≤10 steps/query | ✅ Avg 4.39 | `orchestration/budgets.py` |
| E2E eval + failure taxonomy | ✅ 91.7% | `reports/agent_eval_v1.json` |
| Follow-up suggestions (zero-shot) | ✅ | `apps/ui/streamlit_app.py` |
| Destination validation (no hallucination) | ✅ | `orchestration/nodes.py` |
| Document source reference links | ✅ | `tools/search_kb.py` |
| Streamlit UI | ✅ | `apps/ui/streamlit_app.py` |
| Docker | ✅ | `docker-compose.yml` |
| Rate limiting + caching | ✅ 60 rpm | `apps/api/middleware.py` |
| Responsible AI (refusal, PII, HITL) | ✅ | `docs/refusal-policy.md` |
| Git repository | ✅ | https://github.com/PAVITHRA-3005/JourneyX-AI |
| Trace dashboard | ✅ | Streamlit Trace Dashboard tab |
| Evaluation report + failure taxonomy | ✅ | `docs/eval_report.md` + `reports/*.json` |
| 12-page technical report | ✅ | `TECHNICAL_REPORT.md` |
| 4–5 slide presentation deck | ✅ | `PRESENTATION_SLIDES.md` |
| API keys removed from repository | ✅ | `.env` + `credentials.local.yaml` in `.gitignore` |

---

## Additional Documentation

| Document | Purpose |
|---|---|
| `USER_GUIDE.md` | Step-by-step setup and run instructions for graders |
| `IMPLEMENTATION_PLAN.md` | Full capstone compliance traceability (666 lines) |
| `PRESENTATION_AND_RUNBOOK.md` | System flow, run options, 10-minute demo script |
| `PRESENTATION_SLIDES.md` | **4–5 slide presentation deck** |
| `MENTOR_PRESENTATION.md` | Narrative walkthrough for mentor/panel presentation |
| `TECHNICAL_REPORT.md` | 12-page technical report |
| `docs/eval_report.md` | **Full evaluation report (ROUGE, BLEU, BERT, RAG vs Vanilla)** |
| `docs/COMPLETE_SYSTEM_EXPLAINED.md` | Detailed walkthrough of every component |
| `docs/IDEA_AND_AGENT_FLOW.md` | Agent flow with Mermaid diagrams |
| `docs/gates/` | All 4 validation gate checklists (PASSED) |
| `scripts/run_evaluation_metrics.py` | **Evaluation metrics script (ROUGE, BLEU, BERT, Top-K, Vanilla)** |
| `config/credentials.local.yaml.example` | Credentials template (no real keys) |

---

## Contact

**GitHub:** https://github.com/PAVITHRA-3005/JourneyX-AI  
**Team:** PAVITHRA-3005  
**Track:** B — API-Side Multi-Agent Copilot on Hosted ≤8B LLM

---

*JourneyX — indicative travel planning copilot. All prices and itineraries are for planning only; not booking or payment.*