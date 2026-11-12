"""
Pipeline tab — tạo loạt video và quản lý từng video.

Layout:
  1. Form tạo mới (2 tab: theo chủ đề / theo link Shopee) — một cột, nhãn phía trên,
     kiểm tra dữ liệu khi rời ô (on blur), lỗi kèm hướng dẫn sửa.
  2. Nhập hàng loạt.
  3. Bộ lọc + danh sách sản phẩm; mỗi video là một card (xếp chồng dưới 768px).
"""

import csv
import io
import json
import threading
from urllib.parse import urlparse

import streamlit as st

from webui.affiliate import theme
from webui.affiliate.store import db as store
from webui.affiliate.services import shopee as shopee_svc
from webui.affiliate.services import content as content_svc
from webui.affiliate.services import video_client
from webui.affiliate.services import facebook as fb_svc
from webui.affiliate.services import caption as caption_svc


# ── Nhãn trạng thái ────────────────────────────────────────────────────────────

_STATUS_LABEL = {
    "pending":   "Chờ xử lý",
    "analyzing": "Đang phân tích",
    "scripted":  "Có kịch bản",
    "rendering": "Đang render",
    "scheduled": "Chờ đăng",
    "posted":    "Đã đăng",
    "error":     "Lỗi",
    "draft":     "Nháp",
}

_CAMPAIGN_STATUS_LABEL = {
    "draft":      "Nháp",
    "rendering":  "Đang render",
    "scheduled":  "Chờ đăng",
    "posted":     "Đã đăng",
    "error":      "Lỗi",
}

_STATUS_CHIP_VARIANT = {"posted": "is-done", "error": "is-error", "draft": "is-quiet"}

# Tất cả trạng thái có thể có của 1 video
_ALL_STATUSES = ["draft", "rendering", "scheduled", "posted", "error"]

_NO_PAGE = "— Chưa chọn page —"


def render():
    _flash()
    _add_product_bar()
    _batch_import()
    st.divider()
    _toolbar()
    _product_table()


def _flash():
    """Hiện thông báo kết quả của thao tác vừa xong (sống qua một lần rerun)."""
    flash = st.session_state.pop("pipeline_flash", None)
    if not flash:
        return
    kind, message = flash
    (st.success if kind == "success" else st.error)(message)


# ── Tiện ích chung ─────────────────────────────────────────────────────────────

def _page_options() -> dict:
    opts = {p["name"]: p["id"] for p in store.list_pages()}
    opts[_NO_PAGE] = None
    return opts


def _analyze_dispatch(product_id: int):
    """Chạy đúng engine theo source_type của product."""
    product = store.get_product(product_id)
    if product and product.get("source_type") == "topic":
        content_svc.run_topic_analysis(product_id)
    else:
        shopee_svc.run_product_analysis(product_id)


# ── Kiểm tra dữ liệu (thông báo nói rõ cách sửa) ───────────────────────────────

