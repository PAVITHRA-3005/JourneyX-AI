from __future__ import annotations

import hashlib
import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

_DEFAULT_TTL_S = float(__import__("os").getenv("JOURNEYX_RETRIEVAL_CACHE_TTL_S", "300"))
_MAX_ENTRIES = 512

_store: dict[str, tuple[float, dict[str, Any]]] = {}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _corpus_fingerprint() -> str:
    manifest = _project_root() / "data/manifest.yaml"
    if not manifest.is_file():
        return "unknown"
    import yaml

    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    return str(data.get("chunks_fingerprint") or data.get("indexed_at") or "v1")


def cache_key(query: str, dest_id: str | None, doc_types: list[str], top_k: int) -> str:
    payload = {
        "q": query.strip().lower(),
        "dest": dest_id,
        "types": sorted(doc_types),
        "k": top_k,
        "corpus": _corpus_fingerprint(),
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(key: str) -> dict[str, Any] | None:
    if __import__("os").getenv("JOURNEYX_DISABLE_RETRIEVAL_CACHE", "").lower() in ("1", "true", "yes"):
        return None
    hit = _store.get(key)
    if not hit:
        return None
    expires, value = hit
    if time.time() > expires:
        _store.pop(key, None)
        return None
    out = dict(value)
    out["cache_hit"] = True
    return out


def set_cached(key: str, value: dict[str, Any], ttl_s: float | None = None) -> None:
    if len(_store) >= _MAX_ENTRIES:
        oldest = min(_store.items(), key=lambda x: x[1][0])
        _store.pop(oldest[0], None)
    ttl = ttl_s if ttl_s is not None else _DEFAULT_TTL_S
    copy = {k: v for k, v in value.items() if k != "cache_hit"}
    _store[key] = (time.time() + ttl, copy)


def clear_retrieval_cache() -> int:
    n = len(_store)
    _store.clear()
    return n