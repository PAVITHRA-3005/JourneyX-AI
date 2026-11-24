from __future__ import annotations

import hashlib
import os
import time
from typing import Sequence

import httpx
import numpy as np

from journeyx.config.capstone import build_http_client, get_settings
from journeyx.rag.models import ChunkRecord


class EmbeddingsClient:
    """Hosted embeddings API client with CA trust and request batching."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        settings = get_settings().embeddings
        self.base_url = (base_url or settings.api_base).rstrip("/")
        self.api_key = api_key or settings.api_key
        self.model = model or settings.model
        self.timeout_s = timeout_s or settings.timeout_s
        self.batch_size = settings.embed_batch_size
        self.fallback = os.getenv("JOURNEYX_EMBEDDING_FALLBACK", "").lower() in ("1", "true", "yes")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key) and not self.fallback

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        if self.configured:
            return self._embed_api(texts)
        return self._embed_fallback(texts)

    def _embed_api(self, texts: Sequence[str]) -> np.ndarray:
        base = self.base_url
        if not base.endswith("/v1"):
            pass
        url = f"{base}/embeddings" if base.endswith("/v1") else f"{base}/v1/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        vectors: list[list[float]] = []
        settings = get_settings().embeddings

        max_attempts = 5
        with build_http_client(settings) as client:
            for i in range(0, len(texts), self.batch_size):
                batch = list(texts[i : i + self.batch_size])
                payload = {"model": self.model, "input": batch}
                for attempt in range(max_attempts):
                    try:
                        resp = client.post(url, json=payload, headers=headers)
                        if resp.status_code in (429, 503) and attempt < max_attempts - 1:
                            time.sleep(min(30, 2 ** (attempt + 1)))
                            continue
                        resp.raise_for_status()
                        break
                    except (httpx.HTTPError, httpx.ConnectError):
                        if attempt >= max_attempts - 1:
                            raise
                        time.sleep(min(30, 2 ** (attempt + 1)))
                else:
                    raise RuntimeError("embedding batch failed after retries")
                time.sleep(0.25)
                data = resp.json()["data"]
                data.sort(key=lambda x: x["index"])
                vectors.extend([row["embedding"] for row in data])
        arr = np.array(vectors, dtype=np.float32)
        return _l2_normalize(arr)

    def _embed_fallback(self, texts: Sequence[str]) -> np.ndarray:
        dim = 384
        out = np.zeros((len(texts), dim), dtype=np.float32)
        for i, text in enumerate(texts):
            seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(dim).astype(np.float32)
            out[i] = vec / (np.linalg.norm(vec) + 1e-9)
        return out


def embed_chunks(
    chunks: list[ChunkRecord],
    client: EmbeddingsClient,
) -> np.ndarray:
    texts = [f"{c.title}\n{c.text}" for c in chunks]
    return client.embed_texts(texts)


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-9)
    return matrix / norms