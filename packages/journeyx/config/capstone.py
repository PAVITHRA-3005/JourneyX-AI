from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(raw: str | None) -> str | None:
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = project_root() / p
    return str(p.resolve())


class EndpointSettings(BaseModel):
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    ca_cert: str | None = None
    max_tokens: int = 512
    timeout_s: float = 120.0
    embed_batch_size: int = 16

    @property
    def verify(self) -> bool | str:
        if self.ca_cert:
            resolved = _resolve_path(self.ca_cert)
            if resolved and Path(resolved).is_file():
                return resolved
        return True


class CapstoneSettings(BaseModel):
    chat: EndpointSettings = Field(default_factory=EndpointSettings)
    embeddings: EndpointSettings = Field(default_factory=EndpointSettings)


def _merge_endpoint(data: dict[str, Any] | None, prefix: str) -> dict[str, Any]:
    if not data:
        data = {}
    env_map = {
        "api_base": os.getenv(f"CAPSTONE_{prefix}_API_BASE") or os.getenv(
            "CAPSTONE_API_BASE" if prefix == "CHAT" else "CAPSTONE_EMBEDDINGS_API_BASE", ""
        ),
        "api_key": os.getenv(f"CAPSTONE_{prefix}_API_KEY") or os.getenv(
            "CAPSTONE_API_KEY" if prefix == "CHAT" else "CAPSTONE_EMBEDDINGS_API_KEY", ""
        ),
        "model": os.getenv(f"CAPSTONE_{prefix}_MODEL") or os.getenv(
            "CAPSTONE_MODEL" if prefix == "CHAT" else "CAPSTONE_EMBEDDING_MODEL", ""
        ),
        "ca_cert": os.getenv(f"CAPSTONE_{prefix}_CA_CERT"),
    }
    merged = {**data}
    for key, val in env_map.items():
        if val:
            merged[key] = val
    return merged


def load_credentials_file(path: Path | None = None) -> dict[str, Any]:
    path = path or project_root() / "config" / "credentials.local.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def get_settings() -> CapstoneSettings:
    load_dotenv(project_root() / ".env")
    raw = load_credentials_file()
    chat = _merge_endpoint(raw.get("chat"), "CHAT")
    emb = _merge_endpoint(raw.get("embeddings"), "EMBEDDINGS")
    return CapstoneSettings(
        chat=EndpointSettings(
            api_base=chat.get("api_base", ""),
            api_key=chat.get("api_key", ""),
            model=chat.get("model", "Qwen/Qwen3-8B"),
            ca_cert=chat.get("ca_cert"),
            max_tokens=int(chat.get("max_tokens", 512)),
            timeout_s=float(chat.get("timeout_s", 120)),
        ),
        embeddings=EndpointSettings(
            api_base=emb.get("api_base", ""),
            api_key=emb.get("api_key", ""),
            model=emb.get("model", "bge-small-en-v1.5"),
            ca_cert=emb.get("ca_cert"),
            timeout_s=float(emb.get("timeout_s", 120)),
            embed_batch_size=int(emb.get("embed_batch_size", 16)),
        ),
    )


def reload_settings() -> CapstoneSettings:
    get_settings.cache_clear()
    return get_settings()


def build_http_client(endpoint: EndpointSettings) -> httpx.Client:
    return httpx.Client(timeout=endpoint.timeout_s, verify=endpoint.verify)


def mask_key(key: str) -> str:
    if len(key) < 8:
        return "***"
    return f"{key[:4]}…{key[-4:]}"