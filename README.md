# JourneyX AI — India Travel Planning Copilot

**Multi-Agent Travel Planning Copilot** built entirely on a hosted ≤8B LLM (Qwen3-8B), with no fine-tuning and no frontier models.

> **IIT KGP Executive PGP in Generative AI & Agentic AI | Track B (API-Side) | Team PAVITHRA-3005**

---

## 🚀 How to Run (Quick Launch)

### Prerequisites
- Python 3.10+
- Windows (PowerShell) or macOS/Linux

### Step 1 — Clone & set up the virtual environment

```powershell
# Windows (PowerShell)
cd JourneyX
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_venv.ps1
```

```bash
# macOS / Linux
cd JourneyX
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2 — Configure credentials

```powershell
# Copy the template (no real keys needed for dry-run / demo mode)
copy config\credentials.local.yaml.example config\credentials.local.yaml
copy .env.example .env
```

### Step 3 — Launch the Streamlit UI

**Windows (one-click):**
```powershell
powershell -ExecutionPolicy Bypass -File run_local.ps1
```

**Manual launch (any OS):**
```bash
# Set environment variables for demo mode (no API key needed)
export JOURNEYX_AGENT_DRY_RUN=true
export JOURNEYX_EMBEDDING_FALLBACK=true
export JOURNEYX_DISABLE_RERANK=true
export JOURNEYX_UI_USE_API=false

# Run Streamlit
cd JourneyX
.venv/bin/python -m streamlit run apps/ui/streamlit_app.py --server.port 8501
```

**Windows PowerShell manual:**
```powershell
$env:JOURNEYX_AGENT_DRY_RUN="true"
$env:JOURNEYX_EMBEDDING_FALLBACK="true"
$env:JOURNEYX_DISABLE_RERANK="true"
$env:JOURNEYX_UI_USE_API="false"
.\.venv\Scripts\python.exe -m streamlit run apps\ui\streamlit_app.py --server.port 8501
```

### Step 4 — Open in browser

```
http://localhost:8501
```

---

## 💬 What to Try in the UI

Once the app is open, try these queries in the chat box:

| Query | What it does |
|-------|-------------|
| `Plan 3 days in Jaipur from Delhi` | Full trip plan with itinerary, transport, stays, budget |
| `Plan 4 days in Goa` | Asks for departure city, then generates full plan |
| `Compare train and bus from Delhi to Goa` | Transport comparison table |
| `5 days in Manali for 2 people` | Multi-person trip plan |
| `What is the best time to visit Kochi?` | RAG Q&A from knowledge base |
| `What are the top attractions in Jaipur?` | RAG Q&A — POI visitor cards |
| `Budget trip to Manali from Delhi` | Budget-focused plan |

**Supported destinations:** Delhi, Jaipur, Goa, Manali, Kochi, Bengaluru, Mumbai, Shimla, Rishikesh, Agra, Mysore, Udaipur, Varanasi

---

## 🐳 Docker (Alternative)

```bash
# Build and run with Docker Compose
docker compose up --build
# UI: http://localhost:8501  |  API: http://localhost:8000
```

---

## What It Does

JourneyX is a conversational travel planning assistant for Indian destinations:

- 🗺️ **Full trip planning** — day-wise itinerary, transport, accommodation, budget
- 🚆 **Transport comparison** — train vs bus vs flight vs road (from structured KB)
- 💰 **Budget estimation** — deterministic calculation, no LLM arithmetic
- ❓ **Destination Q&A** — grounded in hybrid RAG (BM25 + FAISS + reranker)
- 🔄 **Multi-turn refinement** — persistent state across conversation turns
- 🛡️ **Responsible AI** — 100% refusal accuracy on bookings, PII, unsafe requests
- 💡 **Follow-up suggestions** — zero-shot suggestions after each answer

---

## Key Results

| Metric | Value |
|--------|-------|
| Task completion rate | **91.7%** (66/72 queries) |
| Refusal accuracy | **100%** |
| Retrieval Recall@5 | 42.9% |
| ROUGE-1 (RAG vs Vanilla) | 0.3124 vs 0.1847 |
| BLEU (RAG vs Vanilla) | 0.0823 vs 0.0341 |
| Avg graph steps / query | 4.39 |

---

## Repository Layout

```text
JourneyX/
├── apps/ui/streamlit_app.py     # Streamlit chat UI
├── packages/journeyx/           # Core agent, LLM client, tools, RAG
│   ├── orchestration/           # LangGraph nodes (planner, executor, critic, composer)
│   ├── tools/                   # search_kb, discovery, transport, budget tools
│   └── llm/                     # LLM client (Qwen3-8B via OpenAI-compatible API)
├── data/
│   ├── structured/              # Accommodations, POIs, transport routes (JSONL)
│   ├── documents/               # KB corpus (destination guides, visitor cards)
│   └── eval/                    # 72 evaluation questions with gold answers
├── scripts/                     # Seed, validate, baseline, evaluation runners
├── config/                      # credentials.local.yaml.example (template)
├── prompts/                     # Prompting strategies A/B/C
├── docs/                        # Technical docs, eval reports, agent flow
├── run_local.ps1                # One-click Windows launcher
├── requirements.txt             # Python dependencies
└── docker-compose.yml           # Docker deployment
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [USER_GUIDE.md](USER_GUIDE.md) | Setup, run, and verify |
| [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) | 12-page technical report |
| [PRESENTATION_SLIDES.md](PRESENTATION_SLIDES.md) | 4-5 slide presentation deck |
| [docs/eval_report.md](docs/eval_report.md) | Full evaluation report |
| [SUBMISSION_COVER.md](SUBMISSION_COVER.md) | Submission cover sheet |

---

## Evaluation

```bash
# Run full evaluation (dry-run, no LLM needed)
python scripts/run_evaluation_metrics.py --dry-run --topk

# Run with live LLM + RAG vs Vanilla comparison
python scripts/run_evaluation_metrics.py --topk --vanilla

# Run BERT score (GPU recommended)
python scripts/run_evaluation_metrics.py --bert --dry-run
```

---

## Security

- API keys are stored in `.env` and `config/credentials.local.yaml` — both are in `.gitignore`
- Use `config/credentials.local.yaml.example` as a template (no real keys)
- **Never commit `.env` or `credentials.local.yaml` to version control**

---

## Status

| Layer | Capability | Gate |
|-------|------------|------|
| Data & eval | Schemas, frozen eval, baseline runner | **PASSED** |
| Retrieval | Hybrid RAG + 8 tools | **PASSED** |
| Agent | LangGraph + FastAPI | **PASSED** |
| Release | Streamlit, Docker, rate limit, cache | **PASSED** |