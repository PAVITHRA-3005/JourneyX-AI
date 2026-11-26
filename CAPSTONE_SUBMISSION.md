# JourneyX AI — Capstone Project Submission

**Course:** Executive Post Graduate Programme in Generative AI and Agentic AI  
**Track:** B — API-Side Multi-Agent Copilot (Hosted ≤8B Inference API)  
**Project Title:** Multi-Agent Operations Copilot — JourneyX AI Travel Planning Assistant  
**Student:** Pavithra V  
**Team:** Suresh Huse, Prabhakar Raturi, Srivishwa T, Pradeep Bastia, Pavithra V  
**Submission Date:** November 27, 2026

---

## 📦 DELIVERABLE 1 — Google Drive Folder (All Files)

> **All submission files are uploaded here. This is the primary access point.**

**🔗 Google Drive Folder Link:**
```
[PASTE YOUR GOOGLE DRIVE LINK HERE]
```

### Files in the Google Drive Folder:

| # | File / Folder | Description |
|---|---------------|-------------|
| 1 | `TECHNICAL_REPORT.pdf` | 12-page technical report — architecture, evaluation, results |
| 2 | `JourneyX AI — Capstone Presentation.pptx` | 5-slide presentation deck summarizing the project |
| 3 | `JourneyX-AI-Demo.mp4` | **Demo video** — 10-minute walkthrough of the live system |
| 4 | `JourneyX-AI-main.zip` | Complete source code (downloaded from GitHub) |
| 5 | `JourneyX-AI_Github_link.txt` | GitHub repository URLs for reference |
| 6 | `JourneyX AI - Evaluation Results/` | **Folder containing all evaluation reports** |

### 📊 Evaluation Results Folder Contents:

| File | What It Contains |
|------|-----------------|
| `agent_eval_v1.json` | Task completion rate (91.7%), per-category breakdown, failure taxonomy |
| `baseline_results.json` | ROUGE-1/2/L, BLEU scores — RAG Agent vs Vanilla LLM comparison |
| `retrieval_eval_v1.json` | Top-K retrieval metrics: Recall@1, Recall@3, Recall@5, Recall@10, MRR@10 |
| `eval_report.md` | Human-readable evaluation summary (open in any text editor or browser) |

---

## 🔗 DELIVERABLE 2 — GitHub Repositories

### Repository 1: Source Code (Main Project)

**🔗 URL:** https://github.com/PAVITHRA-3005/JourneyX-AI

**How to access evaluation reports in this repo:**
```
https://github.com/PAVITHRA-3005/JourneyX-AI/tree/main/reports
```

**Direct file links:**
- Agent Evaluation: https://github.com/PAVITHRA-3005/JourneyX-AI/blob/main/reports/agent_eval_v1.json
- Baseline/ROUGE/BLEU: https://github.com/PAVITHRA-3005/JourneyX-AI/blob/main/reports/baseline_results.json
- Retrieval Metrics: https://github.com/PAVITHRA-3005/JourneyX-AI/blob/main/reports/retrieval_eval_v1.json
- Evaluation Report: https://github.com/PAVITHRA-3005/JourneyX-AI/blob/main/docs/eval_report.md
- Technical Report: https://github.com/PAVITHRA-3005/JourneyX-AI/blob/main/TECHNICAL_REPORT.pdf

**Download source code ZIP directly:**
```
https://github.com/PAVITHRA-3005/JourneyX-AI/archive/refs/heads/main.zip
```

### Repository 2: Submission Deliverables

**🔗 URL:** https://github.com/PAVITHRA-3005/Project_submission

> All submission files (same as Google Drive) are also available here.  
> To download: Click **"Code"** → **"Download ZIP"**

---

## 🎬 DELIVERABLE 3 — Demo Video

**Location:** Google Drive folder → `JourneyX-AI-Demo.mp4`

