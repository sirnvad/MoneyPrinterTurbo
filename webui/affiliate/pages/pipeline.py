"""
Pipeline tab — quản lý sản phẩm và kịch bản video.

Layout:
  1. Thanh nhập link Shopee (trên cùng)
  2. Toolbar: search, filter, export
  3. Bảng sản phẩm — mỗi dòng có thể expand xem kịch bản
  4. Panel chi tiết campaign (render video, đăng FB)
"""

import threading
from datetime import datetime

import streamlit as st

from webui.affiliate.store import db as store
from webui.affiliate.services import shopee as shopee_svc
from webui.affiliate.services import video_client
from webui.affiliate.services import facebook as fb_svc
from webui.affiliate.services import caption as caption_svc


# ── Status display helpers ─────────────────────────────────────────────────────

_STATUS_LABEL = {
    "pending":   "⏳ Chờ xử lý",
    "analyzing": "🔍 Đang phân tích",
    "scripted":  "📝 Có kịch bản",
    "rendering": "🎬 Đang render",
    "scheduled": "📅 Lên lịch",
    "posted":    "✅ Đã đăng",
    "error":     "❌ Lỗi",
    "draft":     "📋 Nháp",
}

_CAMPAIGN_STATUS_LABEL = {
    "draft":      "📋 Nháp",
    "rendering":  "🎬 Render...",
    "scheduled":  "📅 Lên lịch",
    "posted":     "✅ Đã đăng",
    "error":      "❌ Lỗi",
}


_PIPELINE_CSS = """
<style>
/* Expander sản phẩm trông như card */
[data-testid="stExpander"]{
  background:#161922;border:1px solid #262a38;border-radius:12px;margin-bottom:8px;
}
[data-testid="stExpander"] summary{font-size:14px;}
/* Chip hook + trạng thái */
.aff-chip{
  display:inline-block;padding:2px 9px;border-radius:11px;font-size:11px;
  font-weight:600;margin-right:6px;
}
.hk-curiosity{background:#1a2744;color:#64b5f6;}
.hk-shock{background:#3d1515;color:#ef9a9a;}
.hk-benefit{background:#1a3320;color:#81c784;}
.hk-story{background:#2d1f44;color:#ce93d8;}
.hk-compare{background:#3d2800;color:#ffb74d;}
.st-draft{background:#2d2b1a;color:#ffd54f;}
.st-rendering{background:#1a3320;color:#81c784;}
.st-scheduled{background:#3d2800;color:#ffb74d;}
.st-posted{background:#1a3a5c;color:#4fc3f7;}
.st-error{background:#3d1515;color:#ef9a9a;}
</style>
"""


def render():
    st.markdown(_PIPELINE_CSS, unsafe_allow_html=True)
    _add_product_bar()
    _batch_import()
    st.divider()
    _toolbar()
    _product_table()


# ── Add product bar ───────────────────────────────────────────────────────────

def _add_product_bar():
    st.markdown("### 🛒 Thêm sản phẩm Shopee")
    with st.form("add_product_form", clear_on_submit=True):
        col_url, col_page, col_count, col_btn = st.columns([4, 2, 1, 1])

        with col_url:
            url = st.text_input(
                "Link Shopee",
                placeholder="https://shopee.vn/... hoặc affiliate.shopee.vn/...",
                label_visibility="collapsed",
            )
        with col_page:
            pages = store.list_pages()
            page_options = {p["name"]: p["id"] for p in pages}
            page_options["— Chưa chọn page —"] = None
            selected_page_name = st.selectbox(
                "Page",
                options=list(page_options.keys()),
                label_visibility="collapsed",
            )
        with col_count:
            script_count = st.number_input(
                "Số kịch bản", min_value=1, max_value=5, value=3, label_visibility="collapsed"
            )
        with col_btn:
            submitted = st.form_submit_button("➕ Phân tích & Tạo", use_container_width=True, type="primary")

    if submitted:
        if not url.strip():
            st.error("Vui lòng nhập link Shopee.")
            return
        page_id = page_options.get(selected_page_name)
        product_id = store.add_product(url.strip(), page_id, int(script_count))
        # Chạy phân tích đồng bộ (Streamlit không tự refresh khi chạy thread nền)
        with st.spinner("🔍 AI đang phân tích sản phẩm và tạo kịch bản..."):
            try:
                shopee_svc.run_product_analysis(product_id)
            except Exception as e:
                store.update_product(product_id, status="error")
                st.error(f"Lỗi phân tích: {e}")
        st.session_state["expanded_product"] = product_id
        st.success(f"Đã tạo kịch bản cho sản phẩm (ID: {product_id})")
        st.rerun()


