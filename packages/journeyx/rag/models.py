from __future__ import annotations

from pydantic import BaseModel, Field


class ChunkRecord(BaseModel):
    chunk_id: str
    doc_id: str
    dest_id: str
    doc_type: str
    title: str
    text: str
    corpus_version: str = "v1"


class SearchRequest(BaseModel):
    query: str
    dest_id: str | None = None
    doc_types: list[str] = Field(default_factory=list)
    top_k: int = 5


class RetrievalHit(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    doc_type: str
    dest_id: str
    excerpt: str
    score: float
    citation_id: str

    @property
    def cite_marker(self) -> str:
        return f"[cite:{self.doc_id}]"