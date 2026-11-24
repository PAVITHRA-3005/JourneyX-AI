from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from journeyx.rag.chunking import build_chunks, chunks_fingerprint, load_documents
from journeyx.rag.dense import DenseIndex
from journeyx.rag.embeddings import EmbeddingsClient, embed_chunks
from journeyx.rag.models import ChunkRecord
from journeyx.rag.sparse import BM25Index


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_rag_config(path: Path | None = None) -> dict[str, Any]:
    path = path or project_root() / "config/rag.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def save_chunks_jsonl(chunks: list[ChunkRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(c.model_dump_json() + "\n")


def load_chunks_jsonl(path: Path) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(ChunkRecord.model_validate_json(line))
    return chunks


def ingest_corpus(
    strategy: str | None = None,
    run_experiment: bool = False,
) -> dict[str, Any]:
    root = project_root()
    cfg = load_rag_config()
    corpus_version = cfg.get("corpus_version", "v1")
    docs_path = root / "data/documents/documents.jsonl"
    index_dir = root / "data/indexes" / corpus_version
    index_dir.mkdir(parents=True, exist_ok=True)

    documents = load_documents(docs_path)
    experiments = cfg["chunking"]["experiments"]
    winner = strategy or cfg["chunking"]["winner"]

    experiment_results: dict[str, Any] = {}
    if run_experiment:
        from journeyx.eval.retrieval_eval import evaluate_strategy

        for exp in experiments:
            name = exp["name"]
            chunks = build_chunks(
                documents,
                exp["strategy"],
                corpus_version,
                chunk_size=exp.get("chunk_size", 512),
                overlap=exp.get("overlap", 64),
                max_chunk_chars=exp.get("max_chunk_chars", 1200),
            )
            metrics = evaluate_strategy(chunks, root)
            experiment_results[name] = metrics
        winner = max(experiment_results, key=lambda k: experiment_results[k]["mrr@10"])

    exp_cfg = next((e for e in experiments if e["name"] == winner), experiments[0])
    chunks = build_chunks(
        documents,
        exp_cfg["strategy"],
        corpus_version,
        chunk_size=exp_cfg.get("chunk_size", 512),
        overlap=exp_cfg.get("overlap", 64),
        max_chunk_chars=exp_cfg.get("max_chunk_chars", 1200),
    )

    chunks_path = index_dir / "chunks.jsonl"
    save_chunks_jsonl(chunks, chunks_path)

    client = EmbeddingsClient()
    vectors = embed_chunks(chunks, client)
    np.save(index_dir / cfg["embeddings"]["cache_file"], vectors)

    bm25 = BM25Index(chunks)
    bm25.save(index_dir / "bm25.pkl")

    dense = DenseIndex(chunks, vectors)
    dense.save(index_dir / "dense", vectors)

    manifest_path = root / "data/manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "chunk_count": len(chunks),
            "chunking_winner": winner,
            "chunking_strategy": exp_cfg["strategy"],
            "chunks_fingerprint": chunks_fingerprint(chunks),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "embedding_fallback": not client.configured,
            "experiment_results": experiment_results,
        }
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    index_dir_rel = index_dir.relative_to(root).as_posix()

    ingest_meta = {
        "corpus_version": corpus_version,
        "chunking_winner": winner,
        "chunk_count": len(chunks),
        "document_count": len(documents),
        "experiment_results": experiment_results,
        "index_dir": index_dir_rel,
    }
    (index_dir / "ingest_report.json").write_text(
        json.dumps(ingest_meta, indent=2), encoding="utf-8"
    )
    return ingest_meta