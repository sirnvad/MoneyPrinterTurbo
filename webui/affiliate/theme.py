"""
Design system của AffiliateStudio — một nguồn duy nhất cho màu, chữ, khoảng cách.

Màu (5 màu chủ đạo trên nền trắng, không gradient):
  ink     #14181F   chữ chính, trạng thái đã chọn
  muted   #556070   chữ phụ, nhãn            (6.4:1 trên trắng)
  line    #8793A1   viền ô nhập              (3.1:1 trên trắng — WCAG 1.4.11)
  canvas  #F3F5F7   nền card, hover
  accent  #B93815   hành động chính, lỗi     (5.8:1 với chữ trắng)

Khoảng cách: 4 · 8 · 12 · 16 · 24 · 32 px.
Chữ: 12 (nhãn) · 14 (nội dung) · 16 (tiêu đề khối) · 20 (tiêu đề trang) · 28 (số KPI).
Vùng bấm tối thiểu 44px. Breakpoint: 768px và 1024px.
"""

import html

import streamlit as st

INK = "#14181F"
MUTED = "#556070"
LINE = "#8793A1"
CANVAS = "#F3F5F7"
ACCENT = "#B93815"
WHITE = "#FFFFFF"

STREAMLIT_THEME = {
    "theme.base": "light",
    "theme.primaryColor": ACCENT,
    "theme.backgroundColor": WHITE,
    "theme.secondaryBackgroundColor": CANVAS,
    "theme.textColor": INK,
    "theme.font": "sans serif",
}