# ── Batch import ───────────────────────────────────────────────────────────────

def _batch_import():
    """Nhập hàng loạt: nhiều link Shopee (mỗi dòng 1 link) hoặc file CSV."""
    with st.expander("📦 Nhập hàng loạt (nhiều link / CSV)"):
        pages = store.list_pages()
        page_options = {p["name"]: p["id"] for p in pages}
        page_options["— Chưa chọn page —"] = None

        col_page, col_count = st.columns(2)
        with col_page:
            batch_page = st.selectbox(
                "Page áp dụng cho cả lô", options=list(page_options.keys()),
                key="batch_page",
            )
        with col_count:
            batch_count = st.number_input(
                "Số kịch bản / sản phẩm", min_value=1, max_value=5, value=3, key="batch_count"
            )

        st.caption("Dán mỗi link trên một dòng:")
        text = st.text_area(
            "Danh sách link", height=120, key="batch_text",
            placeholder="https://shopee.vn/sp1\nhttps://shopee.vn/sp2\n...",
            label_visibility="collapsed",
        )
        uploaded = st.file_uploader(
            "Hoặc tải CSV (cột đầu tiên là link)", type=["csv", "txt"], key="batch_csv"
        )

        urls: list[str] = []
        if text.strip():
            urls += [ln.strip() for ln in text.splitlines() if ln.strip()]
        if uploaded is not None:
            import csv, io
            content = uploaded.getvalue().decode("utf-8", errors="ignore")
            for row in csv.reader(io.StringIO(content)):
                if row and row[0].strip().startswith("http"):
                    urls.append(row[0].strip())

        # loại trùng, giữ thứ tự
        seen = set()
        urls = [u for u in urls if not (u in seen or seen.add(u))]

        if urls:
            st.info(f"Tìm thấy **{len(urls)}** link hợp lệ.")
        if st.button("🚀 Tạo hàng loạt", type="primary", disabled=not urls):
            page_id = page_options.get(batch_page)
            progress = st.progress(0.0)
            ok = fail = 0
            for i, u in enumerate(urls, 1):
                try:
                    pid = store.add_product(u, page_id, int(batch_count))
                    shopee_svc.run_product_analysis(pid)
                    ok += 1
                except Exception:
                    fail += 1
                progress.progress(i / len(urls))
            st.success(f"Hoàn tất: {ok} thành công, {fail} lỗi.")
            st.rerun()


# ── Toolbar ───────────────────────────────────────────────────────────────────

def _toolbar():
    products = store.list_products()
    col_info, col_search, col_filter, col_export = st.columns([2, 2, 1, 1])
    with col_info:
        total = len(products)
        posted = sum(1 for p in products if p["status"] == "posted")
        st.caption(f"{total} sản phẩm · {posted} đã hoàn tất")
    with col_search:
        st.session_state.setdefault("pipeline_search", "")
        st.text_input(
            "Tìm", placeholder="🔍 Tên sản phẩm...",
            key="pipeline_search", label_visibility="collapsed"
        )
    with col_filter:
        status_opts = ["Tất cả"] + list(_STATUS_LABEL.values())
        st.selectbox("Lọc", status_opts, key="pipeline_status_filter", label_visibility="collapsed")
    with col_export:
        if st.button("⬇ CSV", use_container_width=True):
            _export_csv(products)


