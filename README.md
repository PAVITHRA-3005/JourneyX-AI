# JourneyX AI (Track B Capstone)

Intelligent travel planning copilot using hosted ≤8B LLM, owned knowledge base, and multi-agent orchestration.

## Documentation

| Doc | Purpose |
|-----|---------|
| [USER_GUIDE.md](USER_GUIDE.md) | **Setup, run, and verify (deliverable)** |
| [ProjectIdea.md](ProjectIdea.md) | Executive summary |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Full build & capstone compliance |
| [docs/IDEA_AND_AGENT_FLOW.md](docs/IDEA_AND_AGENT_FLOW.md) | Agents & E2E flow |
| [docs/COMPLETE_SYSTEM_EXPLAINED.md](docs/COMPLETE_SYSTEM_EXPLAINED.md) | **Learn every part** (detailed walkthrough) |
| [docs/gates/data-gate.md](docs/gates/data-gate.md) | Data & eval validation checklist |

## Repository root

All commands assume your **current directory** is the repo root (the folder containing `scripts/`, `packages/`, and `data/`). Scripts under `scripts/` discover the root automatically via `scripts/lib/CapstoneVenv.ps1` — no fixed install path required.

## Python environment (required)

Use a virtualenv **inside this repo only** — never system `C:\Python*`.

```powershell
# From the repository root (folder containing scripts/, packages/, data/)
cd <path-to-repo>
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_venv.ps1
.\.venv\Scripts\Activate.ps1   # optional; IDE uses .venv automatically
```

Run Python without activating:

```powershell
.\.venv\Scripts\python.exe scripts\validate_data_gate.py
.\scripts\capstone-python.ps1 scripts\validate_data_gate.py
powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1
```

Legacy fallback: `.venv-review` if `.venv` is absent (`scripts/lib/CapstoneVenv.ps1`).

## Quick start (data & baseline)

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/seed_eval_data.py
python scripts/validate_data_gate.py
copy .env.example .env
python scripts/run_baseline.py --limit 30
```

## Repository layout

```text
packages/journeyx/   # core schemas, LLM client, baseline eval, traces
data/                # manifest, structured tables, documents, eval
scripts/             # seed, validate, baseline runner
prompts/baseline/    # prompting strategies A/B/C
docs/                # product spec, refusal, schemas, tools
```

## Retrieval (RAG)

```bash
python scripts/ingest_corpus.py
python scripts/run_retrieval_eval.py
python scripts/validate_retrieval_gate.py
```

See [docs/rag-pipeline.md](docs/rag-pipeline.md) and [docs/gates/retrieval-gate.md](docs/gates/retrieval-gate.md).

## Status

| Layer | Capability | Gate |
|-------|------------|------|
| Data & eval | Schemas, frozen eval, baseline runner | [data-gate.md](docs/gates/data-gate.md) **PASSED** (live baseline optional on VPN) |
| Retrieval | Hybrid RAG + 8 tools | [retrieval-gate.md](docs/gates/retrieval-gate.md) **PASSED** |
| Agent | LangGraph + FastAPI | [agent-gate.md](docs/gates/agent-gate.md) **PASSED** |
| Release | Streamlit, Docker, rate limit, cache, agent eval | [release-gate.md](docs/gates/release-gate.md) **done** |

**Verify everything:** `powershell -File scripts/verify_all.ps1`  
**Use-case tests:** `powershell -File scripts/run_test_suite.ps1` — see [docs/TEST_SUITE.md](docs/TEST_SUITE.md)  
**Interactive console demo:** `powershell -File scripts/demo_console.ps1` — see [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)