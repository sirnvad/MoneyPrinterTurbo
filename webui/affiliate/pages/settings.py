"""Settings tab — API keys, LLM, video config, Facebook Pages, Shopee affiliate."""

import streamlit as st

from webui.affiliate.store import db as store
from webui.affiliate.services import facebook as fb_svc


def render():
    # ── Chế độ thử nghiệm (dry-run) ──
    test_on = store.get_setting("test_mode", "") == "1"
    new_val = st.toggle(
        "🧪 Chế độ thử nghiệm (không gọi backend video & không đăng Facebook thật)",
        value=test_on,
        help="Bật để test toàn bộ luồng: render & đăng được giả lập, sinh số liệu mẫu.",
    )
    if new_val != test_on:
        store.set_setting("test_mode", "1" if new_val else "0")
        st.rerun()
    if new_val:
        st.warning("Đang ở **chế độ thử nghiệm** — video không render thật, không đăng lên Facebook.")
    st.divider()

    tab_llm, tab_video, tab_fb, tab_shopee = st.tabs(
        ["🤖 LLM / AI", "🎬 Video", "📘 Facebook Pages", "🛒 Shopee Affiliate"]
    )

    with tab_llm:
        _llm_settings()

    with tab_video:
        _video_settings()

    with tab_fb:
        _facebook_settings()

    with tab_shopee:
        _shopee_settings()


# ── LLM ───────────────────────────────────────────────────────────────────────

def _llm_settings():
    st.markdown("#### Cài đặt LLM")
    st.info("Cài đặt LLM dùng chung với MoneyPrinterTurbo. Chỉnh trong file `config.toml` hoặc qua giao diện gốc.")

    s = store.get_all_settings()

    api_base = st.text_input(
        "MoneyPrinterTurbo API URL",
        value=s.get("api_base_url", "http://localhost:8080"),
        help="URL của backend MoneyPrinterTurbo đang chạy",
    )

    if st.button("💾 Lưu", key="save_llm"):
        store.set_setting("api_base_url", api_base)
        st.success("Đã lưu")

    # Health check
    if st.button("🔌 Kiểm tra kết nối API"):
        import requests as req
        try:
            r = req.get(f"{api_base}/docs", timeout=5)
            if r.status_code < 400:
                st.success(f"✅ Kết nối OK — {api_base}")
            else:
                st.error(f"API trả về {r.status_code}")
        except Exception as e:
            st.error(f"❌ Không kết nối được: {e}")


# ── Video ─────────────────────────────────────────────────────────────────────

_VOICE_NAMES_VI = [
    "vi-VN-NamMinhNeural",
    "vi-VN-HoaiMyNeural",
    "",
]

def _video_settings():
    st.markdown("#### Cài đặt Video mặc định")
    s = store.get_all_settings()

    col1, col2 = st.columns(2)
    with col1:
        video_source = st.selectbox(
            "Nguồn video",
            ["pexels", "pixabay", "coverr", "local_cache"],
            index=["pexels", "pixabay", "coverr", "local_cache"].index(s.get("video_source", "pexels")),
        )
        video_aspect = st.selectbox(
            "Tỷ lệ video",
            ["9:16", "16:9", "1:1"],
            index=["9:16", "16:9", "1:1"].index(s.get("video_aspect", "9:16")),
        )
        clip_duration = st.number_input(
            "Thời lượng mỗi clip (giây)", min_value=3, max_value=15,
            value=int(s.get("video_clip_duration", 5)),
        )

    with col2:
        # Font list from resource/fonts/
        import os
        from pathlib import Path
        font_dir = Path(__file__).parent.parent.parent.parent / "resource" / "fonts"
        fonts = sorted([f for f in os.listdir(font_dir) if f.endswith((".ttf", ".ttc"))]) if font_dir.exists() else []
        current_font = s.get("font_name", "STHeitiMedium.ttc")
        font_idx = fonts.index(current_font) if current_font in fonts else 0
        font_name = st.selectbox("Font phụ đề", fonts, index=font_idx) if fonts else st.text_input("Font phụ đề", current_font)

        voice_name = st.selectbox(
            "Giọng đọc",
            _VOICE_NAMES_VI,
            index=_VOICE_NAMES_VI.index(s.get("voice_name", "")) if s.get("voice_name", "") in _VOICE_NAMES_VI else 0,
        )
        bgm_volume = st.slider("Âm lượng nhạc nền", 0.0, 1.0, float(s.get("bgm_volume", 0.2)), 0.05)

    if st.button("💾 Lưu cài đặt video", key="save_video"):
        for key, val in {
            "video_source": video_source,
            "video_aspect": video_aspect,
            "video_clip_duration": str(clip_duration),
            "font_name": font_name,
            "voice_name": voice_name,
            "bgm_volume": str(bgm_volume),
        }.items():
            store.set_setting(key, str(val))
        st.success("Đã lưu cài đặt video")


