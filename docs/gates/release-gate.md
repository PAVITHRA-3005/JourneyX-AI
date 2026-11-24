# Release validation gate (Ship + eval + demo)

| Item | Location |
|------|----------|
| Docker Compose | `docker-compose.yml`, `infra/docker/Dockerfile` |
| Streamlit UI | `apps/ui/streamlit_app.py` |
| Rate limit + request ID | `apps/api/middleware.py` |
| Retrieval cache | `packages/journeyx/rag/cache.py` |
| Agent E2E eval | `scripts/run_agent_eval.py` → `reports/agent_eval_v1.json` |
| Red-team log | `scripts/run_redteam.py` → `reports/redteam_log.jsonl` |
| Eval report template | `docs/eval_report.md` |
| Demo script | `docs/DEMO_SCRIPT.md` |

**Validate:** `python scripts/validate_release_gate.py`

## Run stack

```powershell
docker compose up --build
# API http://localhost:8000  UI http://localhost:8501
```

Local (no Docker):

```powershell
$env:PYTHONPATH='packages;apps'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir apps --port 8000
.\.venv\Scripts\python.exe -m streamlit run apps/ui/streamlit_app.py
```