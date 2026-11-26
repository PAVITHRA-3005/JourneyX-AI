"""JourneyX Streamlit UI — chat + trace dashboard."""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "apps"))

API_URL = os.getenv("JOURNEYX_API_URL", "http://127.0.0.1:8000").rstrip("/")
TRACE_PATH = ROOT / "reports" / "agent_traces.jsonl"

st.set_page_config(
    page_title="JourneyX AI — India Travel Planner",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Travel-Themed CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Base ── */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 50%, #0d1b2a 100%); }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2744 0%, #0d1b2a 100%);
        border-right: 1px solid rgba(255,107,53,0.3);
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        background: linear-gradient(90deg, #FF6B35, #FFD93D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.4rem;
        font-weight: 800;
    }

    /* ── Main title ── */
    .main-title {
        background: linear-gradient(135deg, #FF6B35 0%, #FFD93D 50%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 0;
    }
    .main-subtitle {
        color: #8fa3bf;
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: rgba(26, 39, 68, 0.8);
        border-radius: 16px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        border: 1px solid rgba(255,107,53,0.15);
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    /* ── Sticky chat input ── */
    [data-testid="stBottom"] {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 999 !important;
        background: linear-gradient(0deg, #0d1b2a 70%, transparent 100%) !important;
        padding: 1rem 1rem 1.4rem 1rem !important;
        backdrop-filter: blur(12px) !important;
    }
    [data-testid="stChatInput"] {
        max-width: 820px !important;
        margin: 0 auto !important;
    }
    [data-testid="stChatInput"] textarea {
        background: rgba(26, 39, 68, 0.95) !important;
        border: 2px solid rgba(255,107,53,0.4) !important;
        border-radius: 18px !important;
        color: #e8f0fe !important;
        font-size: 1rem !important;
        padding: 0.9rem 3.5rem 0.9rem 1.3rem !important;
        min-height: 54px !important;
        max-height: 200px !important;
        resize: none !important;
        box-shadow: 0 4px 30px rgba(255,107,53,0.15) !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #FF6B35 !important;
        box-shadow: 0 0 0 3px rgba(255,107,53,0.2), 0 4px 30px rgba(255,107,53,0.2) !important;
        outline: none !important;
    }
    [data-testid="stChatInput"] textarea::placeholder { color: #5a7a9a !important; }
    [data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #FF6B35 0%, #FFD93D 100%) !important;
        border-radius: 12px !important;
        border: none !important;
        color: #0d1b2a !important;
        font-weight: 700 !important;
        width: 38px !important;
        height: 38px !important;
    }
    [data-testid="stChatInput"] button:hover {
        opacity: 0.9 !important;
        transform: scale(1.06) !important;
    }

    /* ── Bottom padding ── */
    .main .block-container { padding-bottom: 130px !important; }

    /* ── New conversation button ── */
    .new-conv-btn button {
        background: linear-gradient(135deg, #FF6B35 0%, #FFD93D 100%) !important;
        color: #0d1b2a !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        width: 100% !important;
        padding: 0.55rem !important;
        letter-spacing: 0.3px;
    }

    /* ── Example query buttons ── */
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,107,53,0.1) !important;
        color: #FFD93D !important;
        border: 1px solid rgba(255,107,53,0.3) !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        text-align: left !important;
        padding: 0.4rem 0.7rem !important;
        transition: all 0.2s !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,107,53,0.25) !important;
        border-color: #FF6B35 !important;
        color: #fff !important;
    }

    /* ── Status badges ── */
    .status-ok   { color: #4ECDC4; font-weight: 700; }
    .status-refuse { color: #FF6B6B; font-weight: 700; }
    .status-clarify { color: #FFD93D; font-weight: 700; }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: rgba(26, 39, 68, 0.8);
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
        border: 1px solid rgba(255,107,53,0.2);
        box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    }
    [data-testid="stMetric"] label { color: #8fa3bf !important; font-size: 0.78rem !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #FFD93D !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-weight: 600;
        color: #8fa3bf;
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: #FF6B35 !important;
        border-bottom: 2px solid #FF6B35 !important;
    }

    /* ── Spinner ── */
    .stSpinner > div { border-top-color: #FF6B35 !important; }

    /* ── Response metadata ── */
    .response-meta {
        font-size: 0.73rem;
        color: #5a7a9a;
        margin-top: 0.4rem;
        padding: 0.3rem 0.7rem;
        background: rgba(13, 27, 42, 0.7);
        border-radius: 6px;
        border-left: 2px solid rgba(255,107,53,0.4);
    }

    /* ── Welcome card ── */
    .welcome-card {
        text-align: center;
        padding: 3.5rem 1rem 2.5rem;
        color: #8fa3bf;
    }
    .welcome-card .icon { font-size: 3.5rem; margin-bottom: 0.8rem; }
    .welcome-card h3 {
        background: linear-gradient(90deg, #FF6B35, #FFD93D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .welcome-card p { font-size: 0.9rem; line-height: 1.6; color: #6a8aaa; }

    /* ── Trace timeline ── */
    .trace-node {
        display: inline-block;
        padding: 0.25rem 0.7rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.1rem;
    }
    .trace-ok   { background: rgba(78,205,196,0.2); color: #4ECDC4; border: 1px solid rgba(78,205,196,0.4); }
    .trace-err  { background: rgba(255,107,107,0.2); color: #FF6B6B; border: 1px solid rgba(255,107,107,0.4); }
    .trace-warn { background: rgba(255,217,61,0.2); color: #FFD93D; border: 1px solid rgba(255,217,61,0.4); }

    /* ── Divider ── */
    hr { border-color: rgba(255,107,53,0.2) !important; }

    /* ── Scroll anchor ── */
    .chat-scroll-anchor { height: 20px; }

    /* ── Follow-up buttons ── */
    .followup-btn button {
        background: rgba(78,205,196,0.1) !important;
        color: #4ECDC4 !important;
        border: 1px solid rgba(78,205,196,0.3) !important;
        border-radius: 20px !important;
        font-size: 0.8rem !important;
        padding: 0.3rem 0.8rem !important;
        transition: all 0.2s !important;
        animation: slideInUp 0.4s ease-out !important;
    }
    .followup-btn button:hover {
        background: rgba(78,205,196,0.25) !important;
        border-color: #4ECDC4 !important;
        color: #fff !important;
        transform: translateY(-2px) scale(1.04) !important;
        box-shadow: 0 4px 15px rgba(78,205,196,0.3) !important;
    }

    /* ══════════════════════════════════════════════════════════
       KEYFRAME ANIMATIONS
    ══════════════════════════════════════════════════════════ */

    /* Fade in from below */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(24px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Slide in from left */
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-30px); }
        to   { opacity: 1; transform: translateX(0); }
    }

    /* Slide in from bottom */
    @keyframes slideInUp {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Gentle pulse glow */
    @keyframes pulseGlow {
        0%   { box-shadow: 0 0 0 0 rgba(255,107,53,0.0); }
        50%  { box-shadow: 0 0 18px 4px rgba(255,107,53,0.25); }
        100% { box-shadow: 0 0 0 0 rgba(255,107,53,0.0); }
    }

    /* Slow compass rotation */
    @keyframes compassSpin {
        0%   { transform: rotate(0deg); }
        25%  { transform: rotate(15deg); }
        75%  { transform: rotate(-15deg); }
        100% { transform: rotate(0deg); }
    }

    /* Shimmer sweep */
    @keyframes shimmer {
        0%   { background-position: -400px 0; }
        100% { background-position: 400px 0; }
    }

    /* Float up-down */
    @keyframes float {
        0%   { transform: translateY(0px); }
        50%  { transform: translateY(-6px); }
        100% { transform: translateY(0px); }
    }

    /* Gradient border pulse */
    @keyframes borderPulse {
        0%   { border-color: rgba(255,107,53,0.2); }
        50%  { border-color: rgba(255,107,53,0.6); }
        100% { border-color: rgba(255,107,53,0.2); }
    }

    /* Typing cursor blink */
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0; }
    }

    /* ── Apply animations to elements ── */

    /* Welcome card fades in */
    .welcome-card {
        animation: fadeInUp 0.8s ease-out !important;
    }
    .welcome-card .icon {
        animation: float 3s ease-in-out infinite !important;
        display: inline-block !important;
    }

    /* Chat messages slide in */
    [data-testid="stChatMessage"] {
        animation: slideInLeft 0.35s ease-out !important;
    }

    /* Destination cards pulse */
    [data-testid="stSidebar"] div[style*="border-radius:14px"] {
        animation: pulseGlow 3s ease-in-out infinite !important;
    }

    /* Main title compass icon rotates */
    .compass-icon {
        display: inline-block;
        animation: compassSpin 4s ease-in-out infinite !important;
    }

    /* Spinner shimmer */
    .stSpinner {
        animation: shimmer 1.5s infinite linear !important;
        background: linear-gradient(90deg,
            rgba(255,107,53,0.1) 0%,
            rgba(255,217,61,0.3) 50%,
            rgba(255,107,53,0.1) 100%) !important;
        background-size: 400px 100% !important;
    }

    /* New conversation button pulses */
    .new-conv-btn button {
        animation: borderPulse 2.5s ease-in-out infinite !important;
    }

    /* Hero header fades in */
    .hero-header {
        animation: fadeInUp 0.6s ease-out !important;
    }

    /* Destination grid cards float */
    .dest-card {
        animation: float 4s ease-in-out infinite !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    .dest-card:hover {
        transform: translateY(-8px) scale(1.04) !important;
        box-shadow: 0 12px 30px rgba(255,107,53,0.3) !important;
    }

    /* Sidebar destination rows slide in */
    .dest-row {
        animation: slideInLeft 0.4s ease-out !important;
    }

    /* Metric cards fade in */
    [data-testid="stMetric"] {
        animation: fadeInUp 0.5s ease-out !important;
    }

    /* Response meta bar */
    .response-meta {
        animation: slideInUp 0.3s ease-out !important;
    }

    /* ══════════════════════════════════════════════════════════
       SIDEBAR AIRPLANE & CLOUD ANIMATIONS (horizontal only)
       Sidebar is ~300px wide; planes fly left→right within it
    ══════════════════════════════════════════════════════════ */

    /* Horizontal flight within sidebar width */
    @keyframes sidebarFly1 {
        0%   { left: -60px; opacity: 0; }
        8%   { opacity: 1; }
        92%  { opacity: 1; }
        100% { left: 310px; opacity: 0; }
    }

    @keyframes sidebarFly2 {
        0%   { left: -50px; opacity: 0; }
        8%   { opacity: 0.85; }
        92%  { opacity: 0.85; }
        100% { left: 310px; opacity: 0; }
    }

    @keyframes sidebarCloud1 {
        0%   { left: -70px; opacity: 0; }
        8%   { opacity: 0.5; }
        92%  { opacity: 0.5; }
        100% { left: 310px; opacity: 0; }
    }

    @keyframes sidebarCloud2 {
        0%   { left: -55px; opacity: 0; }
        8%   { opacity: 0.4; }
        92%  { opacity: 0.4; }
        100% { left: 310px; opacity: 0; }
    }

    /* Plane 1 — flies across the destinations section (~30-55% of viewport) */
    .flying-plane-1 {
        position: fixed;
        font-size: 1.5rem;
        z-index: 9999;
        pointer-events: none;
        animation: sidebarFly1 12s linear infinite;
        filter: drop-shadow(0 2px 8px rgba(255,107,53,0.5));
        top: 33%;
        left: -60px;
    }

    /* Plane 2 — slightly lower in destinations section, delayed */
    .flying-plane-2 {
        position: fixed;
        font-size: 1.0rem;
        z-index: 9998;
        pointer-events: none;
        animation: sidebarFly2 18s linear infinite;
        animation-delay: 6s;
        filter: drop-shadow(0 2px 6px rgba(78,205,196,0.4));
        top: 48%;
        left: -50px;
        opacity: 0;
    }

    /* Cloud 1 — drifts above destinations section */
    .drifting-cloud-1 {
        position: fixed;
        font-size: 1.2rem;
        z-index: 9997;
        pointer-events: none;
        animation: sidebarCloud1 24s linear infinite;
        animation-delay: 2s;
        top: 28%;
        left: -70px;
        opacity: 0;
    }

    /* Cloud 2 — drifts through middle of destinations section */
    .drifting-cloud-2 {
        position: fixed;
        font-size: 0.9rem;
        z-index: 9997;
        pointer-events: none;
        animation: sidebarCloud2 32s linear infinite;
        animation-delay: 14s;
        top: 42%;
        left: -55px;
        opacity: 0;
    }

    /* ══════════════════════════════════════════════════════════
       WELCOME SCREEN ANIMATIONS
    ══════════════════════════════════════════════════════════ */

    /* Spinning compass */
    @keyframes spinCompass {
        0%   { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Typewriter cursor */
    @keyframes typeCursor {
        0%, 100% { border-right-color: #FF6B35; }
        50%       { border-right-color: transparent; }
    }

    /* Staggered fade-in for feature bullets */
    @keyframes featureFadeIn {
        from { opacity: 0; transform: translateX(-20px); }
        to   { opacity: 1; transform: translateX(0); }
    }

    /* Pulsing ring around compass */
    @keyframes compassRing {
        0%   { box-shadow: 0 0 0 0 rgba(255,107,53,0.4); }
        70%  { box-shadow: 0 0 0 20px rgba(255,107,53,0); }
        100% { box-shadow: 0 0 0 0 rgba(255,107,53,0); }
    }

    /* Welcome title glow */
    @keyframes titleGlow {
        0%   { text-shadow: 0 0 10px rgba(255,107,53,0.3); }
        50%  { text-shadow: 0 0 30px rgba(255,107,53,0.7), 0 0 60px rgba(255,217,61,0.3); }
        100% { text-shadow: 0 0 10px rgba(255,107,53,0.3); }
    }

    /* Welcome card enhanced */
    .welcome-animated {
        text-align: center;
        padding: 2rem 1.5rem 2rem;
        animation: fadeInUp 0.8s ease-out;
    }
    .welcome-compass {
        font-size: 4rem;
        display: inline-block;
        animation: spinCompass 8s linear infinite;
        filter: drop-shadow(0 0 12px rgba(255,107,53,0.6));
    }
    .welcome-title {
        background: linear-gradient(135deg, #FF6B35 0%, #FFD93D 50%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 800;
        margin: 0.8rem 0 0.3rem;
        animation: titleGlow 3s ease-in-out infinite;
        display: block;
    }
    .welcome-subtitle {
        color: #8fa3bf;
        font-size: 0.92rem;
        margin-bottom: 1.5rem;
        animation: fadeInUp 1s ease-out 0.3s both;
    }
    .feature-item {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.55rem 1rem;
        margin: 0.35rem auto;
        max-width: 420px;
        background: rgba(255,107,53,0.07);
        border: 1px solid rgba(255,107,53,0.2);
        border-radius: 10px;
        color: #c8d8e8;
        font-size: 0.88rem;
        text-align: left;
    }
    .feature-item:nth-child(1) { animation: featureFadeIn 0.5s ease-out 0.5s both; }
    .feature-item:nth-child(2) { animation: featureFadeIn 0.5s ease-out 0.8s both; }
    .feature-item:nth-child(3) { animation: featureFadeIn 0.5s ease-out 1.1s both; }
    .feature-item:nth-child(4) { animation: featureFadeIn 0.5s ease-out 1.4s both; }
    .feature-item:nth-child(5) { animation: featureFadeIn 0.5s ease-out 1.7s both; }
    .feature-icon { font-size: 1.3rem; }
    .welcome-cta {
        margin-top: 1.5rem;
        color: #4ECDC4;
        font-size: 0.88rem;
        animation: featureFadeIn 0.5s ease-out 2s both;
    }
    .bounce-arrow {
        display: inline-block;
        animation: float 1.5s ease-in-out infinite;
        font-size: 1.3rem;
    }

    /* ── Destination card buttons ── */
    .dest-card-btn button {
        background: linear-gradient(135deg, rgba(255,107,53,0.12), rgba(255,107,53,0.04)) !important;
        color: #FFD93D !important;
        border: 1px solid rgba(255,107,53,0.35) !important;
        border-radius: 14px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 0.9rem 0.4rem !important;
        min-height: 88px !important;
        line-height: 1.5 !important;
        transition: all 0.25s ease !important;
        white-space: pre-line !important;
        cursor: pointer !important;
    }
    .dest-card-btn button:hover {
        background: linear-gradient(135deg, rgba(255,107,53,0.28), rgba(255,107,53,0.12)) !important;
        border-color: rgba(255,107,53,0.75) !important;
        transform: translateY(-4px) scale(1.03) !important;
        box-shadow: 0 8px 28px rgba(255,107,53,0.35) !important;
        color: #fff !important;
    }
    .dest-card-btn p {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_count" not in st.session_state:
    st.session_state.conversation_count = 1
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0

# ── API helpers ───────────────────────────────────────────────────────────────
def _chat_via_api(message: str) -> dict:
    # Only send role+content — strip UI-only fields (meta, followup_suggestions)
    prefix = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if m["role"] in ("user", "assistant") and m.get("content")
    ]
    payload = {
        "message": message,
        "thread_id": st.session_state.thread_id,
        "conversation_prefix": prefix,
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


# ── Check API availability ────────────────────────────────────────────────────
use_api = os.getenv("JOURNEYX_UI_USE_API", "auto").lower()
api_ok = False
if use_api in ("auto", "true", "1", "yes"):
    try:
        requests.get(f"{API_URL}/health", timeout=3)
        api_ok = True
    except requests.RequestException:
        api_ok = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧭 JourneyX AI")
    st.markdown("<p style='color:#8fa3bf;font-size:0.82rem;margin-top:-0.5rem;'>AI-powered travel planning for India</p>", unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="new-conv-btn">', unsafe_allow_html=True)
    if st.button("✨ New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.session_state.conversation_count += 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ── Supported Destinations ──────────────────────────────────────────────
    st.markdown("### 📍 Supported Destinations")
    st.markdown(
        "<p style='color:#8fa3bf;font-size:0.78rem;margin-top:-0.4rem;margin-bottom:0.6rem;'>"
        "JourneyX v1 covers these Indian cities:</p>",
        unsafe_allow_html=True,
    )
    DESTINATIONS = [
        ("🏰", "Delhi", "Capital"),
        ("🌸", "Jaipur", "Pink City"),
        ("🏖️", "Goa", "Sun & Sand"),
        ("🏔️", "Manali", "Snow Peaks"),
        ("🌴", "Kochi", "Backwaters"),
        ("🌆", "Bengaluru", "Garden City"),
        ("🌊", "Mumbai", "City of Dreams"),
        ("❄️", "Shimla", "Hill Station"),
        ("🕉️", "Rishikesh", "Yoga Capital"),
        ("🕌", "Agra", "Taj Mahal"),
        ("🏯", "Mysore", "Palace City"),
        ("🏞️", "Udaipur", "Lake City"),
        ("🪔", "Varanasi", "Holy City"),
    ]
    for emoji, city, tagline in DESTINATIONS:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0;"
            f"border-bottom:1px solid rgba(255,107,53,0.1);'>"
            f"<span style='font-size:1rem;'>{emoji}</span>"
            f"<span style='color:#FFD93D;font-weight:600;font-size:0.82rem;'>{city}</span>"
            f"<span style='color:#6a8aaa;font-size:0.72rem;margin-left:auto;'>{tagline}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<p style='color:#6a8aaa;font-size:0.72rem;margin-top:0.6rem;'>"
        "⚠️ Transport data available for common routes between these cities only.</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Session stats
    st.markdown("<p style='color:#FFD93D;font-weight:700;font-size:0.85rem;'>📊 SESSION STATS</p>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Messages", len(st.session_state.messages))
    with c2:
        st.metric("Queries", st.session_state.total_queries)
    st.metric("Conversation No.", st.session_state.conversation_count)

    st.divider()

    # Backend status
    st.markdown("<p style='color:#FFD93D;font-weight:700;font-size:0.85rem;'>⚙️ BACKEND</p>", unsafe_allow_html=True)
    if api_ok:
        st.success("✅ FastAPI connected")
    else:
        st.warning("⚡ Local mode (in-process)")

    dry_run = os.getenv("JOURNEYX_AGENT_DRY_RUN", "true")
    if dry_run.lower() in ("1", "true", "yes"):
        st.info("🔧 Heuristic planner active")
    else:
        st.success("🤖 LLM planner active")

    st.divider()

    # Quick examples
    st.markdown("<p style='color:#FFD93D;font-weight:700;font-size:0.85rem;'>💡 TRY THESE</p>", unsafe_allow_html=True)
    examples = [
        "🏰 Plan 3 days in Jaipur from Delhi",
        "🚂 Compare train and bus Delhi to Goa",
        "🌊 5 days in Goa for 2 people",
        "🏔️ Budget trip to Manali from Delhi",
        "🌴 Best time to visit Kochi?",
        "🕌 Plan Agra trip from Delhi",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state._example_query = ex.split(" ", 1)[1]  # strip emoji prefix
            st.rerun()

    st.divider()
    st.markdown("<p style='color:#5a7a9a;font-size:0.75rem;'>⚠️ All plans are indicative.<br>Verify before booking.</p>", unsafe_allow_html=True)

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_chat, tab_traces, tab_health = st.tabs(["💬 Chat", "📈 Trace Dashboard", "🔧 System Health"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ════════════════════════════════════════════════════════════════════════════
with tab_chat:
    # ── Hero header ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom:0.3rem;">
        <span style="font-size:2.2rem;">🧭</span>
        <span style="background:linear-gradient(135deg,#FF6B35 0%,#FFD93D 50%,#4ECDC4 100%);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                     font-size:2.2rem;font-weight:800;letter-spacing:-0.5px;margin-left:0.3rem;">
            JourneyX AI
        </span>
    </div>
    <p style="color:#8fa3bf;font-size:0.95rem;margin:0 0 1.2rem 0;">
        🏔️ From the Himalayas to the backwaters &nbsp;·&nbsp;
        🏖️ Discover Incredible India &nbsp;·&nbsp;
        ✨ Your AI travel companion
    </p>
    """, unsafe_allow_html=True)


    if st.session_state.messages:
        msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        st.markdown(
            f'<div class="response-meta">Session {st.session_state.conversation_count} · '
            f'{msg_count} question{"s" if msg_count != 1 else ""} asked</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")
    else:
        components.html("""
<!DOCTYPE html>
<html>
<head>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: 'Inter', sans-serif; }

  @keyframes bounceMap {
    0%,100% { transform: translateY(0px) scale(1); }
    30%      { transform: translateY(-22px) scale(1.1); }
    60%      { transform: translateY(-10px) scale(1.04); }
  }
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes titleGlow {
    0%,100% { opacity: 0.88; }
    50%      { opacity: 1; }
  }
  @keyframes floatArrow {
    0%,100% { transform: translateY(0); }
    50%      { transform: translateY(-7px); }
  }

  .wrap { text-align: center; padding: 2.5rem 1rem 2rem; }

  .map-icon {
    font-size: 5.5rem;
    display: inline-block;
    animation: bounceMap 1.8s ease-in-out infinite;
    filter: drop-shadow(0 6px 20px rgba(255,107,53,0.6));
  }

  .title {
    background: linear-gradient(135deg, #FF6B35 0%, #FFD93D 50%, #4ECDC4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.2rem;
    font-weight: 800;
    margin: 1rem 0 0.4rem;
    display: block;
    animation: titleGlow 3s ease-in-out infinite;
  }

  .subtitle {
    color: #8fa3bf;
    font-size: 0.95rem;
    margin-bottom: 2rem;
    animation: fadeInUp 0.8s ease-out 0.3s both;
    line-height: 1.7;
  }
  .subtitle em { color: #5a7a9a; font-size: 0.82rem; }

  .cta {
    color: #4ECDC4;
    font-size: 0.92rem;
    animation: fadeInUp 0.6s ease-out 0.6s both;
  }
  .arrow {
    display: inline-block;
    animation: floatArrow 1.4s ease-in-out infinite;
    font-size: 1.4rem;
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="map-icon">🗺️</div>
  <span class="title">Welcome to JourneyX AI</span>
  <p class="subtitle">
    Your intelligent travel companion for Incredible India<br>
    <em>Powered by RAG &middot; Multi-Agent &middot; &le;8B LLM</em>
  </p>
  <div class="cta">
    <span class="arrow">👇</span>&nbsp; Type your travel question below to get started!
  </div>
</div>
</body>
</html>
""", height=340, scrolling=False)

    # Display conversation history
    for msg_idx, msg in enumerate(st.session_state.messages):
        if msg["role"] in ("user", "assistant"):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("meta"):
                    st.markdown(
                        f'<div class="response-meta">{msg["meta"]}</div>',
                        unsafe_allow_html=True,
                    )
                suggestions = msg.get("followup_suggestions", [])
                if msg["role"] == "assistant" and suggestions:
                    st.markdown(
                        '<div style="margin-top:0.7rem;font-size:0.8rem;color:#8fa3bf;">💡 <b>You might also want to ask:</b></div>',
                        unsafe_allow_html=True,
                    )
                    cols = st.columns(len(suggestions))
                    for i, (col, suggestion) in enumerate(zip(cols, suggestions)):
                        with col:
                            st.markdown('<div class="followup-btn">', unsafe_allow_html=True)
                            if st.button(
                                f"→ {suggestion}",
                                key=f"fup_{msg_idx}_{i}",
                                use_container_width=True,
                            ):
                                st.session_state["_example_query"] = suggestion
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

    # Spinner while waiting
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
                        f'intent: <b>{intent}</b> · steps: {steps} · tools: {tools} · '
                        f'{datetime.now().strftime("%H:%M:%S")}'
                    )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "meta": meta_html,
                        "followup_suggestions": data.get("followup_suggestions", []),
                    })

                    if data.get("thread_id"):
                        st.session_state.thread_id = data["thread_id"]

                    # 🎈 Celebrate when a full trip plan is generated!
                    if intent in ("full_plan", "refine") and status == "ok":
                        st.balloons()

                except Exception as exc:  # noqa: BLE001
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ Request failed: {exc}\n\n💡 Make sure the API server is running.",
                        "meta": "",
                    })
                st.rerun()

    st.markdown('<div class="chat-scroll-anchor"></div>', unsafe_allow_html=True)

    example_query = st.session_state.pop("_example_query", None)
    prompt = st.chat_input("Ask about trips, transport, or destinations…") or example_query

    if prompt:
        st.session_state.total_queries += 1
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state["_waiting"] = prompt
        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRACE DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
with tab_traces:
    st.markdown("## 📈 Agent Trace Dashboard")
    st.markdown(
        "<p style='color:#8fa3bf;font-size:0.88rem;'>Real-time view of every agent step — "
        "tool calls, LLM calls, latencies, and errors across all conversations.</p>",
        unsafe_allow_html=True,
    )

    if not TRACE_PATH.is_file():
        st.markdown("""
        <div style='text-align:center;padding:3rem;color:#5a7a9a;'>
            <div style='font-size:2.5rem;'>📭</div>
            <p style='margin-top:0.5rem;'>No traces yet. Run a chat query first to see agent traces here.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        lines = [ln for ln in TRACE_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()][-300:]
        rows = [json.loads(ln) for ln in lines]

        # ── Top-level KPI metrics ──────────────────────────────────────────
        st.markdown("### 📊 Key Performance Indicators")

        total_spans = len(rows)
        tool_spans = [r for r in rows if r.get("node") == "executor"]
        llm_spans  = [r for r in rows if r.get("metadata", {}).get("llm")]
        error_spans = [r for r in rows if r.get("status") == "error"]
        ok_spans    = [r for r in rows if r.get("status") == "ok"]
        latencies   = [r.get("latency_ms", 0) for r in rows if r.get("latency_ms", 0) > 0]
        avg_lat     = sum(latencies) / max(len(latencies), 1)
        max_lat     = max(latencies) if latencies else 0
        success_rate = round(len(ok_spans) / max(total_spans, 1) * 100, 1)

        # Count unique tool names called
        tool_names = [r.get("tool_name") for r in tool_spans if r.get("tool_name")]
        unique_tools = len(set(tool_names))

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1:
            st.metric("🔢 Total Spans", total_spans)
        with k2:
            st.metric("🔧 Tool Calls", len(tool_spans),
                      help="Number of executor spans (each = one tool call)")
        with k3:
            st.metric("🤖 LLM Calls", len(llm_spans),
                      help="Spans where the LLM was invoked (planner or composer)")
        with k4:
            st.metric("⚡ Avg Latency", f"{avg_lat:.0f} ms",
                      help="Average span latency across all recorded spans")
        with k5:
            st.metric("❌ Errors", len(error_spans),
                      help="Spans that returned an error status")
        with k6:
            st.metric("✅ Success Rate", f"{success_rate}%",
                      help="Percentage of spans with status=ok")

        st.divider()

        # ── Tool call breakdown ────────────────────────────────────────────
        st.markdown("### 🔧 Tool Call Breakdown")
        st.markdown(
            "<p style='color:#8fa3bf;font-size:0.83rem;'>How many times each tool was called across all conversations.</p>",
            unsafe_allow_html=True,
        )

        tool_counts: dict[str, int] = defaultdict(int)
        tool_errors: dict[str, int] = defaultdict(int)
        for r in tool_spans:
            tn = r.get("tool_name", "unknown")
            tool_counts[tn] += 1
            if r.get("status") == "error":
                tool_errors[tn] += 1

        if tool_counts:
            tool_rows = []
            for tn, cnt in sorted(tool_counts.items(), key=lambda x: -x[1]):
                errs = tool_errors.get(tn, 0)
                ok_cnt = cnt - errs
                status_badge = "✅" if errs == 0 else ("⚠️" if errs < cnt else "❌")
                tool_rows.append({
                    "Tool Name": tn,
                    "Total Calls": cnt,
                    "✅ Successful": ok_cnt,
                    "❌ Errors": errs,
                    "Status": status_badge,
                })
            st.dataframe(
                tool_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tool Name": st.column_config.TextColumn("🔧 Tool Name", width="medium"),
                    "Total Calls": st.column_config.NumberColumn("Total Calls", width="small"),
                    "✅ Successful": st.column_config.NumberColumn("✅ Successful", width="small"),
                    "❌ Errors": st.column_config.NumberColumn("❌ Errors", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                },
            )
        else:
            st.info("No tool calls recorded yet.")

        st.divider()

        # ── Node-by-node latency ───────────────────────────────────────────
        st.markdown("### ⚡ Latency by Agent Node")
        st.markdown(
            "<p style='color:#8fa3bf;font-size:0.83rem;'>Average response time for each node in the agent pipeline.</p>",
            unsafe_allow_html=True,
        )

        node_latencies: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            if r.get("latency_ms", 0) > 0:
                node_latencies[r.get("node", "unknown")].append(r["latency_ms"])

        if node_latencies:
            lat_rows = []
            node_order = ["policy", "planner", "executor", "critic", "composer"]
            for node in node_order + [n for n in node_latencies if n not in node_order]:
                if node not in node_latencies:
                    continue
                lats = node_latencies[node]
                avg = sum(lats) / len(lats)
                mx = max(lats)
                # Latency colour indicator
                if avg < 100:
                    indicator = "🟢 Fast"
                elif avg < 500:
                    indicator = "🟡 Moderate"
                else:
                    indicator = "🔴 Slow"
                lat_rows.append({
                    "Node": node.title(),
                    "Calls": len(lats),
                    "Avg Latency (ms)": round(avg, 1),
                    "Max Latency (ms)": round(mx, 1),
                    "Speed": indicator,
                })
            st.dataframe(
                lat_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Node": st.column_config.TextColumn("🔵 Node", width="small"),
                    "Calls": st.column_config.NumberColumn("Calls", width="small"),
                    "Avg Latency (ms)": st.column_config.NumberColumn("Avg Latency (ms)", width="medium"),
                    "Max Latency (ms)": st.column_config.NumberColumn("Max Latency (ms)", width="medium"),
                    "Speed": st.column_config.TextColumn("Speed", width="small"),
                },
            )
        else:
            st.info("No latency data recorded yet.")

        st.divider()

        # ── Recent trace timeline ──────────────────────────────────────────
        st.markdown("### 🕐 Recent Trace Timeline")
        st.markdown(
            "<p style='color:#8fa3bf;font-size:0.83rem;'>Last 50 spans — most recent first. "
            "Each row is one step in the agent pipeline.</p>",
            unsafe_allow_html=True,
        )

        # Filter controls
        fc1, fc2, fc3 = st.columns([2, 2, 1])
        with fc1:
            all_nodes = sorted({r.get("node", "") for r in rows if r.get("node")})
            pick_nodes = st.multiselect("Filter by Node", all_nodes, default=all_nodes, key="trace_node_filter")
        with fc2:
            pick_status = st.multiselect("Filter by Status", ["ok", "error"], default=["ok", "error"], key="trace_status_filter")
        with fc3:
            show_n = st.selectbox("Show last", [25, 50, 100, 200], index=1, key="trace_show_n")

        filtered = [
            r for r in rows
            if r.get("node") in pick_nodes and r.get("status") in pick_status
        ][-show_n:]
        filtered_display = list(reversed(filtered))  # most recent first

        if filtered_display:
            timeline_rows = []
            for r in filtered_display:
                node = r.get("node", "—")
                status = r.get("status", "ok")
                tool = r.get("tool_name") or "—"
                lat = r.get("latency_ms", 0)
                step = r.get("step_index", "—")
                thread = (r.get("thread_id") or "—")[:12]
                ts = r.get("timestamp", "")
                if ts:
                    try:
                        ts = datetime.fromisoformat(ts).strftime("%H:%M:%S")
                    except Exception:
                        ts = ts[:8]

                status_icon = "✅" if status == "ok" else "❌"
                lat_str = f"{lat:.0f} ms" if lat > 0 else "—"

                timeline_rows.append({
                    "Time": ts,
                    "Step": step,
                    "Node": node.title(),
                    "Tool Called": tool,
                    "Latency": lat_str,
                    "Status": f"{status_icon} {status}",
                    "Thread": thread,
                })

            st.dataframe(
                timeline_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Time": st.column_config.TextColumn("🕐 Time", width="small"),
                    "Step": st.column_config.TextColumn("Step", width="small"),
                    "Node": st.column_config.TextColumn("🔵 Node", width="small"),
                    "Tool Called": st.column_config.TextColumn("🔧 Tool Called", width="medium"),
                    "Latency": st.column_config.TextColumn("⚡ Latency", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Thread": st.column_config.TextColumn("Thread ID", width="medium"),
                },
            )
            st.caption(f"Showing {len(filtered_display)} of {len(rows)} total spans")
        else:
            st.info("No spans match the current filters.")

        st.divider()

        # ── Error log ─────────────────────────────────────────────────────
        if error_spans:
            st.markdown("### ❌ Error Log")
            st.markdown(
                f"<p style='color:#FF6B6B;font-size:0.83rem;'>{len(error_spans)} error(s) detected in traces.</p>",
                unsafe_allow_html=True,
            )
            err_rows = []
            for r in reversed(error_spans[-20:]):
                err_rows.append({
                    "Node": r.get("node", "—").title(),
                    "Tool": r.get("tool_name") or "—",
                    "Error Detail": str(r.get("metadata", {}).get("message", "—"))[:120],
                    "Thread": (r.get("thread_id") or "—")[:12],
                })
            st.dataframe(err_rows, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — SYSTEM HEALTH
# ════════════════════════════════════════════════════════════════════════════
with tab_health:
    st.markdown("## 🔧 System Health")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🌐 API Status**")
        try:
            if api_ok:
                h = requests.get(f"{API_URL}/health", timeout=5).json()
                st.success("✅ FastAPI server is healthy")
                st.json(h)
            else:
                st.warning("⚡ API unreachable — using local in-process mode")
                st.json({"mode": "local", "corpus_available": str((ROOT / "data/manifest.yaml").is_file())})
        except requests.RequestException as e:
            st.error(f"API error: {e}")

    with col2:
        st.markdown("**⚙️ Environment Configuration**")
        env_info = {
            "JOURNEYX_AGENT_DRY_RUN": os.getenv("JOURNEYX_AGENT_DRY_RUN", "true"),
            "JOURNEYX_EMBEDDING_FALLBACK": os.getenv("JOURNEYX_EMBEDDING_FALLBACK", "false"),
            "JOURNEYX_DISABLE_RERANK": os.getenv("JOURNEYX_DISABLE_RERANK", "false"),
            "JOURNEYX_API_URL": API_URL,
            "data/manifest.yaml present": str((ROOT / "data/manifest.yaml").is_file()),
            "reports/agent_traces.jsonl present": str(TRACE_PATH.is_file()),
            "trace_span_count": len(lines) if TRACE_PATH.is_file() else 0,
        }
        st.json(env_info)

    st.divider()
    st.markdown("**📁 Data Files**")
    data_dir = ROOT / "data"
    if data_dir.is_dir():
        file_info = []
        for f in sorted(data_dir.rglob("*")):
            if f.is_file() and f.suffix in (".jsonl", ".yaml", ".json", ".faiss", ".pkl"):
                size_kb = f.stat().st_size / 1024
                file_info.append({"File": str(f.relative_to(ROOT)), "Size (KB)": round(size_kb, 1)})
        if file_info:
            st.dataframe(file_info, use_container_width=True, hide_index=True)