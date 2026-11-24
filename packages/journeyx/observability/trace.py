from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

NodeName = Literal[
    "baseline",
    "planner",
    "executor",
    "critic",
    "policy",
    "composer",
]


@dataclass
class TraceSpan:
    trace_id: str
    thread_id: str
    corpus_version: str
    prompt_version: str
    node: NodeName
    step_index: int
    latency_ms: float
    tokens_in: int | None = None
    tokens_out: int | None = None
    tool_name: str | None = None
    status: Literal["ok", "error", "degraded"] = "ok"
    error_class: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TraceWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def new_trace_id(self) -> str:
        return str(uuid.uuid4())

    def write(self, span: TraceSpan) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(span), ensure_ascii=False) + "\n")