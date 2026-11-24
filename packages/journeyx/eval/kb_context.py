"""Static knowledge-base digest for single-agent baseline prompting."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_kb_digest(max_chars: int = 8000) -> str:
    """Load structured + document summaries for baseline context injection."""
    data = _root() / "data"
    lines: list[str] = ["# JourneyX KB digest (indicative)"]

    cities = data / "structured/cities.jsonl"
    if cities.is_file():
        lines.append("\n## Cities (best months)")
        for line in cities.read_text(encoding="utf-8").splitlines()[:15]:
            if line.strip():
                row = json.loads(line)
                lines.append(
                    f"- {row['city_id']}: {row['name']}, best_months={row.get('best_months', [])}"
                )

    docs = data / "documents/documents.jsonl"
    if docs.is_file():
        lines.append("\n## Document excerpts")
        used = 0
        for line in docs.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("doc_type") in ("destination_guide", "poi_card", "transport_guide"):
                excerpt = row["body"][:280].replace("\n", " ")
                lines.append(f"[{row['doc_id']}] {row['title']}: {excerpt}")
                used += 1
                if used >= 25:
                    break

    text = "\n".join(lines)
    return text[:max_chars]