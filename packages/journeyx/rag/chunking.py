from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from journeyx.core.structured import TravelDocument
from journeyx.rag.models import ChunkRecord

STRUCTURE_SINGLE_TYPES = {
    "destination_guide",
    "poi_card",
    "transport_guide",
    "accommodation_blurb",
    "itinerary_template",
}


def _chunk_id(doc_id: str, part: int) -> str:
    return f"chunk_{doc_id}_{part:03d}"


def chunk_document(
    doc: TravelDocument,
    strategy: str,
    corpus_version: str,
    chunk_size: int = 512,
    overlap: int = 64,
    max_chunk_chars: int = 1200,
) -> list[ChunkRecord]:
    body = doc.body.strip()
    title = doc.title
    doc_type = doc.doc_type

    if strategy == "structure_aware" and doc_type in STRUCTURE_SINGLE_TYPES:
        text = f"{title}\n{body}"[:max_chunk_chars]
        return [
            ChunkRecord(
                chunk_id=_chunk_id(doc.doc_id, 0),
                doc_id=doc.doc_id,
                dest_id=doc.dest_id,
                doc_type=doc_type,
                title=title,
                text=text,
                corpus_version=corpus_version,
            )
        ]

    if strategy == "fixed" or (strategy == "structure_aware" and doc_type not in STRUCTURE_SINGLE_TYPES):
        chunks: list[ChunkRecord] = []
        start = 0
        part = 0
        combined = f"{title}\n{body}"
        while start < len(combined):
            end = min(start + chunk_size, len(combined))
            piece = combined[start:end].strip()
            if piece:
                chunks.append(
                    ChunkRecord(
                        chunk_id=_chunk_id(doc.doc_id, part),
                        doc_id=doc.doc_id,
                        dest_id=doc.dest_id,
                        doc_type=doc_type,
                        title=title,
                        text=piece,
                        corpus_version=corpus_version,
                    )
                )
                part += 1
            if end >= len(combined):
                break
            start = max(end - overlap, start + 1)
        return chunks or [
            ChunkRecord(
                chunk_id=_chunk_id(doc.doc_id, 0),
                doc_id=doc.doc_id,
                dest_id=doc.dest_id,
                doc_type=doc_type,
                title=title,
                text=title,
                corpus_version=corpus_version,
            )
        ]

    raise ValueError(f"Unknown chunking strategy: {strategy}")


def load_documents(path: Path) -> list[TravelDocument]:
    docs: list[TravelDocument] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(TravelDocument.model_validate_json(line))
    return docs


def build_chunks(
    documents: list[TravelDocument],
    strategy: str,
    corpus_version: str,
    chunk_size: int = 512,
    overlap: int = 64,
    max_chunk_chars: int = 1200,
) -> list[ChunkRecord]:
    all_chunks: list[ChunkRecord] = []
    for doc in documents:
        all_chunks.extend(
            chunk_document(doc, strategy, corpus_version, chunk_size, overlap, max_chunk_chars)
        )
    return all_chunks


def chunks_fingerprint(chunks: list[ChunkRecord]) -> str:
    payload = json.dumps([c.model_dump() for c in chunks], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]