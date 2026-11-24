# Agent validation gate checklist (Track B — template IV)

| Item | Status |
|------|--------|
| LangGraph planner → executor → critic | `packages/journeyx/orchestration/` |
| Persistent checkpoints (SQLite) | `data/checkpoints.sqlite` |
| Step cap ≤10 / tool cap 8 | `orchestration/budgets.py` |
| ≥8 traced internal tools | `packages/journeyx/tools/` + `registry.py` |
| FastAPI chat | `apps/api/main.py` → `POST /v1/chat` |
| Trace spans (planner/executor/critic) | `reports/agent_traces.jsonl` |
| Tests | `tests/test_agent_smoke.py` |

**Validate:** `python scripts/validate_agent_gate.py`

**Env (offline gate / CI):** `JOURNEYX_AGENT_DRY_RUN=true`, `JOURNEYX_EMBEDDING_FALLBACK=true`

**Run API locally:**

```powershell
$env:PYTHONPATH="packages;apps"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir apps --reload
```