"""Dashboard tab — KPI, lịch nội dung, video theo ngày, top video, Pages.

Toàn bộ được render bằng HTML theo design system trong ``theme.py`` để kiểm soát
bố cục ở 390 / 768 / 1440px. Lịch điều hướng bằng query-param links
(?ym=YYYY-MM&d=YYYY-MM-DD): là thẻ <a> thật nên dùng được bằng bàn phím.
"""

import calendar
from datetime import date, timedelta

import streamlit as st

from webui.affiliate.store import db as store
from webui.affiliate.theme import esc

_WEEKDAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"]
_STATUS_TEXT = {
    "draft": "Nháp",
    "rendering": "Đang render",
    "scheduled": "Chờ đăng",
    "posted": "Đã đăng",
    "error": "Lỗi",
}


def _compact(n: int) -> str:
    return f"{n / 1000:.1f}K" if n >= 1000 else str(n)


def render():
    stats = store.get_stats()
    sel = _selected_date()

    html = (
        _kpis_html(stats)
        + "<div class='af-dash'>"
        + _calendar_html(stats, sel)
        + "<div class='af-side'>"
        + _day_html(sel)
        + _top_videos_html()
        + _pages_html()
        + "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ── KPI ───────────────────────────────────────────────────────────────────────

def _kpis_html(stats: dict) -> str:
    pending = stats["pending_post"]
    cards = [
        ("is-primary", "Chờ đăng", str(pending),
         "Cần xử lý trong Pipeline" if pending else "Không có video tồn"),
        ("", "Đã đăng", str(stats["total_posted"]), "video"),
        ("", "Lượt xem", _compact(stats["total_views"]), "tổng cộng"),
        ("", "Lượt thích", _compact(stats["total_likes"]), "tổng cộng"),
    ]
    items = "".join(
        f"<div class='af-kpi {cls}'><span class='af-kpi-label'>{esc(label)}</span>"
        f"<span class='af-kpi-value'>{esc(value)}</span>"
        f"<span class='af-kpi-note'>{esc(note)}</span></div>"
        for cls, label, value, note in cards
    )
    return f"<section class='af-kpis' aria-label='Chỉ số tổng quan'>{items}</section>"


# ── Calendar ──────────────────────────────────────────────────────────────────

def _selected_date() -> str:
    raw = st.query_params.get("d") or ""
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return date.today().isoformat()


def _current_month(sel: str) -> tuple[int, int]:
    raw = st.query_params.get("ym") or sel[:7]
    try:
        y, m = (int(x) for x in raw.split("-"))
        date(y, m, 1)
        return y, m
    except (ValueError, TypeError):
        today = date.today()
        return today.year, today.month


def _calendar_html(stats: dict, sel: str) -> str:
    today = date.today().isoformat()
    y, m = _current_month(sel)
    ym = f"{y:04d}-{m:02d}"
    prev_ym = (date(y, m, 1) - timedelta(days=1)).strftime("%Y-%m")
    next_ym = (date(y, m, 1) + timedelta(days=32)).strftime("%Y-%m")
    posted, scheduled = stats["posted_dates"], stats["scheduled_dates"]

    first_weekday, num_days = calendar.monthrange(y, m)
    offset = (first_weekday + 1) % 7  # tuần bắt đầu Chủ nhật

    cells = "".join(
        f"<div class='af-cal-wd' aria-hidden='true'>{d}</div>" for d in _WEEKDAYS
    )
    cells += "<div aria-hidden='true'></div>" * offset
    for day in range(1, num_days + 1):
        ds = f"{ym}-{day:02d}"
        classes = ["af-cal-day"]
        label = [f"Ngày {day} tháng {m} năm {y}"]
        attrs = ""
        mark = ""
        if ds == today:
            classes.append("is-today")
            label.append("hôm nay")
            attrs += " aria-current='date'"
        if ds == sel:
            classes.append("is-selected")
            label.append("đang chọn")
        if posted.get(ds):
            mark = "<span class='af-cal-mark is-posted' aria-hidden='true'></span>"
            label.append(f"{posted[ds]} video đã đăng")
        elif scheduled.get(ds):
            mark = "<span class='af-cal-mark is-scheduled' aria-hidden='true'></span>"
            label.append(f"{scheduled[ds]} video lên lịch")
        cells += (
            f"<a href='?ym={ym}&d={ds}' target='_self' class='{' '.join(classes)}'"
            f" aria-label='{esc(', '.join(label))}'{attrs}>{day}{mark}</a>"
        )

    return (
        f"<nav class='af-card' aria-label='Lịch nội dung tháng {m} năm {y}'>"
        "<div class='af-cal-head'>"
        f"<a href='?ym={prev_ym}&d={sel}' target='_self' class='af-cal-nav'"
        " aria-label='Tháng trước'><span aria-hidden='true'>‹</span></a>"
        f"<h2>Tháng {m} / {y}</h2>"
        f"<a href='?ym={next_ym}&d={sel}' target='_self' class='af-cal-nav'"
        " aria-label='Tháng sau'><span aria-hidden='true'>›</span></a>"
        "</div>"
        f"<div class='af-cal-grid'>{cells}</div>"
        "<div class='af-cal-legend'>"
        "<span><span class='af-cal-mark is-posted' aria-hidden='true'></span>Đã đăng</span>"
        "<span><span class='af-cal-mark is-scheduled' aria-hidden='true'></span>Lên lịch</span>"
        "</div></nav>"
    )


# ── Cột phải ──────────────────────────────────────────────────────────────────

def _day_html(sel: str) -> str:
    y, m, d = sel.split("-")
    campaigns = store.get_campaigns_for_date(sel)
    if campaigns:
        rows = "".join(
            "<li><div class='af-list-main'>"
            f"{esc((c.get('product_name') or '')[:60])}"
            f"<small>{esc(c.get('hook_text') or c.get('hook_type') or '')}</small></div>"
            f"<div class='af-list-meta'>{esc(_STATUS_TEXT.get(c['status'], c['status']))}"
            + (f"<br>{c['views']:,} lượt xem" if c.get("views") else "")
            + "</div></li>"
            for c in campaigns
        )
        body = f"<ul class='af-list'>{rows}</ul>"
    else:
        body = "<p class='af-empty'>Không có video nào được đăng hoặc lên lịch trong ngày này.</p>"
    return (
        "<section class='af-card af-span'>"
        f"<h2>Ngày {int(d)}/{int(m)}/{y}</h2>{body}</section>"
    )


def _top_videos_html() -> str:
    top = store.get_top_campaigns()
    if top:
        rows = "".join(
            "<li><div class='af-list-main'>"
            f"{esc((c.get('product_name') or '')[:50])}"
            f"<small>{esc(c.get('hook_type') or '')}</small></div>"
            f"<div class='af-list-meta'>{c['views']:,} lượt xem<br>{c['likes']:,} lượt thích</div></li>"
            for c in top
        )
        body = f"<ul class='af-list'>{rows}</ul>"
    else:
        body = "<p class='af-empty'>Chưa có video nào được đăng. Đăng video đầu tiên từ tab Pipeline.</p>"
    return f"<section class='af-card'><h2>Top video</h2>{body}</section>"


def _pages_html() -> str:
    pages = store.list_pages()
    if pages:
        rows = "".join(
            f"<li><div class='af-list-main'>{esc(p['name'])}"
            f"<small>ID {esc(p['page_id'])}</small></div></li>"
            for p in pages
        )
        body = f"<ul class='af-list'>{rows}</ul>"
    else:
        body = "<p class='af-empty'>Chưa kết nối Page nào. Thêm Page trong tab Cài đặt.</p>"
    return f"<section class='af-card'><h2>Facebook Pages</h2>{body}</section>"