# ── Facebook Pages ────────────────────────────────────────────────────────────

def _facebook_settings():
    st.markdown("#### Facebook Pages đã kết nối")

    pages = store.list_pages()
    if pages:
        for p in pages:
            col_name, col_id, col_del = st.columns([3, 2, 1])
            col_name.markdown(f"**{p['name']}**")
            col_id.code(p["page_id"])
            if col_del.button("🗑", key=f"del_page_{p['page_id']}"):
                store.delete_page(p["page_id"])
                st.rerun()
    else:
        st.info("Chưa có Page nào. Thêm Page ở bên dưới.")

    st.divider()
    st.markdown("#### Thêm Page mới")

    with st.form("add_page_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            page_name = st.text_input("Tên Page (hiển thị trong tool)")
        with col2:
            page_id = st.text_input("Page ID")
        with col3:
            token = st.text_input("Page Access Token", type="password")

        col_verify, col_add = st.columns(2)
        with col_verify:
            verify = st.form_submit_button("🔌 Kiểm tra token")
        with col_add:
            add = st.form_submit_button("➕ Thêm Page", type="primary")

    if verify and page_id and token:
        ok, name = fb_svc.validate_page_token(page_id, token)
        if ok:
            st.success(f"✅ Token hợp lệ — Page: **{name}**")
        else:
            st.error(f"❌ Token không hợp lệ: {name}")

    if add:
        if not all([page_name, page_id, token]):
            st.error("Vui lòng điền đầy đủ Tên Page, Page ID và Token.")
        else:
            store.add_page(page_name, page_id, token)
            st.success(f"Đã thêm Page: {page_name}")
            st.rerun()

    st.divider()
    st.markdown("#### Cài đặt đăng tự động")
    s = store.get_all_settings()

    auto_post_hour = st.slider(
        "Giờ đăng tự động (giờ vàng)",
        min_value=6, max_value=23,
        value=int(s.get("auto_post_hour", "19")),
        help="Tool sẽ đăng video lên lịch vào giờ này mỗi ngày",
    )
    if st.button("💾 Lưu cài đặt đăng", key="save_fb"):
        store.set_setting("auto_post_hour", str(auto_post_hour))
        st.success("Đã lưu")


# ── Shopee Affiliate ──────────────────────────────────────────────────────────

def _shopee_settings():
    st.markdown("#### Shopee Affiliate — Monetize mềm")
    st.caption("Caption mang giá trị (không link), link affiliate đặt ở **comment** để tránh bóp reach.")
    s = store.get_all_settings()

    default_link = st.text_input(
        "Link affiliate mặc định (cho video theo chủ đề)",
        value=s.get("default_affiliate_link", ""),
        help="Dùng khi video sinh từ chủ đề (không có link sản phẩm riêng). Đặt link Shopee Affiliate của bạn.",
        placeholder="https://shopee.vn/... hoặc affiliate.shopee.vn/...",
    )
    tracking_id = st.text_input(
        "Tracking ID mặc định",
        value=s.get("shopee_tracking_id", ""),
        help="Gắn vào link để theo dõi nguồn click",
        placeholder="your_tracking_id",
    )

    col1, col2 = st.columns(2)
    with col1:
        caption_cta = st.text_input(
            "CTA trong caption",
            value=s.get("caption_cta", "💬 Link sản phẩm mình để ở bình luận ghim 👇"),
        )
    with col2:
        comment_cta = st.text_input(
            "CTA trong comment",
            value=s.get("comment_cta", "🛒 Sản phẩm trong video nhé cả nhà:"),
        )

    default_hashtags = st.text_area(
        "Hashtag mặc định (caption)",
        value=s.get("default_hashtags", "#meohay #tips #review #shopee"),
        height=70,
    )

    with st.expander("Template nâng cao"):
        caption_template = st.text_area(
            "Caption template",
            value=s.get("caption_template", "{script_hook}\n\n{cta}\n\n{hashtags}"),
            height=90,
            help="Biến: {script_hook}, {cta}, {hashtags}",
        )
        comment_template = st.text_area(
            "Comment template",
            value=s.get("comment_template", "{cta_comment}\n🔗 {affiliate_link}"),
            height=70,
            help="Biến: {cta_comment}, {affiliate_link}",
        )

    if st.button("💾 Lưu cài đặt Shopee", key="save_shopee"):
        for key, val in {
            "default_affiliate_link": default_link,
            "shopee_tracking_id": tracking_id,
            "caption_cta": caption_cta,
            "comment_cta": comment_cta,
            "default_hashtags": default_hashtags,
            "caption_template": caption_template,
            "comment_template": comment_template,
        }.items():
            store.set_setting(key, val)
        st.success("Đã lưu")