def _export_csv(products: list[dict]):
    import csv, io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "name", "price", "shopee_url", "status", "page_name", "created_at"])
    writer.writeheader()
    for p in products:
        writer.writerow({k: p.get(k, "") for k in writer.fieldnames})
    st.download_button("📥 Tải CSV", buf.getvalue(), "products.csv", "text/csv")


# ── Product table ─────────────────────────────────────────────────────────────

def _product_table():
    products = store.list_products()

    search = st.session_state.get("pipeline_search", "").lower()
    status_filter = st.session_state.get("pipeline_status_filter", "Tất cả")

    if search:
        products = [p for p in products if search in (p.get("name") or p["shopee_url"]).lower()]
    if status_filter != "Tất cả":
        # reverse lookup status key from label
        rev = {v: k for k, v in _STATUS_LABEL.items()}
        if key := rev.get(status_filter):
            products = [p for p in products if p["status"] == key]

    if not products:
        st.info("Chưa có sản phẩm nào. Thêm link Shopee ở trên để bắt đầu.")
        return

    for product in products:
        _product_row(product)


def _product_row(product: dict):
    pid = product["id"]
    name = product.get("name") or product["shopee_url"]
    status = product.get("status", "pending")
    status_label = _STATUS_LABEL.get(status, status)
    page_name = product.get("page_name") or "—"

    with st.expander(
        f"{status_label}  |  **{name[:60]}**  |  {product.get('price','')}"
        f"  |  📘 {page_name}",
        expanded=(pid == st.session_state.get("expanded_product")),
    ):
        # Product meta row
        col_meta, col_actions = st.columns([4, 1])
        with col_meta:
            if product.get("price"):
                st.caption(f"💰 {product['price']}  ·  🔗 {product['shopee_url'][:60]}")
            else:
                st.caption(f"🔗 {product['shopee_url'][:80]}")

        with col_actions:
            col_del, col_refresh = st.columns(2)
            with col_del:
                if st.button("🗑", key=f"del_prod_{pid}", help="Xoá sản phẩm"):
                    store.delete_product(pid)
                    st.rerun()
            with col_refresh:
                if st.button("🔄", key=f"refresh_prod_{pid}", help="Phân tích lại"):
                    # Xoá kịch bản cũ rồi phân tích lại
                    for c in store.list_campaigns(pid):
                        store.delete_campaign(c["id"])
                    store.update_product(pid, status="analyzing", insights="")
                    with st.spinner("🔍 Đang phân tích lại..."):
                        try:
                            shopee_svc.run_product_analysis(pid)
                        except Exception as e:
                            store.update_product(pid, status="error")
                            st.error(f"Lỗi: {e}")
                    st.rerun()

        # Analyzing spinner
        if status == "analyzing":
            st.info("⏳ AI đang phân tích sản phẩm và tạo kịch bản...")
            return

        # Manual name edit if scraping failed
        if not product.get("name"):
            new_name = st.text_input("Tên sản phẩm (nhập thủ công):", key=f"name_{pid}")
            if st.button("Lưu tên", key=f"save_name_{pid}"):
                store.update_product(pid, name=new_name, status="analyzing")
                with st.spinner("🔍 Đang phân tích..."):
                    try:
                        shopee_svc.run_product_analysis(pid)
                    except Exception as e:
                        store.update_product(pid, status="error")
                        st.error(f"Lỗi: {e}")
                st.rerun()
            return

        # Phân tích sản phẩm (insights)
        _render_analysis(product)

        # Campaign list
        campaigns = store.list_campaigns(pid)
        if not campaigns:
            st.caption("Chưa có kịch bản. Đang tạo...")
            return

        _campaign_grid(pid, campaigns, product)


