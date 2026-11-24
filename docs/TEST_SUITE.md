# JourneyX test suite (full system)

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_test_suite.ps1
```

Or:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

**Environment:** Tests force offline-safe flags (embedding fallback, agent dry-run, no live Capstone APIs).

## Layout

| File | Coverage |
|------|----------|
| `conftest.py` | Session ingest + env |
| `test_eval_gate.py` | Eval/manifest smoke |
| `test_usecases_foundation.py` | Docs, eval categories, schemas, baseline dry-run, traces |
| `test_rag_smoke.py` | KB citations, transport, retrieval eval |
| `test_usecases_retrieval.py` | All 8 tools, registry, index artifacts |
| `test_agent_smoke.py` | Agent transport, refusal, budget determinism |
| `test_usecases_agent.py` | Parametrized agent scenarios + FastAPI TestClient |
| `test_platform_smoke.py` | Docker/UI smoke, cache, API headers, redteam |
| `test_usecases_platform.py` | Cache hit, health/chat/admin API, agent eval, safety refusals |
| `test_integration_gates.py` | `validate_*_gate.py` subprocess (data → release) |

## Use-case matrix (Agent parametrized)

Refusal (booking/PII), transport compare, RAG seasons, full plan, budget, route, KB discovery — see `AGENT_USE_CASES` in `test_usecases_agent.py`.

## Release / platform coverage (`test_usecases_platform.py` + `test_platform_smoke.py`)

- Ship artifacts (Docker, Streamlit, eval/redteam scripts, docs)
- Retrieval cache: hit on repeat, dest-scoped keys, admin clear
- FastAPI: `/health` corpus count, `/v1/chat` trace fields, `/v1/admin/cache/clear`
- Rate-limit middleware RPM config
- Agent eval: `summarize` / `_classify`, `run_agent_eval.py --limit 8`
- Safety refusals (medical, illegal, live-price jailbreak) + redteam PII/injection
- Graph singleton and `step_count` / spans alignment

**Current total:** 81 tests (offline-safe via `conftest.py`).