"""Shared pytest fixtures: offline API defaults and corpus index build."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def offline_capstone_env() -> None:
    os.environ["JOURNEYX_EMBEDDING_FALLBACK"] = "true"
    os.environ["JOURNEYX_DISABLE_RERANK"] = "true"
    os.environ["JOURNEYX_AGENT_DRY_RUN"] = "true"
    os.environ["JOURNEYX_BASELINE_DRY_RUN"] = "true"


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="session", autouse=True)
def ensure_corpus_index(offline_capstone_env: None, project_root: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(project_root / "packages")}
    subprocess.run(
        [sys.executable, str(project_root / "scripts/ingest_corpus.py")],
        cwd=project_root,
        env=env,
        check=True,
    )
    from journeyx.rag.retrieve import load_retriever

    load_retriever.cache_clear()