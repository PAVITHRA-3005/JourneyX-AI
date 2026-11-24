from __future__ import annotations

import logging
import os

from journeyx.rag.models import ChunkRecord

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        self.enabled = os.getenv("JOURNEYX_DISABLE_RERANK", "").lower() not in ("1", "true")

    def _load(self) -> None:
        if self._model is not None or not self.enabled:
            return
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reranker disabled: %s", exc)
            self.enabled = False

    def rerank(
        self, query: str, chunks: list[ChunkRecord], scores: list[float], top_k: int
    ) -> list[tuple[ChunkRecord, float]]:
        if not chunks:
            return []
        self._load()
        if not self.enabled or self._model is None:
            paired = list(zip(chunks, scores, strict=False))
            paired.sort(key=lambda x: x[1], reverse=True)
            return [(c, s) for c, s in paired[:top_k]]

        pairs = [[query, f"{c.title}\n{c.text}"] for c in chunks]
        rerank_scores = self._model.predict(pairs)
        paired = list(zip(chunks, [float(s) for s in rerank_scores], strict=False))
        paired.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in paired[:top_k]]