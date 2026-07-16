"""Dashboard tab — lịch nội dung + thống kê + top video.

Lịch được render hoàn toàn bằng HTML/CSS (1 card liền mạch). Điều hướng tháng
và chọn ngày qua query-param links (?ym=YYYY-MM&d=YYYY-MM-DD) nên kiểm soát
được 100% giao diện, không phụ thuộc widget thô của Streamlit.
"""

import calendar
from datetime import date, timedelta

import streamlit as st

from webui.affiliate.store import db as store


_CAL_CSS = """
<style>
.cal-card{
  background:#161922;border:1px solid #262a38;border-radius:16px;
  padding:18px 20px;max-width:360px;font-family:'Segoe UI',sans-serif;
}
.cal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
.cal-title{font-size:15px;font-weight:700;color:#e8e8ea;letter-spacing:.2px;}
.cal-nav{
  width:30px;height:30px;border-radius:9px;background:#222636;color:#9aa0b3;
  display:flex;align-items:center;justify-content:center;text-decoration:none;
  font-size:18px;line-height:1;transition:.15s;
}
.cal-nav:hover{background:#343b52;color:#fff;}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:5px;}
.cal-wd{
  text-align:center;font-size:10px;color:#565d72;font-weight:700;
  text-transform:uppercase;letter-spacing:.5px;padding-bottom:6px;
}
.cal-day{
  position:relative;aspect-ratio:1/1;display:flex;align-items:center;
  justify-content:center;border-radius:9px;font-size:13px;color:#c5c9d6;
  text-decoration:none;transition:.12s;
}
.cal-day:hover{background:#222636;color:#fff;}
.cal-day.muted{color:transparent;pointer-events:none;}
.cal-day.evt-posted{background:#10243a;}
.cal-day.evt-sched{background:#2c2110;}
.cal-day.today{color:#ff6b6b;font-weight:700;box-shadow:inset 0 0 0 1.5px #ff4b4b66;}
.cal-day.sel{background:#ff4b4b !important;color:#fff !important;font-weight:700;box-shadow:none;}
.cal-dot{
  position:absolute;bottom:5px;left:50%;transform:translateX(-50%);
  width:4px;height:4px;border-radius:50%;
}
.cal-dot.posted{background:#4fc3f7;}
.cal-dot.sched{background:#ff9800;}
.cal-legend{display:flex;gap:16px;margin-top:14px;font-size:10.5px;color:#565d72;}
.cal-legend i{display:inline-block;width:6px;height:6px;border-radius:50%;
  margin-right:5px;vertical-align:middle;}
</style>
"""


def render():
    stats = store.get_stats()
    top   = store.get_top_campaigns()

    # ── Stat cards ────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📹 Video đã đăng", stats["total_posted"])
    with c2:
        v = stats["total_views"]
        st.metric("👁 Lượt xem", f"{v/1000:.1f}K" if v >= 1000 else str(v))
    with c3:
        st.metric("❤️ Lượt thích", stats["total_likes"])
    with c4:
        st.metric("⏳ Chờ đăng", stats["pending_post"])

    st.divider()

    left, right = st.columns([1, 1])
    with left:
        sel = _render_calendar(stats)
        _render_selected_day(sel)
    with right:
        _render_top_videos(top)
        st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)
        _render_page_summary()


# ── Calendar ──────────────────────────────────────────────────────────────────

