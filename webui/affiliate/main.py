"""
AffiliateStudio — Shopee Affiliate Video Pipeline
Entry point: streamlit run webui/affiliate/main.py

Tabs:
  📊 Dashboard  — lịch tháng + thống kê
  ⚡ Pipeline   — quản lý sản phẩm & kịch bản
  ⚙️ Cài đặt   — API keys, LLM, video, Facebook Pages
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import app.*
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from webui.affiliate.store import db as store
from webui.affiliate.pages import dashboard, pipeline, settings


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AffiliateStudio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* Hide default Streamlit header/footer */
    #MainMenu, footer, header {visibility: hidden;}

    /* Tighter padding */
    .block-container {padding-top: 1rem; padding-bottom: 0.5rem;}

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #1a1d27;
        border: 1px solid #2d3142;
        border-radius: 8px;
        padding: 12px 16px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #13151f;
        padding: 6px 8px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background: #ff4b4b !important;
        color: white !important;
    }

    /* Expander header */
    .streamlit-expanderHeader {
        font-size: 14px;
        background: #1a1d27;
        border-radius: 6px;
    }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: #ff4b4b;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #e53935;
    }

    /* Calendar day buttons — compact */
    div[data-testid="column"] .stButton > button {
        padding: 4px 2px;
        font-size: 11px;
        min-height: 32px;
    }

    /* Info/success/error boxes */
    .stAlert {border-radius: 6px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Init DB ───────────────────────────────────────────────────────────────────

store.init_db()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    "<h2 style='margin-bottom:0'>🎬 AffiliateStudio</h2>"
    "<p style='color:#888;margin-top:2px'>Shopee Affiliate Video Pipeline</p>",
    unsafe_allow_html=True,
)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_dash, tab_pipe, tab_settings = st.tabs(
    ["📊 Dashboard", "⚡ Pipeline", "⚙️ Cài đặt"]
)

with tab_dash:
    dashboard.render()

with tab_pipe:
    pipeline.render()

with tab_settings:
    settings.render()
