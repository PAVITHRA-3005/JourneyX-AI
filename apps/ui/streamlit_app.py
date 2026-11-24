"""JourneyX Streamlit UI — chat + trace dashboard."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "apps"))

API_URL = os.getenv("JOURNEYX_API_URL", "http://127.0.0.1:8000").rstrip("/")
TRACE_PATH = ROOT / "reports" / "agent_traces.jsonl"

st.set_page_config(
    page_title="JourneyX AI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f2e 0%, #0f1117 100%);
        border-right: 1px solid #2d3748;
    }

    /* Title area */
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background-color: #1e2433;
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border: 1px solid #2d3748;
    }

    /* User message */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #1a2744;
        border-left: 3px solid #667eea;
    }

    /* ── STICKY CHAT INPUT (ChatGPT-style) ── */
    /* Fix the entire chat input container to the bottom */
    [data-testid="stBottom"] {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 999 !important;
        background: linear-gradient(0deg, #0f1117 70%, transparent 100%) !important;
        padding: 1rem 1rem 1.2rem 1rem !important;
        backdrop-filter: blur(10px) !important;
    }

    /* The actual input box */
    [data-testid="stChatInput"] {
        max-width: 800px !important;
        margin: 0 auto !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #2d3748 !important;
        border: 2px solid #4a5568 !important;
        border-radius: 16px !important;
        color: #e2e8f0 !important;
        font-size: 1rem !important;
        padding: 0.9rem 3.5rem 0.9rem 1.2rem !important;
        min-height: 52px !important;
        max-height: 200px !important;
        resize: none !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4) !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }

    [data-testid="stChatInput"] textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.25), 0 4px 24px rgba(0,0,0,0.4) !important;
        outline: none !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #718096 !important;
    }

    /* Send button */
    [data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border-radius: 10px !important;
        border: none !important;
        color: white !important;
        width: 36px !important;
        height: 36px !important;
        right: 10px !important;
        bottom: 8px !important;
    }

    [data-testid="stChatInput"] button:hover {
        opacity: 0.85 !important;
        transform: scale(1.05) !important;
    }

    /* Add bottom padding to main content so messages don't hide behind input */
    .main .block-container {
        padding-bottom: 120px !important;
    }

    /* New conversation button */
    .new-conv-btn button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        width: 100% !important;
        padding: 0.5rem !important;
    }

    /* Status badge */
    .status-ok { color: #48bb78; font-weight: 600; }
    .status-refuse { color: #fc8181; font-weight: 600; }
    .status-clarify { color: #f6ad55; font-weight: 600; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #1e2433;
        border-radius: 8px;
        padding: 0.5rem;
        border: 1px solid #2d3748;
    }

    /* Tabs */
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-weight: 600;
    }

    /* Spinner */
    .stSpinner > div { border-top-color: #667eea !important; }

    /* Caption / metadata */
    .response-meta {
        font-size: 0.75rem;
        color: #718096;
        margin-top: 0.3rem;
        padding: 0.3rem 0.5rem;
        background: #161b27;
        border-radius: 6px;
        border-left: 2px solid #4a5568;
    }

    /* Scroll to bottom helper */
    .chat-scroll-anchor { height: 20px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_count" not in st.session_state:
    st.session_state.conversation_count = 1
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0

# ── API helpers ──────────────────────────────────────────────────────────────
def _chat_via_api(message: str) -> dict:
    payload = {
        "message": message,
        "thread_id": st.session_state.thread_id,
        "conversation_prefix": [
            m for m in st.session_state.messages
            if m["role"] in ("user", "assistant")
        ],
    }
    r = requests.post(f"{API_URL}/v1/chat", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def _chat_local(message: str) -> dict:
    from journeyx.orchestration.graph import run_turn

    out = run_turn(
        message,
        thread_id=st.session_state.thread_id,
        conversation_prefix=st.session_state.messages,
    )
    st.session_state.thread_id = out["thread_id"]
    return out


# ── Check API availability ───────────────────────────────────────────────────
use_api = os.getenv("JOURNEYX_UI_USE_API", "auto").lower()
api_ok = False
if use_api in ("auto", "true", "1", "yes"):
    try:
        requests.get(f"{API_URL}/health", timeout=3)
        api_ok = True
    except requests.RequestException:
        api_ok = False

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧭 JourneyX AI")
    st.markdown("*AI-powered travel planning for India*")
    st.divider()

    # New Conversation button
    st.markdown('<div class="new-conv-btn">', unsafe_allow_html=True)
    if st.button("✨ New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.session_state.conversation_count += 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # Conversation stats
    st.markdown("### 📊 Session Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Messages", len(st.session_state.messages))
    with col2:
        st.metric("Queries", st.session_state.total_queries)

    st.metric("Conversation #", st.session_state.conversation_count)

    st.divider()

    # Backend status
    st.markdown("### ⚙️ Backend")
    if api_ok:
        st.success("✅ FastAPI connected")
    else:
        st.warning("⚡ Local mode (in-process)")

    dry_run = os.getenv("JOURNEYX_AGENT_DRY_RUN", "true")
    if dry_run.lower() in ("1", "true", "yes"):
        st.info("🔧 DRY_RUN=true (heuristic planner)")
    else:
        st.success("🤖 LLM planner active")

    st.divider()

    # Quick examples
    st.markdown("### 💡 Try these")
    examples = [
        "Plan 3 days in Jaipur from Delhi",
        "Compare train and bus Delhi to Goa",
        "Best time to visit Manali?",
        "Budget trip to Kerala for 2 people",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state._example_query = ex
            st.rerun()

    st.divider()
    st.caption("⚠️ All plans are indicative. Verify before booking.")

# ── Main tabs ────────────────────────────────────────────────────────────────
tab_chat, tab_traces, tab_health = st.tabs(["💬 Chat", "📈 Trace Dashboard", "🔧 System Health"])

with tab_chat:
    # Header
    st.markdown('<p class="main-title">🧭 JourneyX AI</p>', unsafe_allow_html=True)
    st.caption("Indicative travel plans for India · Powered by RAG + LangGraph agents · Verify before booking")

    # Conversation header
    if st.session_state.messages:
        msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        st.markdown(
            f'<div class="response-meta">Conversation #{st.session_state.conversation_count} · '
            f'{msg_count} question{"s" if msg_count != 1 else ""} asked</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")
    else:
        # Welcome message when no conversation
        st.markdown("""
        <div style="text-align:center; padding: 3rem 1rem; color: #718096;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🗺️</div>
            <h3 style="color: #a0aec0; margin-bottom: 0.5rem;">Plan your next India trip</h3>
            <p style="font-size: 0.9rem;">Ask about destinations, transport, itineraries, or budgets.<br>
            Try the examples in the sidebar to get started!</p>
        </div>
        """, unsafe_allow_html=True)

    # Display conversation history — ALL messages render here, ABOVE the chat input
    for msg in st.session_state.messages:
        if msg["role"] in ("user", "assistant"):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("meta"):
                    st.markdown(
                        f'<div class="response-meta">{msg["meta"]}</div>',
                        unsafe_allow_html=True,
                    )

    # Show spinner while waiting for response (before rerun)
    if st.session_state.get("_waiting"):
        with st.chat_message("assistant"):
            with st.spinner("🗺️ Planning your trip…"):
                try:
                    pending = st.session_state.pop("_waiting")
                    if api_ok and use_api != "false":
                        data = _chat_via_api(pending)
                    else:
                        data = _chat_local(pending)

                    answer = data.get("response", "")
                    status = data.get("status", "ok")
                    steps = data.get("step_count", 0)
                    tools = data.get("tool_calls", 0)
                    intent = data.get("planner_intent", "—")

                    status_class = {
                        "ok": "status-ok",
                        "refuse": "status-refuse",
                        "clarify": "status-clarify",
                    }.get(status, "status-ok")

                    meta_html = (
                        f'<span class="{status_class}">●</span> {status} · '
                        f'intent: {intent} · steps: {steps} · tools: {tools} · '
                        f'{datetime.now().strftime("%H:%M:%S")}'
                    )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "meta": meta_html,
                    })

                    if data.get("thread_id"):
                        st.session_state.thread_id = data["thread_id"]

                except Exception as exc:  # noqa: BLE001
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ Request failed: {exc}\n\n💡 Make sure the API server is running.",
                        "meta": "",
                    })
                st.rerun()

    # Scroll anchor
    st.markdown('<div class="chat-scroll-anchor"></div>', unsafe_allow_html=True)

    # Handle example query from sidebar
    example_query = st.session_state.pop("_example_query", None)

    # ── Chat input — always at the bottom ──
    prompt = st.chat_input("Ask about trips, transport, or destinations…") or example_query

    if prompt:
        st.session_state.total_queries += 1
        # Add user message to history immediately
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Store pending query — will be processed on next rerun (above the input)
        st.session_state["_waiting"] = prompt
        st.rerun()

with tab_traces:
    st.subheader("📈 Agent Trace Dashboard")
    st.caption("Real-time view of agent steps, tool calls, and latencies")

    if not TRACE_PATH.is_file():
        st.info("💬 No traces yet. Run a chat query first to see agent traces here.")
    else:
        lines = [ln for ln in TRACE_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()][-200:]
        rows = [json.loads(ln) for ln in lines]

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Spans", len(rows))
        with col2:
            avg_lat = sum(r.get("latency_ms", 0) for r in rows) / max(len(rows), 1)
            st.metric("Avg Latency", f"{avg_lat:.0f}ms")
        with col3:
            errors = sum(1 for r in rows if r.get("status") == "error")
            st.metric("Errors", errors)
        with col4:
            nodes_count = len({r.get("node") for r in rows})
            st.metric("Node Types", nodes_count)

        st.divider()

        nodes = sorted({r.get("node") for r in rows})
        pick = st.multiselect("Filter by node", nodes, default=nodes)
        filtered = [r for r in rows if r.get("node") in pick]
        st.dataframe(filtered, use_container_width=True)
        st.caption(f"Showing {len(filtered)} of {len(rows)} spans")

with tab_health:
    st.subheader("🔧 System Health")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**API Status**")
        try:
            if api_ok:
                h = requests.get(f"{API_URL}/health", timeout=5).json()
                st.success("✅ API is healthy")
                st.json(h)
            else:
                st.warning("⚡ API unreachable — using local in-process mode")
                st.json({"mode": "local", "corpus": str((ROOT / "data/manifest.yaml").is_file())})
        except requests.RequestException as e:
            st.error(f"API error: {e}")

    with col2:
        st.markdown("**Environment**")
        env_info = {
            "JOURNEYX_AGENT_DRY_RUN": os.getenv("JOURNEYX_AGENT_DRY_RUN", "true"),
            "JOURNEYX_API_URL": API_URL,
            "data/manifest.yaml": str((ROOT / "data/manifest.yaml").is_file()),
            "reports/agent_traces.jsonl": str(TRACE_PATH.is_file()),
        }
        st.json(env_info)