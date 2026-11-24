#!/usr/bin/env python3
"""Run injection/PII probes; append log for responsible-AI review."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from journeyx.security.redteam import PII_PROBES, run_redteam

OUT = ROOT / "reports/redteam_log.jsonl"


def main() -> int:
    results = run_redteam()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with OUT.open("a", encoding="utf-8") as f:
        for r in results:
            row = {"timestamp": ts, "probe": r.probe, "status": r.status, "refused": r.refused}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    refused = sum(1 for r in results if r.refused)
    print(f"Probes={len(results)} refused={refused} log={OUT}")
    for r in results:
        if r.probe in PII_PROBES and not r.refused:
            return 1
    return 0