**What the video demonstrates:**
1. Full trip planning query: "Plan 3 days in Jaipur from Delhi for 2 people under ₹20,000"
2. Structured itinerary output with day-wise breakdown
3. Transport comparison with real prices
4. Accommodation suggestions with booking links
5. Budget breakdown
6. RAG Q&A: "What's the best time to visit Goa?" — with citations
7. Refusal handling: "Book a flight on my credit card" — instant policy gate
8. Trace Dashboard showing agent execution (Planner → Executor → Critic → Composer)
9. Follow-up question suggestions

---

## 📄 DELIVERABLE 4 — Technical Report

**Location:** Google Drive folder → `TECHNICAL_REPORT.pdf`  
**Also available at:** https://github.com/PAVITHRA-3005/JourneyX-AI/blob/main/TECHNICAL_REPORT.pdf

**Report Sections:**
1. Abstract
2. Introduction & Motivation
3. System Architecture (5-layer diagram)
4. Knowledge Base & Corpus Statistics (523 documents, 13 destinations)
5. Hybrid RAG Pipeline (BM25 + FAISS + Cross-Encoder Reranker)
6. Multi-Agent Orchestration (Planner → Executor → Critic → Composer)
7. Evaluation Results (ROUGE, BLEU, Top-K, RAG vs Vanilla, Failure Taxonomy)
8. Compensating for Small Model Limitations
9. Deployment (Docker, FastAPI, Streamlit)
10. Responsible AI (Refusal Policy, PII Handling, Prompt Injection Tests)
11. Conclusion
12. Capstone Requirement Traceability (24 requirements — all ✅)

---

## 📊 DELIVERABLE 5 — Evaluation Report

**Location:** Google Drive folder → `JourneyX AI - Evaluation Results/`  
**Also available at:** https://github.com/PAVITHRA-3005/JourneyX-AI/tree/main/reports

### Key Results Summary:

#### Agent Evaluation (72 frozen queries):

| Metric | Value |
|--------|-------|
| **Task Completion Rate** | **91.7%** (66/72 queries) |
| Average tool calls per query | 1.71 |
| Average graph steps per query | 4.39 (budget: 10) |

#### By Intent Category:

| Category | Queries | Success Rate |
|----------|---------|--------------|
| Refusal | 8 | 100% |
| Clarify | 10 | 100% |
| RAG Q&A | 17 | 94.1% |
| Transport Compare | 14 | 85.7% |
| Full Plan | 16 | 81.3% |
| Refine | 7 | 100% |

#### Failure Taxonomy:

| Class | Count | Description |
|-------|-------|-------------|
| `ok` | 66 | Task completed successfully |
| `no_grounding` | 1 | Factual claim without citation |
| `no_tool_result` | 2 | Route not in knowledge base |
| `incomplete_plan` | 3 | Full plan missing itinerary days |

#### Lexical Metrics — RAG Agent vs Vanilla LLM:

| Metric | RAG Agent | Vanilla LLM | Improvement |
|--------|-----------|-------------|-------------|
| ROUGE-1 | 0.3124 | 0.1847 | **+69.1%** ✅ |
| ROUGE-2 | 0.1456 | 0.0612 | **+137.9%** ✅ |
| ROUGE-L | 0.2891 | 0.1634 | **+76.9%** ✅ |
| BLEU | 0.0823 | 0.0341 | **+141.3%** ✅ |

#### Top-K Retrieval Metrics:

| Metric | Value |
|--------|-------|
| Recall@1 | 23.8% |
| Recall@3 | 35.7% |
| Recall@5 | **42.9%** (production K) |
| Recall@10 | 45.2% |
| MRR@10 | 0.2844 |

---

## 🖥️ DELIVERABLE 6 — Presentation Slides

**Location:** Google Drive folder → `JourneyX AI — Capstone Presentation.pptx`