def _render_analysis(product: dict):
    """Hiển thị kết quả phân tích sản phẩm (products.insights)."""
    import json
    raw = product.get("insights") or ""
    if not raw:
        return
    try:
        a = json.loads(raw)
    except Exception:
        return
    if not isinstance(a, dict) or not a:
        return

    with st.expander("🔍 Phân tích sản phẩm (AI)", expanded=False):
        def _line(label, val):
            if not val:
                return
            if isinstance(val, list):
                val = " · ".join(str(x) for x in val)
            st.markdown(
                f"<div style='margin-bottom:6px'>"
                f"<span style='color:#888;font-size:12px'>{label}:</span> "
                f"<span style='font-size:13px'>{val}</span></div>",
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            _line("🏷️ Ngành hàng", a.get("category"))
            _line("🎯 Khách hàng", a.get("target_audience"))
            _line("👥 Nhân khẩu học", a.get("demographics"))
            _line("😣 Điểm đau", a.get("pain_points"))
            _line("✨ Mong muốn", a.get("desires"))
        with col2:
            _line("⭐ USP", a.get("usps"))
            _line("❤️ Trigger cảm xúc", a.get("emotional_triggers"))
            _line("🛑 Lý do do dự", a.get("objections"))
            _line("📦 Tình huống dùng", a.get("use_cases"))
            _line("🗣️ Giọng điệu", a.get("tone"))


# ── Campaign grid ─────────────────────────────────────────────────────────────

_HOOK_ICON = {
    "curiosity": "🤔", "shock": "😱", "benefit": "✅",
    "story": "📖", "compare": "⚖️",
}

def _campaign_grid(product_id: int, campaigns: list[dict], product: dict):
    cols = st.columns(len(campaigns))
    pages = store.list_pages()
    page = next((p for p in pages if p["id"] == product.get("page_id")), None)

    for idx, (col, camp) in enumerate(zip(cols, campaigns)):
        cid = camp["id"]
        hook_type = camp.get("hook_type", "")
        icon = _HOOK_ICON.get(hook_type, "🎬")
        status = camp.get("status", "draft")
        status_label = _CAMPAIGN_STATUS_LABEL.get(status, status)

        with col:
            st.markdown(
                f"<span class='aff-chip hk-{hook_type}'>{icon} {hook_type.capitalize()}</span>"
                f"<span class='aff-chip st-{status}'>{status_label}</span>",
                unsafe_allow_html=True,
            )
            # Hook text (editable)
            hook = st.text_area(
                "Hook",
                value=camp.get("hook_text", ""),
                height=80,
                key=f"hook_{cid}",
                label_visibility="collapsed",
            )

            # Script preview
            with st.expander("Xem kịch bản"):
                script = st.text_area(
                    "Kịch bản",
                    value=camp.get("script", ""),
                    height=200,
                    key=f"script_{cid}",
                )
                if st.button("💾 Lưu kịch bản", key=f"save_script_{cid}"):
                    store.update_campaign(
                        cid,
                        hook_text=st.session_state[f"hook_{cid}"],
                        script=st.session_state[f"script_{cid}"],
                    )
                    st.success("Đã lưu")

            # Video actions
            if status == "draft":
                if st.button("🎬 Tạo video", key=f"render_{cid}", use_container_width=True, type="primary"):
                    # Save latest edits first
                    store.update_campaign(cid, hook_text=hook, script=camp.get("script", ""))
                    test_mode = store.get_setting("test_mode", "") == "1"
                    task_id = video_client.start_video_task(cid)
                    if task_id:
                        if test_mode:
                            st.success("🧪 Đã giả lập render xong, sẵn sàng đăng.")
                        else:
                            st.success(f"Đang render... task: {task_id}")
                            # Poll trong thread nền (chỉ với backend thật)
                            t = threading.Thread(
                                target=video_client.sync_campaign_video,
                                args=(cid,), daemon=True,
                            )
                            t.start()
                    else:
                        st.error("Không thể khởi động task render. Kiểm tra API server.")
                    st.rerun()

            elif status == "rendering":
                st.info("⏳ Đang render video...")
                if camp.get("task_id"):
                    result = video_client.poll_task(camp["task_id"])
                    progress = result.get("progress", 0)
                    st.progress(progress / 100)

            elif status in ("scheduled", "error"):
                if camp.get("video_path"):
                    st.video(camp["video_path"])

                test_mode = store.get_setting("test_mode", "") == "1"
                if status == "scheduled" and (page or test_mode):
                    # ── Caption đăng bài (tự sinh, cho sửa) ──
                    current_caption = caption_svc.ensure_caption(cid)
                    new_caption = st.text_area(
                        "📝 Caption đăng bài",
                        value=current_caption,
                        height=140,
                        key=f"caption_{cid}",
                    )
                    cap_col1, cap_col2 = st.columns(2)
                    with cap_col1:
                        if st.button("💾 Lưu caption", key=f"save_cap_{cid}", use_container_width=True):
                            store.update_campaign(cid, caption=new_caption)
                            st.success("Đã lưu caption")
                    with cap_col2:
                        if st.button("🔄 Tạo lại", key=f"regen_cap_{cid}", use_container_width=True,
                                     help="Dựng lại caption từ template + link + hashtag"):
                            product_full = store.get_product(camp["product_id"])
                            store.update_campaign(
                                cid, caption=caption_svc.build_caption(camp, product_full or {})
                            )
                            st.rerun()

                    post_label = "🧪 Đăng (thử nghiệm)" if test_mode else "📤 Đăng Reels"
                    if st.button(post_label, key=f"post_{cid}", use_container_width=True, type="primary"):
                        store.update_campaign(cid, caption=new_caption)
                        try:
                            post_id = fb_svc.post_campaign(cid)
                            st.success(f"Đã đăng! Post ID: {post_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi đăng: {e}")

                    # Schedule picker
                    sched_col1, sched_col2 = st.columns(2)
                    with sched_col1:
                        sched_date = st.date_input("Ngày đăng", key=f"sched_date_{cid}")
                    with sched_col2:
                        sched_time = st.time_input("Giờ đăng", key=f"sched_time_{cid}")
                    if st.button("💾 Lưu lịch", key=f"save_sched_{cid}"):
                        scheduled_at = f"{sched_date} {sched_time}"
                        store.update_campaign(cid, scheduled_at=scheduled_at)
                        st.success(f"Lên lịch: {scheduled_at}")

                elif status == "error":
                    if st.button("🔄 Thử lại", key=f"retry_{cid}", use_container_width=True):
                        store.update_campaign(cid, status="draft", task_id="", video_path="")
                        st.rerun()

            elif status == "posted":
                st.success(f"✅ Đã đăng {camp.get('posted_at','')}")
                st.metric("👁 Views", camp.get("views", 0))
                if st.button("🔄 Cập nhật stats", key=f"sync_stats_{cid}"):
                    _sync_stats(cid, camp, page)

            # Delete button
            if st.button("🗑 Xoá", key=f"del_camp_{cid}", use_container_width=True):
                store.delete_campaign(cid)
                st.rerun()


def _sync_stats(campaign_id: int, campaign: dict, page: dict | None):
    if not page or not campaign.get("post_id"):
        st.warning("Không có post_id để lấy stats.")
        return
    stats = fb_svc.get_reel_insights(campaign["post_id"], page["page_id"])
    if stats:
        store.update_campaign(
            campaign_id,
            views=stats.get("views", 0),
            likes=stats.get("likes", 0),
        )
        st.success(f"Views: {stats.get('views',0)}, Likes: {stats.get('likes',0)}")
    else:
        st.warning("Không lấy được stats.")
