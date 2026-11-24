# JourneyX — user guide (setup and execution)

This guide is for **reviewers, graders, and new team members** running the JourneyX deliverable offline or against the hosted capstone APIs.

## What you received

| Path | Purpose |
|------|---------|
| `USER_GUIDE.md` | This document — start here |
| `README.md` | Project overview and doc index |
| `packages/journeyx/` | Core library: schemas, RAG, tools, LangGraph agent |
| `apps/api/` | FastAPI `/v1/chat` and admin endpoints |
| `apps/ui/` | Streamlit chat + trace dashboard |
| `scripts/` | Bootstrap, validation gates, eval, demo console |
| `data/` | Structured tables, document corpus, frozen eval, search indexes |
| `config/` | `credentials.example.yaml`, `rag.yaml` |
| `certs/` | CA certificates for hosted API TLS |
| `prompts/baseline/` | Prompting baseline strategies A/B/C |
| `docs/` | Product spec, gates, RAG pipeline, test matrix |
| `reports/` | Offline evaluation summaries (JSON) |
| `tests/` | Pytest suite (81 tests) |
| `infra/docker/`, `docker-compose.yml` | Containerized API + UI |
| `ProjectIdea.md`, `IMPLEMENTATION_PLAN.md` | Capstone scope and architecture |

**Not included (by design):** virtualenv (`.venv`), secrets (`config/credentials.local.yaml`), runtime SQLite checkpoints, and verbose trace logs. Indexes under `data/indexes/v1/` are **pre-built** so hybrid retrieval works without calling the embedding API first.

## Requirements

- **Python 3.10+** (3.10 recommended; matches development)
- **Windows or Linux/macOS** — commands below use PowerShell; translate paths for bash if needed
- **Optional:** Docker Desktop for `docker compose`
- **Optional (live LLM/embeddings):** VPN + group API keys from the course coordinator

## 1. One-time setup

Open a terminal at the **repository root** (the folder that contains `scripts/`, `packages/`, and `data/`).

### Create the virtual environment

```powershell
cd <path-to-JourneyX>
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_venv.ps1
```

This creates `.venv` in the project folder and installs `requirements.txt` plus the editable `journeyx` package.

### Credentials (live API only)

For **offline demo and CI-style runs**, skip this step. Defaults use heuristic agent + embedding fallback.

For **live** chat and embeddings:

1. Copy `config/credentials.example.yaml` → `config/credentials.local.yaml`
2. Paste your group **chat** and **embeddings** API keys
3. Ensure `certs/vm05-ca.crt` and `certs/vm02-ca.crt` are present (included in deliverable)

See `docs/capstone-api-setup.md` for endpoint details.

### Environment flags (common)

| Variable | Offline (default) | Live |
|----------|-------------------|------|
| `JOURNEYX_AGENT_DRY_RUN` | `true` | `false` |
| `JOURNEYX_EMBEDDING_FALLBACK` | `true` | `false` |
| `JOURNEYX_DISABLE_RERANK` | `true` | optional `false` |
| `JOURNEYX_BASELINE_DRY_RUN` | `true` | `false` |

PowerShell example for live run:

```powershell
$env:JOURNEYX_AGENT_DRY_RUN = "false"
$env:JOURNEYX_EMBEDDING_FALLBACK = "false"
```

## 2. Verify the deliverable

Run all validation gates and tests (uses offline flags automatically in gate scripts):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1
```

Expected: data, retrieval, agent, and release gates exit **0**; retrieval eval and ingest steps succeed.

Full pytest suite:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_test_suite.ps1
```

## 3. How to run JourneyX

### A. Interactive console demo (fastest)

No HTTP server — LangGraph agent in the terminal:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo_console.ps1
```

Commands: `/help`, `/samples`, `/new`, `/quit`. See `docs/DEMO_SCRIPT.md`.

Single query:

```powershell
powershell -File scripts\demo_console.ps1 -m "Compare train vs road Delhi to Jaipur for 2 people"
```

### B. FastAPI + Streamlit (local)

Terminal 1 — API:

```powershell
$env:PYTHONPATH = "$PWD\packages;$PWD\apps"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir apps --host 127.0.0.1 --port 8000
```

Terminal 2 — UI:

```powershell
$env:JOURNEYX_API_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\streamlit run apps\ui\streamlit_app.py
```

Open `http://localhost:8501`. Chat tab for queries; Trace dashboard for planner → executor → critic spans.

### C. Docker Compose

```powershell
copy config\credentials.example.yaml config\credentials.local.yaml
# edit keys if using live APIs
docker compose up --build
```

API: `http://localhost:8000` · UI: `http://localhost:8501`

Compose mounts `config/credentials.local.yaml` and creates `data/checkpoints.sqlite` on first run for multi-turn persistence.

## 4. Rebuild indexes (optional)

Pre-built indexes are shipped under `data/indexes/v1/`. To rebuild after corpus changes:

```powershell
.\.venv\Scripts\python.exe scripts\ingest_corpus.py
.\.venv\Scripts\python.exe scripts\run_retrieval_eval.py
```

With live embeddings, set `JOURNEYX_EMBEDDING_FALLBACK=false` before ingest. See `docs/rag-pipeline.md`.

## 5. Evaluation and reports

| Script | Output |
|--------|--------|
| `scripts/run_baseline.py` | `reports/baseline_results.json` |
| `scripts/run_retrieval_eval.py` | `reports/retrieval_eval_v1.json` |
| `scripts/run_agent_eval.py` | `reports/agent_eval_v1.json` |
| `scripts/run_redteam.py` | security probe log under `reports/` |

Shipped copies of key JSON files are in `reports/` for offline review.

## 6. Architecture (30-second orientation)

1. **Planner** — intent, slots, task list (LLM or heuristic in dry-run)
2. **Executor** — deterministic tools: KB search, transport, budget, itinerary
3. **Critic** — grounding and completeness checks; bounded **≤10** graph steps

Hybrid **BM25 + FAISS** retrieval with fusion; structured **source of truth** for fares and stays. Full narrative: `docs/COMPLETE_SYSTEM_EXPLAINED.md` and `docs/IDEA_AND_AGENT_FLOW.md`.

## 7. Gate checklists

| Layer | Document |
|-------|----------|
| Data & eval | `docs/gates/data-gate.md` |
| Retrieval | `docs/gates/retrieval-gate.md` |
| Agent | `docs/gates/agent-gate.md` |
| Release | `docs/gates/release-gate.md` |

## 8. Troubleshooting

| Issue | Action |
|-------|--------|
| `Capstone virtualenv not found` | Run `scripts\bootstrap_venv.ps1` |
| SSL errors to API | Confirm CA paths in `credentials.local.yaml` |
| Empty RAG results | Confirm `data/indexes/v1/chunks.jsonl` exists; rerun `ingest_corpus.py` |
| Rate limit (HTTP 429) | Default 60 rpm per IP; wait or adjust `JOURNEYX_RATE_LIMIT_RPM` |
| Tests slow on first run | Session fixture runs one corpus ingest |

## 9. Support contacts

Use your **course coordinator** for API keys, VPN, and quota. For codebase questions, see `docs/TEST_SUITE.md` and module docstrings under `packages/journeyx/`.

---

*JourneyX — indicative travel planning copilot. All prices and itineraries are for planning only; not booking or payment.*