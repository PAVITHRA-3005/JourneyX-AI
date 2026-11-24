#!/usr/bin/env python3
"""Interactive JourneyX console demo — LangGraph agent, no HTTP server."""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
import uuid

from journeyx.orchestration.graph import run_turn

BANNER = """
JourneyX — interactive console demo (planner → executor → critic)
Type a travel question and press Enter. Commands start with /
"""

SAMPLE_PROMPTS = [
    "Book a flight Delhi to Goa on my credit card",
    "Compare train vs road diesel Delhi to Jaipur for 2 people",
    "What are the best months to visit Jaipur?",
    "Plan a 3 day trip to Jaipur from Delhi for 2 travellers",
]


def _status_line() -> str:
    dry = os.getenv("JOURNEYX_AGENT_DRY_RUN", "true")
    emb = os.getenv("JOURNEYX_EMBEDDING_FALLBACK", "true")
    return f"agent_dry_run={dry}  embedding_fallback={emb}"


def _print_help() -> None:
    print(
        textwrap.dedent(
            """
            Commands:
              /help     — this message
              /quit     — exit (also /exit)
              /new      — new conversation thread (checkpoint)
              /thread   — show current thread_id
              /status   — show demo environment flags
              /demo     — print sample prompts you can try
              /samples  — run the four built-in sample prompts once

            Tips:
              - Same thread keeps LangGraph checkpoint state (use /new to reset).
              - Offline default: heuristic planner + local embedding fallback.
              - Live LLM: set JOURNEYX_AGENT_DRY_RUN=false before starting.
            """
        ).strip()
    )


def _render_turn(out: dict) -> None:
    print("-" * 60)
    print(f"status={out.get('status')}  steps={out.get('step_count')}  tools={out.get('tool_calls')}", end="")
    intent = out.get("planner_intent")
    if intent:
        print(f"  intent={intent}", end="")
    print()
    print(f"trace_id={out.get('trace_id')}")
    response = (out.get("response") or "").strip()
    if response:
        print()
        for line in response.splitlines():
            print(textwrap.fill(line, width=76, subsequent_indent="  ") if line else "")
    else:
        print("(empty response)")
    print("-" * 60)


def _run_samples(thread_id: str) -> tuple[str, int]:
    """Run built-in samples; return final thread_id and count."""
    n = 0
    for msg in SAMPLE_PROMPTS:
        print(f"\n>>> SAMPLE: {msg}")
        out = run_turn(msg, thread_id=thread_id)
        thread_id = out["thread_id"]
        _render_turn(out)
        n += 1
    return thread_id, n


def interactive_loop(thread_id: str | None) -> int:
    thread_id = thread_id or str(uuid.uuid4())
    print(BANNER.strip())
    print(_status_line())
    print(f"thread_id={thread_id}")
    print("/help for commands\n")

    while True:
        try:
            line = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if not line:
            continue

        lower = line.lower()
        if lower in {"/quit", "/exit", "/q"}:
            print("Bye.")
            return 0
        if lower == "/help":
            _print_help()
            continue
        if lower == "/new":
            thread_id = str(uuid.uuid4())
            print(f"New thread_id={thread_id}")
            continue
        if lower == "/thread":
            print(f"thread_id={thread_id}")
            continue
        if lower == "/status":
            print(_status_line())
            continue
        if lower == "/demo":
            for i, p in enumerate(SAMPLE_PROMPTS, 1):
                print(f"  {i}. {p}")
            continue
        if lower == "/samples":
            thread_id, _ = _run_samples(thread_id)
            continue
        if line.startswith("/"):
            print("Unknown command. Try /help")
            continue

        try:
            out = run_turn(line, thread_id=thread_id)
        except Exception as exc:
            print(f"Error: {exc}")
            continue
        thread_id = out["thread_id"]
        print("\nAssistant>")
        _render_turn(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="JourneyX interactive console demo")
    parser.add_argument(
        "-m",
        "--message",
        help="Single turn then exit (non-interactive)",
    )
    parser.add_argument(
        "--samples",
        action="store_true",
        help="Run built-in sample prompts then exit",
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="Optional thread id for checkpoint continuity",
    )
    args = parser.parse_args()

    if args.samples:
        thread_id = args.thread_id or str(uuid.uuid4())
        print(_status_line())
        _run_samples(thread_id)
        return 0

    if args.message:
        out = run_turn(args.message, thread_id=args.thread_id)
        print("\nAssistant>")
        _render_turn(out)
        return 0

    return interactive_loop(args.thread_id)


if __name__ == "__main__":
    sys.exit(main())