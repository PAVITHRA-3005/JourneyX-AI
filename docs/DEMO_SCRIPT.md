# JourneyX — 10-minute demo script

## Console demo (interactive, no server)

```powershell
# Repository root = folder with scripts/, packages/, data/
cd <path-to-repo>
powershell -ExecutionPolicy Bypass -File scripts\demo_console.ps1
```

Type travel questions at the `You>` prompt. Built-ins: `/help`, `/samples`, `/new`, `/quit`.  
Single message: `powershell -File scripts\demo_console.ps1 -m "Compare Delhi to Jaipur transport for 2"`.  
Batch tour: `powershell -File scripts\demo_console.ps1 --samples`.

## Setup (before audience)

1. VPN if required for live LLM (`JOURNEYX_AGENT_DRY_RUN=false`).
2. `docker compose up --build` **or** FastAPI + Streamlit locally.
3. Open UI `http://localhost:8501` and **Trace dashboard** tab.

## Flow (~10 min)

| Min | Action | What to say |
|-----|--------|-------------|
| 0–1 | Show architecture slide | Planner → Executor → Critic; owned KB; no booking APIs |
| 1–2 | **Refusal** | "Book a flight on my credit card" → policy refuse + HITL disclaimer |
| 2–4 | **Transport** | Delhi–Jaipur compare for 2 → indicative modes incl. road_diesel |
| 4–5 | **RAG** | "Best months to visit Jaipur?" → KB line with citation |
| 5–7 | **Full plan** | "3 day Jaipur from Delhi for 2" → itinerary + budget lines |
| 7–8 | **Traces** tab | Filter `executor` — show tool spans |
| 8–9 | `reports/agent_eval_v1.json` | Task completion + failure taxonomy |
| 9–10 | Limits | ≤10 steps, rate limit, retrieval cache by corpus fingerprint |

## Backup (offline)

Set `JOURNEYX_AGENT_DRY_RUN=true` — heuristic planner; same graph and tools.