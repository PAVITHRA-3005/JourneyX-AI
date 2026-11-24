#!/usr/bin/env python3
"""Smoke-test chat + embeddings using config/credentials.local.yaml."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

import httpx

from journeyx.config.capstone import get_settings, mask_key, reload_settings
from journeyx.llm.client import ChatMessage, LLMClient
from journeyx.rag.embeddings import EmbeddingsClient


def main() -> int:
    # Live API smoke tests; overrides offline dry-run environment variables.
    os.environ["JOURNEYX_BASELINE_DRY_RUN"] = "false"
    os.environ["JOURNEYX_EMBEDDING_FALLBACK"] = "false"
    reload_settings()
    s = get_settings()
    errors: list[str] = []

    if not s.chat.api_key:
        errors.append("chat.api_key missing in credentials.local.yaml")
    if not s.embeddings.api_key:
        errors.append("embeddings.api_key missing")

    print("Chat:", s.chat.api_base, mask_key(s.chat.api_key), s.chat.ca_cert)
    print("Emb:", s.embeddings.api_base, mask_key(s.embeddings.api_key), s.embeddings.ca_cert)

    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1

    emb = EmbeddingsClient()
    vecs = emb.embed_texts(["Test query for JourneyX", "Jaipur travel"])
    print(f"Embeddings: shape={vecs.shape}")

    llm = LLMClient()
    print("LLM configured:", llm.configured, "dry_run:", llm.dry_run)
    resp = llm.chat(
        [ChatMessage(role="user", content="Reply with one word: ok")],
        max_tokens=16,
    )
    print("Chat:", (resp.content or "")[:200], "latency_ms=", resp.latency_ms)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except httpx.HTTPError as exc:
        print("CONNECTIVITY_ERROR:", exc)
        print("Hint: Capstone VMs (103.42.50.41) need campus network or IITKGP VPN.")
        raise SystemExit(1) from exc