def _render_calendar(stats: dict) -> str:
    today = date.today()
    qp = st.query_params

    ym  = qp.get("ym") or today.strftime("%Y-%m")
    sel = qp.get("d")  or today.strftime("%Y-%m-%d")
    try:
        y, m = map(int, ym.split("-"))
    except Exception:
        y, m = today.year, today.month
        ym = today.strftime("%Y-%m")

    prev_ym = (date(y, m, 1) - timedelta(days=1)).strftime("%Y-%m")
    next_ym = (date(y, m, 1) + timedelta(days=32)).strftime("%Y-%m")

    posted_dates = stats["posted_dates"]
    sched_dates  = stats["scheduled_dates"]

    # Grid data — tuần bắt đầu Chủ Nhật
    first_weekday, num_days = calendar.monthrange(y, m)
    start_offset = (first_weekday + 1) % 7
    cells: list[int | None] = [None] * start_offset + list(range(1, num_days + 1))
    while len(cells) % 7:
        cells.append(None)

    # Weekday header
    wd_html = "".join(
        f"<div class='cal-wd'>{d}</div>"
        for d in ["CN", "T2", "T3", "T4", "T5", "T6", "T7"]
    )

    # Day cells
    days_html = ""
    for day in cells:
        if day is None:
            days_html += "<div class='cal-day muted'>0</div>"
            continue
        ds = f"{y:04d}-{m:02d}-{day:02d}"
        cls = ["cal-day"]
        dot = ""
        if ds in posted_dates:
            cls.append("evt-posted")
            dot = "<span class='cal-dot posted'></span>"
        elif ds in sched_dates:
            cls.append("evt-sched")
            dot = "<span class='cal-dot sched'></span>"
        if ds == today.strftime("%Y-%m-%d"):
            cls.append("today")
        if ds == sel:
            cls.append("sel")
        href = f"?ym={ym}&d={ds}"
        days_html += (
            f"<a href='{href}' target='_self' class='{' '.join(cls)}'>"
            f"{day}{dot}</a>"
        )

    html = f"""
{_CAL_CSS}
<div class="cal-card">
  <div class="cal-head">
    <a href="?ym={prev_ym}&d={sel}" target="_self" class="cal-nav">‹</a>
    <div class="cal-title">Tháng {m} / {y}</div>
    <a href="?ym={next_ym}&d={sel}" target="_self" class="cal-nav">›</a>
  </div>
  <div class="cal-grid">{wd_html}{days_html}</div>
  <div class="cal-legend">
    <span><i style="background:#4fc3f7"></i>Đã đăng</span>
    <span><i style="background:#ff9800"></i>Lên lịch</span>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
    return sel


def _render_selected_day(sel: str):
    campaigns = store.get_campaigns_for_date(sel)
    st.markdown(
        f"<div style='margin-top:14px;font-size:13px;color:#888'>"
        f"📋 Ngày <b style='color:#ccc'>{sel}</b></div>",
        unsafe_allow_html=True,
    )
    if not campaigns:
        st.caption("Không có video nào ngày này.")
        return
    for c in campaigns:
        icon = "✅" if c["status"] == "posted" else "📅"
        views_str = f" · 👁 {c['views']:,}" if c.get("views") else ""
        st.markdown(
            f"{icon} **{c['product_name'][:40]}** — _{c.get('hook_type','')}_{views_str}"
        )


# ── Top videos ────────────────────────────────────────────────────────────────

def _render_top_videos(top: list[dict]):
    st.markdown("**🏆 Top video**")
    if not top:
        st.caption("Chưa có video nào được đăng.")
        return
    for c in top:
        col_info, col_stats = st.columns([3, 1])
        with col_info:
            st.markdown(
                f"<div style='font-size:11px;color:#888'>{c.get('hook_type','')}</div>"
                f"<div style='font-size:13px;font-weight:600'>{c['product_name'][:35]}</div>",
                unsafe_allow_html=True,
            )
        with col_stats:
            st.markdown(
                f"<div style='text-align:right;font-size:12px'>"
                f"👁 {c['views']:,}<br>❤️ {c['likes']:,}</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            "<hr style='margin:6px 0;border:none;border-top:1px solid #2d3142'>",
            unsafe_allow_html=True,
        )


# ── Page summary ──────────────────────────────────────────────────────────────

def _render_page_summary():
    st.markdown("**📘 Facebook Pages**")
    pages = store.list_pages()
    if not pages:
        st.caption("Chưa kết nối page nào. Vào tab **Cài đặt** để thêm.")
        return
    for p in pages:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0'>"
            f"<span style='width:8px;height:8px;background:#4caf50;"
            f"border-radius:50%;display:inline-block;flex-shrink:0'></span>"
            f"<b>{p['name']}</b>&nbsp;"
            f"<span style='color:#555;font-size:11px'>{p['page_id']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