def _validate_topic(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "Chưa có chủ đề. Nhập điều bạn muốn làm video, ví dụ: “mẹo tiết kiệm điện”."
    if len(value) < 3:
        return "Chủ đề quá ngắn. Viết ít nhất 3 ký tự, ví dụ: “dọn tủ lạnh”."
    if len(value) > 120:
        return f"Chủ đề đang dài {len(value)} ký tự. Rút gọn còn tối đa 120 ký tự."
    return ""


def _validate_shopee_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ("Chưa có link. Mở sản phẩm trên Shopee, bấm Chia sẻ → Sao chép liên kết "
                "rồi dán vào đây.")
    if not value.lower().startswith(("http://", "https://")):
        return "Link phải bắt đầu bằng https://. Dán lại đầy đủ link sao chép từ Shopee."
    host = (urlparse(value).hostname or "").lower()
    if "shopee" not in host and "shp.ee" not in host:
        return ("Đây không phải link Shopee. Dùng link có dạng https://shopee.vn/... "
                "hoặc https://s.shopee.vn/...")
    return ""


def _mark_touched(flag_key: str):
    st.session_state[flag_key] = True


# ── Form tạo mới ───────────────────────────────────────────────────────────────

def _add_product_bar():
    tab_topic, tab_shopee = st.tabs(["Tạo từ chủ đề", "Từ link Shopee"])
    with tab_topic:
        _add_by_topic()
    with tab_shopee:
        _add_by_shopee()


def _add_by_topic():
    ss = st.session_state
    gen = ss.setdefault("topic_gen", 0)
    busy = bool(ss.get("topic_busy"))
    touched_key = f"topic_touched_{gen}"
    niches = content_svc.niche_labels()

    with st.container(key="af-form-topic"):
        st.caption("Sinh loạt video mang giá trị theo ngách. Sản phẩm chỉ được gợi ý ở bình luận.")

        niche_label = st.selectbox(
            "Ngách", list(niches.values()), key=f"topic_niche_{gen}", disabled=busy,
        )

        topic = ss.get(f"topic_text_{gen}", "")
        error = _validate_topic(topic) if ss.get(touched_key) else ""
        with st.container(key=f"af-err-topic-{gen}" if error else f"af-fld-topic-{gen}"):
            topic = st.text_input(
                "Chủ đề", key=f"topic_text_{gen}", disabled=busy, max_chars=200,
                placeholder="Ví dụ: mẹo tiết kiệm điện",
                on_change=_mark_touched, args=(touched_key,),
            )
            if error:
                theme.field_error(error)
            else:
                theme.field_help("Một chủ đề cụ thể cho kết quả tốt hơn, 3–120 ký tự.")

        page_opts = _page_options()
        page_name = st.selectbox(
            "Page", list(page_opts.keys()), key=f"topic_page_{gen}", disabled=busy,
        )
        count = st.number_input(
            "Số video", min_value=5, max_value=30, value=10,
            key=f"topic_count_{gen}", disabled=busy,
        )

        clicked = st.button(
            "Đang sinh video…" if busy else "Sinh loạt video",
            key=f"topic_submit_{gen}", type="primary", disabled=busy,
        )

        if clicked:
            ss[touched_key] = True
            if not _validate_topic(topic):
                ss["topic_busy"] = True
            st.rerun()

        if busy:
            niche_key = next((k for k, v in niches.items() if v == niche_label), "")
            product_id = store.add_product(
                shopee_url="", page_id=page_opts.get(page_name), script_count=int(count),
                source_type="topic", niche=niche_key, name=topic.strip(),
            )
            with st.spinner(f"AI đang viết {int(count)} kịch bản. Việc này có thể mất vài phút…"):
                try:
                    content_svc.run_topic_analysis(product_id)
                    ss["pipeline_flash"] = (
                        "success", f"Đã sinh xong loạt video cho chủ đề “{topic.strip()}”.")
                except Exception as e:
                    store.update_product(product_id, status="error")
                    ss["pipeline_flash"] = (
                        "error",
                        f"Không sinh được nội dung ({e}). Kiểm tra LLM đang chạy trong tab "
                        "Cài đặt rồi bấm “Tạo lại kịch bản” ở sản phẩm bên dưới.")
            ss["expanded_product"] = product_id
            ss["topic_busy"] = False
            ss["topic_gen"] = gen + 1  # làm trống form cho lần nhập kế tiếp
            st.rerun()


def _add_by_shopee():
    ss = st.session_state
    gen = ss.setdefault("shopee_gen", 0)
    busy = bool(ss.get("shopee_busy"))
    touched_key = f"shopee_touched_{gen}"

    with st.container(key="af-form-shopee"):
        st.caption("Phân tích một sản phẩm Shopee rồi viết kịch bản bán hàng trực tiếp.")

        url = ss.get(f"shopee_url_{gen}", "")
        error = _validate_shopee_url(url) if ss.get(touched_key) else ""
        with st.container(key=f"af-err-shopee-{gen}" if error else f"af-fld-shopee-{gen}"):
            url = st.text_input(
                "Link Shopee", key=f"shopee_url_{gen}", disabled=busy,
                placeholder="https://shopee.vn/...",
                on_change=_mark_touched, args=(touched_key,),
            )
            if error:
                theme.field_error(error)
            else:
                theme.field_help("Dán link sản phẩm hoặc link affiliate của Shopee.")

        page_opts = _page_options()
        page_name = st.selectbox(
            "Page", list(page_opts.keys()), key=f"shopee_page_{gen}", disabled=busy,
        )
        script_count = st.number_input(
            "Số video", min_value=5, max_value=10, value=5,
            key=f"shopee_count_{gen}", disabled=busy,
        )

        clicked = st.button(
            "Đang phân tích…" if busy else "Phân tích và tạo kịch bản",
            key=f"shopee_submit_{gen}", type="primary", disabled=busy,
        )

        if clicked:
            ss[touched_key] = True
            if not _validate_shopee_url(url):
                ss["shopee_busy"] = True
            st.rerun()

        if busy:
            product_id = store.add_product(
                url.strip(), page_opts.get(page_name), int(script_count))
            with st.spinner("AI đang phân tích sản phẩm và viết kịch bản…"):
                try:
                    shopee_svc.run_product_analysis(product_id)
                    ss["pipeline_flash"] = ("success", "Đã tạo kịch bản cho sản phẩm.")
                except Exception as e:
                    store.update_product(product_id, status="error")
                    ss["pipeline_flash"] = (
                        "error",
                        f"Không phân tích được sản phẩm ({e}). Kiểm tra LLM trong tab Cài đặt "
                        "rồi bấm “Tạo lại kịch bản” ở sản phẩm bên dưới.")
            ss["expanded_product"] = product_id
            ss["shopee_busy"] = False
            ss["shopee_gen"] = gen + 1
            st.rerun()


# ── Nhập hàng loạt ─────────────────────────────────────────────────────────────

def _batch_import():
    """Nhập hàng loạt: nhiều link Shopee (mỗi dòng 1 link) hoặc file CSV."""
    with st.expander("Nhập hàng loạt nhiều link Shopee"):
        with st.container(key="af-form-batch"):
            page_options = _page_options()
            batch_page = st.selectbox(
                "Page áp dụng cho cả lô", options=list(page_options.keys()), key="batch_page",
            )
            batch_count = st.number_input(
                "Số video mỗi sản phẩm", min_value=5, max_value=10, value=5, key="batch_count",
            )
            text = st.text_area(
                "Danh sách link (mỗi dòng một link)", height=120, key="batch_text",
                placeholder="https://shopee.vn/sp1\nhttps://shopee.vn/sp2",
            )
            uploaded = st.file_uploader(
                "Hoặc tải file CSV (cột đầu tiên là link)", type=["csv", "txt"], key="batch_csv",
            )

            urls: list[str] = []
            if text.strip():
                urls += [ln.strip() for ln in text.splitlines() if ln.strip()]
            if uploaded is not None:
                content = uploaded.getvalue().decode("utf-8", errors="ignore")
                for row in csv.reader(io.StringIO(content)):
                    if row and row[0].strip().startswith("http"):
                        urls.append(row[0].strip())

            seen = set()
            urls = [u for u in urls if not (u in seen or seen.add(u))]
            valid = [u for u in urls if not _validate_shopee_url(u)]
            invalid = len(urls) - len(valid)

            if invalid:
                theme.field_error(
                    f"{invalid} dòng không phải link Shopee và sẽ bị bỏ qua. "
                    "Mỗi dòng cần một link bắt đầu bằng https://shopee.vn/...")
            elif valid:
                theme.field_help(f"Sẵn sàng tạo {len(valid)} sản phẩm.")
            else:
                theme.field_help("Dán ít nhất một link để bật nút tạo.")

            if st.button(f"Tạo {len(valid)} sản phẩm" if valid else "Tạo hàng loạt",
                         key="batch_submit", type="primary", disabled=not valid):
                page_id = page_options.get(batch_page)
                progress = st.progress(0.0, text="Đang xử lý…")
                ok = fail = 0
                for i, u in enumerate(valid, 1):
                    try:
                        pid = store.add_product(u, page_id, int(batch_count))
                        shopee_svc.run_product_analysis(pid)
                        ok += 1
                    except Exception:
                        fail += 1
                    progress.progress(i / len(valid), text=f"Đã xử lý {i}/{len(valid)}")
                st.session_state["pipeline_flash"] = (
                    "success" if not fail else "error",
                    f"Hoàn tất: {ok} sản phẩm thành công, {fail} lỗi.")
                st.rerun()


# ── Bộ lọc ─────────────────────────────────────────────────────────────────────

def _toolbar():
    products = store.list_products()
    total = len(products)
    posted = sum(1 for p in products if p["status"] == "posted")
    st.caption(f"{total} sản phẩm · {posted} đã hoàn tất")

    col_search, col_filter, col_export = st.columns([3, 2, 1], vertical_alignment="bottom")
    with col_search:
        st.session_state.setdefault("pipeline_search", "")
        st.text_input("Tìm sản phẩm", placeholder="Tên sản phẩm hoặc chủ đề",
                      key="pipeline_search")
    with col_filter:
        status_opts = ["Tất cả"] + list(dict.fromkeys(_STATUS_LABEL.values()))
        st.selectbox("Trạng thái", status_opts, key="pipeline_status_filter")
    with col_export:
        st.download_button(
            "Xuất CSV", _products_csv(products), "products.csv", "text/csv",
            use_container_width=True, disabled=not products,
        )


def _products_csv(products: list[dict]) -> str:
    buf = io.StringIO()
    fields = ["id", "name", "price", "shopee_url", "status", "page_name", "created_at"]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for p in products:
        writer.writerow({k: p.get(k, "") for k in fields})
    return buf.getvalue()


# ── Danh sách sản phẩm ─────────────────────────────────────────────────────────

def _product_table():
    products = store.list_products()

    search = st.session_state.get("pipeline_search", "").lower()
    status_filter = st.session_state.get("pipeline_status_filter", "Tất cả")

    if search:
        products = [p for p in products if search in (p.get("name") or p["shopee_url"]).lower()]
    if status_filter != "Tất cả":
        keys = {k for k, v in _STATUS_LABEL.items() if v == status_filter}
        products = [p for p in products if p["status"] in keys]

    if not products:
        st.info("Chưa có sản phẩm nào khớp. Tạo loạt video đầu tiên bằng form phía trên.")
        return

    for product in products:
        _product_row(product)


def _product_row(product: dict):
    pid = product["id"]
    name = product.get("name") or product["shopee_url"]
    status = product.get("status", "pending")
    status_label = _STATUS_LABEL.get(status, status)
    page_name = product.get("page_name") or "chưa chọn Page"

    with st.expander(
        f"{name[:60]} — {status_label} · {page_name}",
        expanded=(pid == st.session_state.get("expanded_product")),
    ):
        col_meta, col_refresh, col_del = st.columns([4, 1.4, 1.4], vertical_alignment="center")
        with col_meta:
            parts = [p for p in (product.get("price"), product.get("shopee_url")) if p]
            if parts:
                st.caption(" · ".join(str(p)[:80] for p in parts))
        with col_refresh:
            if st.button("Tạo lại kịch bản", key=f"refresh_prod_{pid}", use_container_width=True):
                for c in store.list_campaigns(pid):
                    store.delete_campaign(c["id"])
                store.update_product(pid, status="analyzing", insights="")
                with st.spinner("Đang tạo lại kịch bản…"):
                    try:
                        _analyze_dispatch(pid)
                    except Exception as e:
                        store.update_product(pid, status="error")
                        st.session_state["pipeline_flash"] = (
                            "error", f"Không tạo lại được ({e}). Kiểm tra LLM trong tab Cài đặt.")
                st.session_state["expanded_product"] = pid
                st.rerun()
        with col_del:
            if st.button("Xoá sản phẩm", key=f"del_prod_{pid}", use_container_width=True):
                store.delete_product(pid)
                st.rerun()

        if status == "analyzing":
            st.info("AI đang phân tích và viết kịch bản. Tải lại trang sau ít phút.")
            return

        # Scrape Shopee thất bại → cho nhập tên thủ công
        if not product.get("name"):
            with st.container(key=f"af-form-name-{pid}"):
                new_name = st.text_input("Tên sản phẩm", key=f"name_{pid}",
                                         placeholder="Ví dụ: Kem chống nắng Anessa SPF50+")
                theme.field_help("Không đọc được tên từ Shopee. Nhập tên để AI phân tích.")
                if st.button("Lưu tên và phân tích", key=f"save_name_{pid}", type="primary",
                             disabled=not new_name.strip()):
                    store.update_product(pid, name=new_name.strip(), status="analyzing")
                    with st.spinner("Đang phân tích…"):
                        try:
                            shopee_svc.run_product_analysis(pid)
                        except Exception as e:
                            store.update_product(pid, status="error")
                            st.session_state["pipeline_flash"] = (
                                "error", f"Không phân tích được ({e}).")
                    st.rerun()
            return

        _render_analysis(product)

        campaigns = store.list_campaigns(pid)
        if not campaigns:
            st.caption("Chưa có kịch bản. Bấm “Tạo lại kịch bản” để sinh.")
            return

        _campaign_grid(pid, campaigns, product)


def _render_analysis(product: dict):
    """Hiển thị kết quả phân tích sản phẩm (products.insights)."""
    try:
        a = json.loads(product.get("insights") or "")
    except Exception:
        return
    if not isinstance(a, dict) or not a:
        return

    rows = [
        ("Ngách", a.get("niche")), ("Chủ đề", a.get("topic")),
        ("Ngành hàng", a.get("category")), ("Khách hàng", a.get("target_audience")),
        ("Nhân khẩu học", a.get("demographics")), ("Điểm đau", a.get("pain_points")),
        ("Mong muốn", a.get("desires")), ("USP", a.get("usps")),
        ("Trigger cảm xúc", a.get("emotional_triggers")), ("Lý do do dự", a.get("objections")),
        ("Tình huống dùng", a.get("use_cases")), ("Giọng điệu", a.get("tone")),
    ]
    rows = [(label, val) for label, val in rows if val]
    if not rows:
        return

    with st.expander("Phân tích của AI"):
        html = "".join(
            f"<p><strong>{theme.esc(label)}:</strong> "
            f"{theme.esc(' · '.join(map(str, val)) if isinstance(val, list) else val)}</p>"
            for label, val in rows
        )
        st.markdown(html, unsafe_allow_html=True)


# ── Danh sách video ────────────────────────────────────────────────────────────

def _campaign_grid(product_id: int, campaigns: list[dict], product: dict):
    """Mỗi video là một card: chọn · thumbnail · nội dung · hành động."""
    pages = store.list_pages()
    page = next((p for p in pages if p["id"] == product.get("page_id")), None)

    counts = {s: 0 for s in _ALL_STATUSES}
    for c in campaigns:
        key = c.get("status", "draft")
        counts[key] = counts.get(key, 0) + 1
    legend = "".join(
        theme.chip(f"{_CAMPAIGN_STATUS_LABEL[s]}: {counts[s]}",
                   _STATUS_CHIP_VARIANT.get(s, "") if counts[s] else "is-quiet")
        for s in _ALL_STATUSES
    )
    st.markdown(
        f"<p><strong>{len(campaigns)} video</strong></p><div>{legend}</div>",
        unsafe_allow_html=True,
    )

    _bulk_action_bar(product_id, campaigns, page)

    for camp in campaigns:
        _campaign_row(camp, product, page)


def _bulk_action_bar(product_id: int, campaigns: list[dict], page: dict | None):
    """Chọn nhiều video + thực hiện hành động hàng loạt."""
    selected = [c for c in campaigns if st.session_state.get(f"sel_{c['id']}")]
    n_sel = len(selected)
    test_mode = store.get_setting("test_mode", "") == "1"

    cols = st.columns([1.2, 1.2, 1.6, 1.4, 1.2])

    with cols[0]:
        if st.button("Chọn tất cả", key=f"selall_{product_id}", use_container_width=True):
            for c in campaigns:
                st.session_state[f"sel_{c['id']}"] = True
            st.rerun()
    with cols[1]:
        if st.button("Bỏ chọn", key=f"selnone_{product_id}", use_container_width=True,
                     disabled=not selected):
            for c in campaigns:
                st.session_state[f"sel_{c['id']}"] = False
            st.rerun()

    with cols[2]:
        drafts = [c for c in selected if c.get("status") == "draft"]
        if st.button(f"Tạo video ({len(drafts)})", key=f"bulkrender_{product_id}",
                     use_container_width=True, type="primary", disabled=not drafts):
            with st.spinner(f"Đang khởi động {len(drafts)} video…"):
                for c in drafts:
                    tid = video_client.start_video_task(c["id"])
                    if tid and not test_mode:
                        threading.Thread(target=video_client.sync_campaign_video,
                                         args=(c["id"],), daemon=True).start()
            st.session_state["expanded_product"] = product_id
            st.rerun()

    with cols[3]:
        sched = [c for c in selected if c.get("status") == "scheduled"]
        post_disabled = not sched or not (page or test_mode)
        if st.button(f"Đăng ({len(sched)})", key=f"bulkpost_{product_id}",
                     use_container_width=True, disabled=post_disabled):
            ok = fail = 0
            with st.spinner(f"Đang đăng {len(sched)} video…"):
                for c in sched:
                    try:
                        fb_svc.post_campaign(c["id"])
                        ok += 1
                    except Exception:
                        fail += 1
            st.session_state["pipeline_flash"] = (
                "success" if not fail else "error",
                f"Đăng xong: {ok} thành công, {fail} lỗi.")
            st.session_state["expanded_product"] = product_id
            st.rerun()

    with cols[4]:
        if st.button(f"Xoá ({n_sel})", key=f"bulkdel_{product_id}",
                     use_container_width=True, disabled=not selected):
            for c in selected:
                store.delete_campaign(c["id"])
                st.session_state.pop(f"sel_{c['id']}", None)
            st.session_state["expanded_product"] = product_id
            st.rerun()

    if n_sel:
        st.caption(f"Đã chọn {n_sel} video.")
    else:
        st.caption("Tích chọn video để tạo, đăng hoặc xoá nhiều video cùng lúc.")


def _campaign_row(camp: dict, product: dict, page: dict | None):
    cid = camp["id"]
    hook_type = camp.get("hook_type", "") or "video"
    status = camp.get("status", "draft")
    status_label = _CAMPAIGN_STATUS_LABEL.get(status, status)
    hook_text = camp.get("hook_text", "") or ""
    test_mode = store.get_setting("test_mode", "") == "1"

    with st.container(key=f"af-row-{cid}"):
        c_sel, c_thumb, c_main, c_act = st.columns([0.4, 1, 4, 2])

        with c_sel:
            st.checkbox(f"Chọn video: {hook_text[:40] or cid}", key=f"sel_{cid}",
                        label_visibility="collapsed")

        with c_thumb:
            if camp.get("video_path"):
                st.video(camp["video_path"])
            else:
                st.markdown("<div class='af-thumb'>Chưa render</div>", unsafe_allow_html=True)

        with c_main:
            st.markdown(
                theme.chip(hook_type)
                + theme.chip(status_label, _STATUS_CHIP_VARIANT.get(status, ""))
                + f"<p class='af-hook'>{theme.esc(hook_text)}</p>",
                unsafe_allow_html=True,
            )
            with st.expander("Sửa kịch bản và caption"):
                hook = st.text_area("Câu mở đầu (hook)", value=hook_text,
                                    height=70, key=f"hook_{cid}")
                script = st.text_area("Kịch bản", value=camp.get("script", ""),
                                      height=160, key=f"script_{cid}")
                if st.button("Lưu kịch bản", key=f"save_script_{cid}"):
                    store.update_campaign(cid, hook_text=hook, script=script)
                    st.success("Đã lưu kịch bản.")

                # Caption (giá trị, KHÔNG link) + Comment (chứa link) — monetize mềm
                if status in ("scheduled", "posted"):
                    new_caption = st.text_area(
                        "Caption (không chứa link)",
                        value=caption_svc.ensure_caption(cid), height=100, key=f"caption_{cid}",
                    )
                    new_comment = st.text_area(
                        "Bình luận đầu tiên (chứa link affiliate, tự ghim)",
                        value=caption_svc.ensure_comment(cid), height=70, key=f"comment_{cid}",
                        help="Link đặt ở bình luận để tránh nền tảng bóp reach.",
                    )
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Lưu caption", key=f"save_cap_{cid}",
                                     use_container_width=True):
                            store.update_campaign(
                                cid, caption=new_caption, comment_text=new_comment)
                            st.success("Đã lưu caption và bình luận.")
                    with cc2:
                        if st.button("Tạo lại caption", key=f"regen_cap_{cid}",
                                     use_container_width=True):
                            pf = store.get_product(camp["product_id"])
                            store.update_campaign(
                                cid,
                                caption=caption_svc.build_value_caption(camp),
                                comment_text=caption_svc.build_comment(camp, pf or {}),
                            )
                            st.rerun()

        with c_act:
            if status == "draft":
                if st.button("Tạo video", key=f"render_{cid}", use_container_width=True,
                             type="primary"):
                    task_id = video_client.start_video_task(cid)
                    if task_id:
                        if not test_mode:
                            threading.Thread(target=video_client.sync_campaign_video,
                                             args=(cid,), daemon=True).start()
                    else:
                        st.session_state["pipeline_flash"] = (
                            "error",
                            "Không khởi động được render. Kiểm tra API server đang chạy "
                            "và địa chỉ API trong tab Cài đặt.")
                    st.session_state["expanded_product"] = camp["product_id"]
                    st.rerun()

            elif status == "rendering":
                progress = 0
                if camp.get("task_id"):
                    progress = video_client.poll_task(camp["task_id"]).get("progress", 0)
                st.progress(min(max(progress, 0), 100) / 100, text=f"Đang render {progress}%")

            elif status == "scheduled":
                if page or test_mode:
                    post_label = "Đăng (thử nghiệm)" if test_mode else "Đăng Reels"
                    if st.button(post_label, key=f"post_{cid}", use_container_width=True,
                                 type="primary"):
                        try:
                            fb_svc.post_campaign(cid)
                            st.session_state["pipeline_flash"] = ("success", "Đã đăng video.")
                        except Exception as e:
                            st.session_state["pipeline_flash"] = (
                                "error",
                                f"Không đăng được ({e}). Kiểm tra token của Page trong tab Cài đặt.")
                        st.session_state["expanded_product"] = camp["product_id"]
                        st.rerun()
                    with st.popover("Lên lịch", use_container_width=True):
                        sd = st.date_input("Ngày đăng", key=f"sched_date_{cid}")
                        stime = st.time_input("Giờ đăng", key=f"sched_time_{cid}")
                        if st.button("Lưu lịch", key=f"save_sched_{cid}"):
                            store.update_campaign(cid, scheduled_at=f"{sd} {stime}")
                            st.success("Đã lên lịch.")
                else:
                    st.caption("Chưa chọn Page. Thêm Page trong tab Cài đặt để đăng.")

            elif status == "error":
                if st.button("Thử lại", key=f"retry_{cid}", use_container_width=True):
                    store.update_campaign(cid, status="draft", task_id="", video_path="")
                    st.session_state["expanded_product"] = camp["product_id"]
                    st.rerun()

            elif status == "posted":
                st.caption(f"{camp.get('views', 0):,} lượt xem · {camp.get('likes', 0):,} lượt thích")
                if st.button("Cập nhật số liệu", key=f"sync_stats_{cid}",
                             use_container_width=True):
                    _sync_stats(cid, camp, page)

            if st.button("Xoá video", key=f"del_camp_{cid}", use_container_width=True):
                store.delete_campaign(cid)
                st.session_state["expanded_product"] = camp["product_id"]
                st.rerun()


def _sync_stats(campaign_id: int, campaign: dict, page: dict | None):
    if not page or not campaign.get("post_id"):
        st.warning("Video này chưa có mã bài đăng nên chưa lấy được số liệu.")
        return
    stats = fb_svc.get_reel_insights(campaign["post_id"], page["page_id"])
    if stats:
        store.update_campaign(
            campaign_id, views=stats.get("views", 0), likes=stats.get("likes", 0))
        st.success(f"{stats.get('views', 0):,} lượt xem · {stats.get('likes', 0):,} lượt thích")
    else:
        st.warning("Facebook chưa trả về số liệu. Thử lại sau vài phút.")