_CSS = f"""
<style>
:root {{
  --ink:{INK}; --muted:{MUTED}; --line:{LINE}; --canvas:{CANVAS}; --accent:{ACCENT}; --white:{WHITE};
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px;
  --t-label:12px; --t-body:14px; --t-title:16px; --t-page:20px; --t-kpi:28px;
  --radius:8px; --tap:44px;
  --font:"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
}}

/* ── Nền tảng ─────────────────────────────────────────────────────────────── */
#MainMenu, footer, header {{ visibility:hidden; }}
.stApp {{ background:var(--white); color:var(--ink); font-family:var(--font); }}
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button {{
  font-family:var(--font);
}}
[data-testid="stMainBlockContainer"], .block-container {{
  padding:var(--s5) var(--s6) var(--s6); max-width:1280px;
}}
html, body, .stApp {{ overflow-x:hidden; }}
.stApp [data-testid="stMarkdownContainer"] p {{ font-size:var(--t-body); line-height:1.5; }}
.stApp [data-testid="stCaptionContainer"] p {{ font-size:var(--t-label); color:var(--muted); }}
.stApp code {{ overflow-wrap:anywhere; white-space:pre-wrap; }}

/* ── Header ───────────────────────────────────────────────────────────────── */
.af-header {{ display:flex; align-items:baseline; flex-wrap:wrap; gap:var(--s2) var(--s3);
  margin-bottom:var(--s3); }}
.stApp .af-header h1 {{ font-size:var(--t-page) !important; font-weight:600; margin:0;
  padding:0; color:var(--ink); line-height:1.3; }}
[data-testid="stHeaderActionElements"] {{ display:none !important; }}
.af-header span {{ font-size:var(--t-label); color:var(--muted); }}
.af-badge {{ font-size:var(--t-label); font-weight:600; color:var(--accent);
  border:1px solid var(--accent); border-radius:var(--radius); padding:2px var(--s2); }}

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
.stTabs [role="tablist"] {{ gap:var(--s2); background:transparent; padding:0; flex-wrap:wrap; }}
.stTabs [role="tab"] {{ min-height:var(--tap); min-width:var(--tap); padding:0 var(--s4);
  color:var(--muted); background:transparent; border-radius:var(--radius) var(--radius) 0 0;
  justify-content:center; }}
.stTabs [role="tab"] p {{ font-size:var(--t-body); font-weight:600; }}
.stTabs [role="tab"]:hover {{ background:var(--canvas); color:var(--ink); }}
.stTabs [role="tab"][aria-selected="true"] {{ color:var(--ink); }}

/* ── Nút ──────────────────────────────────────────────────────────────────── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button,
[data-testid="stPopover"] button {{
  min-height:var(--tap); border-radius:var(--radius); font-size:var(--t-body); font-weight:600;
  border:1px solid var(--line); background:var(--white); color:var(--ink);
  padding:0 var(--s4);
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  background:var(--canvas); border-color:var(--ink); color:var(--ink);
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {{
  background:var(--accent); border-color:var(--accent); color:var(--white);
}}
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
  background:var(--ink); border-color:var(--ink); color:var(--white);
}}
.stButton > button:disabled, [data-testid="stBaseButton-primary"]:disabled {{
  background:var(--canvas); border-color:var(--canvas); color:var(--muted);
  cursor:not-allowed; opacity:1;
}}

/* ── Ô nhập ───────────────────────────────────────────────────────────────── */
.stApp [data-testid="stWidgetLabel"] p {{ font-size:var(--t-label); font-weight:600;
  color:var(--ink); }}
[data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"],
[data-testid="stTextAreaRootElement"], [data-testid="stSelectbox"] [role="group"],
[data-testid="stDateInput"] [data-baseweb="input"], [data-testid="stTimeInput"] [role="group"] {{
  min-height:var(--tap); border:1px solid var(--line) !important; border-radius:var(--radius);
  background:var(--white) !important; box-sizing:border-box;
}}
[data-testid="stTextInputRootElement"] input, [data-testid="stNumberInputContainer"] input,
[data-testid="stTextAreaRootElement"] textarea, [data-testid="stSelectbox"] input {{
  font-size:var(--t-body); color:var(--ink); background:transparent !important;
}}
.stApp input::placeholder, .stApp textarea::placeholder {{ color:var(--muted); opacity:1; }}
[data-testid="stNumberInputContainer"] button {{ min-width:var(--tap); min-height:var(--tap); }}
[data-testid="stFileUploader"] button {{ min-height:var(--tap); }}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within,
[data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stSelectbox"] [role="group"]:focus-within {{
  border-color:var(--ink) !important; outline:2px solid var(--ink); outline-offset:1px;
}}
.stApp input:disabled, .stApp textarea:disabled {{ color:var(--muted);
  -webkit-text-fill-color:var(--muted); cursor:not-allowed; }}
[data-testid="stTextInputRootElement"]:has(input:disabled),
[data-testid="stNumberInputContainer"]:has(input:disabled),
[data-testid="stSelectbox"] [role="group"]:has(input:disabled) {{
  background:var(--canvas) !important; border-color:var(--canvas) !important;
}}
.stCheckbox label, [data-testid="stCheckbox"] label {{ min-height:var(--tap); min-width:var(--tap);
  align-items:center; }}

/* Trạng thái lỗi của field: container có key bắt đầu bằng "af-err-" */
[class*="st-key-af-err-"] [data-testid="stTextInputRootElement"],
[class*="st-key-af-err-"] [data-testid="stTextAreaRootElement"] {{
  border:2px solid var(--accent) !important;
}}
.stApp p.af-error {{ display:flex; gap:var(--s2); align-items:flex-start; margin:var(--s1) 0 var(--s3);
  font-size:var(--t-label); line-height:1.4; color:var(--accent); font-weight:600; }}
.stApp p.af-help, .stApp span.af-help {{ margin:var(--s1) 0 var(--s3); font-size:var(--t-label);
  line-height:1.4; color:var(--muted); }}

/* Form một cột */
[class*="st-key-af-form-"] {{ max-width:560px; }}

/* ── Focus nhìn thấy được ─────────────────────────────────────────────────── */
.stApp a:focus-visible, .stApp button:focus-visible, .stApp summary:focus-visible,
.stApp [role="tab"]:focus-visible, .stApp [tabindex]:focus-visible,
.stApp input[type="checkbox"]:focus-visible + div {{
  outline:2px solid var(--ink) !important; outline-offset:2px; box-shadow:none !important;
}}

/* ── Expander, card ───────────────────────────────────────────────────────── */
[data-testid="stExpander"] details {{ border:1px solid var(--canvas); border-radius:var(--radius);
  background:var(--white); }}
[data-testid="stExpander"] summary {{ min-height:var(--tap); font-size:var(--t-body);
  font-weight:600; color:var(--ink); }}
[data-testid="stExpander"] summary:hover {{ background:var(--canvas); color:var(--ink); }}
[class*="st-key-af-row-"] {{ background:var(--canvas); border-radius:var(--radius);
  padding:var(--s3) var(--s4); border:none; }}

.af-card {{ background:var(--canvas); border-radius:var(--radius); padding:var(--s4); }}
.stApp .af-card h2 {{ font-size:var(--t-title) !important; font-weight:600;
  margin:0 0 var(--s3); padding:0; color:var(--ink); line-height:1.3; }}
.stApp p.af-empty {{ font-size:var(--t-body); color:var(--muted); margin:0; }}

/* ── Chip ─────────────────────────────────────────────────────────────────── */
.af-chip {{ display:inline-block; padding:2px var(--s2); border-radius:var(--radius);
  font-size:var(--t-label); font-weight:600; margin:0 var(--s1) var(--s1) 0;
  border:1px solid var(--line); color:var(--ink); background:var(--white); }}
.af-chip.is-done {{ background:var(--ink); border-color:var(--ink); color:var(--white); }}
.af-chip.is-error {{ background:var(--accent); border-color:var(--accent); color:var(--white); }}
.af-chip.is-quiet {{ border-color:var(--canvas); background:var(--canvas); color:var(--muted); }}
.af-thumb {{ width:100%; aspect-ratio:9/16; max-height:120px; border-radius:var(--radius);
  display:flex; align-items:center; justify-content:center; font-size:var(--t-label);
  color:var(--muted); background:var(--white); border:1px dashed var(--line); }}
.stApp p.af-hook {{ font-size:var(--t-body); margin:var(--s1) 0 var(--s2); color:var(--ink);
  overflow-wrap:anywhere; }}

/* ── Dashboard ────────────────────────────────────────────────────────────── */
.af-kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:var(--s4);
  margin:var(--s2) 0 var(--s5); }}
.af-kpi {{ background:var(--canvas); border-radius:var(--radius); padding:var(--s4);
  display:flex; flex-direction:column; gap:var(--s1); min-width:0; }}
.af-kpi-label {{ font-size:var(--t-label); font-weight:600; color:var(--muted); }}
.af-kpi-value {{ font-size:var(--t-kpi); font-weight:600; line-height:1.15; color:var(--ink); }}
.af-kpi-note {{ font-size:var(--t-label); color:var(--muted); }}
.af-kpi.is-primary {{ background:var(--ink); }}
.af-kpi.is-primary .af-kpi-label, .af-kpi.is-primary .af-kpi-note {{ color:var(--canvas); }}
.af-kpi.is-primary .af-kpi-value {{ color:var(--white); }}

.af-dash {{ display:grid; grid-template-columns:minmax(320px,5fr) 7fr; gap:var(--s4);
  align-items:start; }}
.af-side {{ display:grid; grid-template-columns:1fr 1fr; gap:var(--s4); }}
.af-side .af-span {{ grid-column:1 / -1; }}

.af-cal-head {{ display:flex; align-items:center; justify-content:space-between;
  margin-bottom:var(--s3); }}
.stApp .af-cal-head h2 {{ margin:0; }}
.af-cal-nav {{ width:var(--tap); height:var(--tap); border-radius:var(--radius);
  display:flex; align-items:center; justify-content:center; text-decoration:none !important;
  font-size:var(--t-page); line-height:1; color:var(--ink) !important;
  background:var(--white); border:1px solid var(--line); }}
.af-cal-nav:hover {{ border-color:var(--ink); }}
.af-cal-grid {{ display:grid; grid-template-columns:repeat(7,1fr); gap:var(--s1); }}
.af-cal-wd {{ text-align:center; font-size:var(--t-label); font-weight:600; color:var(--muted);
  padding-bottom:var(--s1); }}
.af-cal-day {{ position:relative; min-height:var(--tap); display:flex; align-items:center;
  justify-content:center; border-radius:var(--radius); font-size:var(--t-body);
  color:var(--ink) !important; text-decoration:none !important; background:var(--white); }}
.af-cal-day:hover {{ box-shadow:inset 0 0 0 1px var(--ink); }}
.af-cal-day.is-today {{ font-weight:700; box-shadow:inset 0 0 0 2px var(--ink); }}
.af-cal-day.is-selected {{ background:var(--accent); color:var(--white) !important;
  font-weight:700; box-shadow:none; }}
.af-cal-mark {{ position:absolute; bottom:6px; left:50%; transform:translateX(-50%);
  width:6px; height:6px; border-radius:50%; box-sizing:border-box; }}
.af-cal-mark.is-posted {{ background:var(--ink); }}
.af-cal-mark.is-scheduled {{ border:1.5px solid var(--accent); background:var(--white); }}
.af-cal-day.is-selected .af-cal-mark.is-posted {{ background:var(--white); }}
.af-cal-day.is-selected .af-cal-mark.is-scheduled {{ border-color:var(--white);
  background:transparent; }}
.af-cal-legend {{ display:flex; flex-wrap:wrap; gap:var(--s4); margin-top:var(--s3);
  font-size:var(--t-label); color:var(--muted); }}
.af-cal-legend span {{ display:inline-flex; align-items:center; gap:var(--s2); }}
.af-cal-legend .af-cal-mark {{ position:static; transform:none; }}

.af-list {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column;
  gap:var(--s2); }}
.af-list li {{ display:flex; justify-content:space-between; align-items:flex-start;
  gap:var(--s3); background:var(--white); border-radius:var(--radius);
  padding:var(--s3); margin:0; font-size:var(--t-body); }}
.af-list .af-list-main {{ min-width:0; overflow-wrap:anywhere; }}
.af-list .af-list-main small {{ display:block; font-size:var(--t-label); color:var(--muted); }}
.af-list .af-list-meta {{ flex-shrink:0; text-align:right; font-size:var(--t-label);
  color:var(--muted); }}
.af-sr {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0);
  white-space:nowrap; }}

/* ── Responsive ───────────────────────────────────────────────────────────── */
@media (max-width:1023px) {{
  .af-dash {{ grid-template-columns:minmax(300px,1fr) 1fr; }}
  .af-side {{ grid-template-columns:1fr; }}
}}
@media (max-width:767px) {{
  [data-testid="stMainBlockContainer"], .block-container {{ padding:var(--s4); }}
  .af-kpis {{ grid-template-columns:repeat(2,1fr); gap:var(--s3); margin-bottom:var(--s4); }}
  .af-dash, .af-side {{ grid-template-columns:1fr; }}
  .af-card {{ padding:var(--s3); }}
  .af-cal-grid {{ gap:2px; }}
  [class*="st-key-af-form-"] {{ max-width:none; }}
  /* Bảng → card xếp chồng: mọi hàng cột trở thành một cột */
  .stApp [data-testid="stHorizontalBlock"] {{ flex-direction:column; gap:var(--s2); }}
  .stApp [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width:100% !important; flex:1 1 100% !important; min-width:0 !important;
  }}
  .af-thumb {{ aspect-ratio:auto; min-height:var(--tap); max-height:none; }}
  .stTabs [role="tab"] {{ padding:0 var(--s3); }}
}}

/* ── Giảm chuyển động ─────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {{
  .stApp *, .stApp *::before, .stApp *::after {{
    animation-duration:0.01ms !important; animation-iteration-count:1 !important;
    transition-duration:0.01ms !important; scroll-behavior:auto !important;
  }}
}}
</style>
"""


def apply_streamlit_theme() -> None:
    """Cố định theme sáng để giao diện không đổi theo chế độ tối của hệ thống."""
    from streamlit import config as _config

    for key, value in STREAMLIT_THEME.items():
        try:
            _config.set_option(key, value)
        except Exception:
            pass


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def chip(text: str, variant: str = "") -> str:
    cls = f"af-chip {variant}".strip()
    return f"<span class='{cls}'>{esc(text)}</span>"


def field_error(message: str) -> None:
    """Thông báo lỗi ngay dưới field; role=alert để trình đọc màn hình đọc lên."""
    st.markdown(
        f"<p class='af-error' role='alert'><span aria-hidden='true'>!</span>"
        f"<span>{esc(message)}</span></p>",
        unsafe_allow_html=True,
    )


def field_help(message: str) -> None:
    st.markdown(f"<p class='af-help'>{esc(message)}</p>", unsafe_allow_html=True)
