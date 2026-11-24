#!/usr/bin/env python3
"""Copy CA certs and scaffold config/credentials.local.yaml."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERTS = ROOT / "certs"
LOCAL = ROOT / "config" / "credentials.local.yaml"
EXAMPLE = ROOT / "config" / "credentials.example.yaml"
EMB_KEY_FILE = ROOT / "VM02_Embeddings_Access" / "shared-embedding-key.txt"


def main() -> None:
    CERTS.mkdir(parents=True, exist_ok=True)
    pairs = [
        (ROOT / "vm05-ca.crt", CERTS / "vm05-ca.crt"),
        (ROOT / "VM02_Embeddings_Access" / "vm02-ca.crt", CERTS / "vm02-ca.crt"),
    ]
    for src, dst in pairs:
        if src.is_file():
            shutil.copy2(src, dst)
            print(f"Copied {src.name} -> {dst.relative_to(ROOT)}")
        else:
            print(f"WARN: missing {src}")

    emb_key = ""
    if EMB_KEY_FILE.is_file():
        emb_key = EMB_KEY_FILE.read_text(encoding="utf-8").strip()

    if LOCAL.is_file():
        print(f"Exists: {LOCAL.relative_to(ROOT)} (not overwritten)")
        return

    if not EXAMPLE.is_file():
        raise SystemExit("Missing credentials.example.yaml")

    text = EXAMPLE.read_text(encoding="utf-8")
    if emb_key and "YOUR_EMBEDDINGS_API_KEY" in text:
        text = text.replace("YOUR_EMBEDDINGS_API_KEY", emb_key)
    LOCAL.write_text(
        text
        + "\n# Chat api_key: set YOUR_GROUP_CHAT_API_KEY in this file after copying.\n",
        encoding="utf-8",
    )
    print(f"Created {LOCAL.relative_to(ROOT)} — set chat api_key and verify group URL.")


if __name__ == "__main__":
    main()