from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.middleware import RateLimitMiddleware, RequestIdMiddleware
from journeyx.config.capstone import get_settings, reload_settings
from journeyx.orchestration.graph import run_turn
from journeyx.rag.cache import clear_retrieval_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("journeyx.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    reload_settings()
    logger.info("JourneyX API started agent_dry_run=%s", os.getenv("JOURNEYX_AGENT_DRY_RUN", "true"))
    yield


app = FastAPI(
    title="JourneyX API",
    version="1.0.0-release",
    description="Indicative travel copilot — planner, executor, and critic",
    lifespan=lifespan,
)

_origins = os.getenv("JOURNEYX_CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None
    conversation_prefix: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    status: str
    thread_id: str
    trace_id: str
    step_count: int
    tool_calls: int
    planner_intent: str | None
    request_id: str | None = None


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


@app.get("/health")
def health() -> dict[str, Any]:
    manifest_path = _root() / "data/manifest.yaml"
    corpus_ok = manifest_path.is_file()
    doc_count = 0
    if corpus_ok:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        doc_count = manifest.get("document_count", 0)
    settings = get_settings()
    return {
        "status": "ok",
        "corpus_documents": doc_count,
        "chat_configured": bool(settings.chat.api_key),
        "embeddings_configured": bool(settings.embeddings.api_key),
        "agent_dry_run": os.getenv("JOURNEYX_AGENT_DRY_RUN", "true"),
        "retrieval_cache": os.getenv("JOURNEYX_DISABLE_RETRIEVAL_CACHE", "false"),
    }


@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> dict[str, Any]:
    start = time.perf_counter()
    out = run_turn(
        req.message,
        thread_id=req.thread_id,
        conversation_prefix=req.conversation_prefix,
    )
    latency_ms = (time.perf_counter() - start) * 1000
    rid = getattr(request.state, "request_id", None)
    logger.info(
        "chat thread=%s status=%s steps=%s tools=%s latency_ms=%.1f rid=%s",
        out.get("thread_id"),
        out.get("status"),
        out.get("step_count"),
        out.get("tool_calls"),
        latency_ms,
        rid,
    )
    return ChatResponse(
        response=out["response"],
        status=out["status"],
        thread_id=out["thread_id"],
        trace_id=out["trace_id"],
        step_count=out["step_count"],
        tool_calls=out["tool_calls"],
        planner_intent=out.get("planner_intent"),
        request_id=rid,
    ).model_dump()


@app.post("/v1/admin/cache/clear")
def clear_cache() -> dict[str, int]:
    """Clear retrieval cache (admin/demo; protect in production with API key)."""
    if os.getenv("JOURNEYX_ALLOW_CACHE_CLEAR", "true").lower() not in ("1", "true", "yes"):
        return {"cleared": 0}
    return {"cleared": clear_retrieval_cache()}