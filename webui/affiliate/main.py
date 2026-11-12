"""
AffiliateStudio — Shopee Affiliate Video Pipeline
Entry point: streamlit run webui/affiliate/main.py

Tabs:
  Dashboard  — KPI + lịch nội dung
  Pipeline   — tạo loạt video theo chủ đề / link Shopee
  Cài đặt    — LLM, video, Facebook Pages, affiliate
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import app.*
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from webui.affiliate import theme
from webui.affiliate.store import db as store
from webui.affiliate.views import dashboard, pipeline, settings

theme.apply_streamlit_theme()

st.set_page_config(
    page_title="AffiliateStudio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

theme.inject_css()
store.init_db()

_test_badge = (
    "<span class='af-badge'>Chế độ thử nghiệm</span>"
    if store.get_setting("test_mode", "") == "1"
    else ""
)
st.markdown(
    "<div class='af-header'><h1>AffiliateStudio</h1>"
    f"<span>Shopee Affiliate Video Pipeline</span>{_test_badge}</div>",
    unsafe_allow_html=True,
)

tab_dash, tab_pipe, tab_settings = st.tabs(["Dashboard", "Pipeline", "Cài đặt"])

with tab_dash:
    dashboard.render()

with tab_pipe:
    pipeline.render()

with tab_settings:
    settings.render()
