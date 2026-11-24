"""Integration: validation gate scripts exit 0."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

GATE_SCRIPTS = [
    "scripts/validate_data_gate.py",
    "scripts/validate_retrieval_gate.py",
    "scripts/validate_agent_gate.py",
    "scripts/validate_release_gate.py",
]


def test_validation_gate_scripts_pass(project_root: Path) -> None:
    env = {**dict(__import__("os").environ), "PYTHONPATH": str(project_root / "packages")}
    for rel in GATE_SCRIPTS:
        proc = subprocess.run(
            [sys.executable, str(project_root / rel)],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"{rel}\n{proc.stdout}\n{proc.stderr}"