**5 Slides:**
1. Problem & Solution — Why JourneyX AI?
2. System Architecture — Multi-agent orchestration diagram
3. Knowledge Base & RAG Pipeline — Hybrid retrieval metrics
4. Evaluation Results — Task completion, ROUGE/BLEU, RAG vs Vanilla
5. Compensating for Small Model & Demo Queries

---

## 💻 DELIVERABLE 7 — Source Code

**Location:** Google Drive folder → `JourneyX-AI-main.zip`  
**GitHub:** https://github.com/PAVITHRA-3005/JourneyX-AI

**How to run locally:**
```powershell
# 1. Clone the repository
git clone https://github.com/PAVITHRA-3005/JourneyX-AI.git
cd JourneyX-AI

# 2. Set up environment
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure API key
copy config\credentials.local.yaml.example config\credentials.local.yaml
# Edit credentials.local.yaml and add your API key

# 4. Run the app
streamlit run apps\ui\streamlit_app.py
# Open http://localhost:8501
```

---

## ✅ CAPSTONE TRACK B REQUIREMENTS — ALL COMPLETED

| Requirement | Status | Where to Find |
|-------------|--------|---------------|
| Task specification + refusal policy | ✅ | GitHub: `docs/product-spec.md` |
| 60–100 frozen eval queries with gold answers | ✅ 72 queries | GitHub: `data/eval/eval_v1.jsonl` |
| ≥3 prompting strategies compared | ✅ 3 strategies (A, B, C) | GitHub: `prompts/baseline/` |
| RAG over 500–2000 documents | ✅ 523 docs | GitHub: `data/` |
| Hybrid BM25 + dense retrieval | ✅ | GitHub: `packages/journeyx/rag/` |
| Cross-encoder reranker | ✅ | GitHub: `rag/rerank.py` |
| Citation-grounded answers | ✅ | Critic enforces `[cite:doc_id]` |
| Recall@K measured separately | ✅ Recall@5=42.9% | Google Drive: `retrieval_eval_v1.json` |
| Top-K comparison (K=1,3,5) | ✅ | Google Drive: `retrieval_eval_v1.json` |
| ROUGE + BLEU lexical metrics | ✅ | Google Drive: `baseline_results.json` |
| RAG vs Vanilla LLM comparison | ✅ +69% ROUGE-1 | Google Drive: `baseline_results.json` |
| ≥3 tools | ✅ 8 tools | GitHub: `packages/journeyx/tools/` |
| Planner → Executor → Critic loop | ✅ | GitHub: `orchestration/graph.py` |
| Persistent state (multi-turn) | ✅ SQLite | GitHub: `orchestration/` |
| ≤10 steps per query | ✅ Avg 4.39 | Google Drive: `agent_eval_v1.json` |
| E2E evaluation + failure taxonomy | ✅ 91.7% | Google Drive: `agent_eval_v1.json` |
| Follow-up suggestions (zero-shot) | ✅ | GitHub: `apps/ui/streamlit_app.py` |
| Streamlit front-end | ✅ | GitHub: `apps/ui/` |
| Docker containerised | ✅ | GitHub: `docker-compose.yml` |
| Rate limiting + caching | ✅ 60 rpm | GitHub: `apps/api/middleware.py` |
| Responsible AI (refusal, PII, HITL) | ✅ | GitHub: `docs/refusal-policy.md` |
| Trace dashboard | ✅ | Streamlit → Trace Dashboard tab |
| 12-page technical report | ✅ | Google Drive: `TECHNICAL_REPORT.pdf` |
| 4–5 slide presentation | ✅ | Google Drive: `Capstone Presentation.pptx` |

---

## 📞 Contact

**GitHub:** https://github.com/PAVITHRA-3005/JourneyX-AI  
**Submission Repo:** https://github.com/PAVITHRA-3005/Project_submission  
**Track:** B — API-Side Multi-Agent Copilot on Hosted ≤8B LLM (Qwen3-8B)

---

*JourneyX AI — Indicative travel planning copilot. All prices and itineraries are for planning purposes only; not for booking or payment.*