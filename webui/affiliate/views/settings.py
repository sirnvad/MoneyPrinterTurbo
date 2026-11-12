"""Settings tab — chế độ thử nghiệm, kết nối API, video, Facebook Pages, affiliate."""

import os
from pathlib import Path

import requests
import streamlit as st

from webui.affiliate import theme
from webui.affiliate.store import db as store
from webui.affiliate.services import facebook as fb_svc

_VIDEO_SOURCES = ["pexels", "pixabay", "coverr", "local_cache"]
_ASPECTS = ["9:16", "16:9", "1:1"]
_VOICE_NAMES_VI = ["vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural", ""]


def render():
    test_on = store.get_setting("test_mode", "") == "1"
    new_val = st.toggle(
        "Chế độ thử nghiệm",
        value=test_on,
        help="Giả lập viết kịch bản, render và đăng bài để thử toàn bộ luồng mà không gọi "
             "LLM, backend video hay Facebook.",
    )
    if new_val != test_on:
        store.set_setting("test_mode", "1" if new_val else "0")
        st.rerun()
    if new_val:
        st.warning("Đang bật chế độ thử nghiệm: video không được render thật và không đăng lên Facebook.")

    tab_llm, tab_video, tab_fb, tab_shopee = st.tabs(
        ["Kết nối API", "Video", "Facebook Pages", "Affiliate"]
    )
    with tab_llm:
        _llm_settings()
    with tab_video:
        _video_settings()
    with tab_fb:
        _facebook_settings()
    with tab_shopee:
        _shopee_settings()


def _index(options: list, value, default: int = 0) -> int:
    return options.index(value) if value in options else default


# ── Kết nối API ────────────────────────────────────────────────────────────────

def _validate_api_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "Chưa có địa chỉ API. Nhập địa chỉ backend, mặc định là http://localhost:8080."
    if not value.lower().startswith(("http://", "https://")):
        return "Địa chỉ phải bắt đầu bằng http:// hoặc https://, ví dụ http://localhost:8080."
    return ""


def _llm_settings():
    with st.container(key="af-form-api"):
        st.caption("LLM dùng chung cấu hình với MoneyPrinterTurbo (file config.toml hoặc giao diện gốc).")
        s = store.get_all_settings()

        current = st.session_state.get("api_base_url", s.get("api_base_url", "http://localhost:8080"))
        error = _validate_api_url(current)
        with st.container(key="af-err-api" if error else "af-fld-api"):
            api_base = st.text_input(
                "Địa chỉ API của MoneyPrinterTurbo",
                value=s.get("api_base_url", "http://localhost:8080"),
                key="api_base_url",
            )
            if error:
                theme.field_error(error)
            else:
                theme.field_help("Backend tạo video, thường chạy ở cổng 8080.")

        if st.button("Lưu địa chỉ API", key="save_llm", type="primary", disabled=bool(error)):
            store.set_setting("api_base_url", api_base.strip().rstrip("/"))
            st.success("Đã lưu địa chỉ API.")

        if st.button("Kiểm tra kết nối", key="check_api", disabled=bool(error)):
            with st.spinner("Đang kiểm tra kết nối…"):
                try:
                    r = requests.get(f"{api_base.strip().rstrip('/')}/docs", timeout=5)
                    ok = r.status_code < 400
                    detail = f"máy chủ trả về mã {r.status_code}"
                except Exception as e:
                    ok, detail = False, str(e)
            if ok:
                st.success(f"Kết nối được tới {api_base}.")
            else:
                st.error(
                    f"Không kết nối được ({detail}). Chạy backend bằng lệnh "
                    "“python main.py” rồi kiểm tra lại địa chỉ và cổng.")


# ── Video ──────────────────────────────────────────────────────────────────────

def _video_settings():
    s = store.get_all_settings()
    with st.container(key="af-form-video"):
        video_source = st.selectbox(
            "Nguồn video", _VIDEO_SOURCES, index=_index(_VIDEO_SOURCES, s.get("video_source")),
            help="local_cache dùng lại các video đã tải trong storage/cache_videos.",
        )
        video_aspect = st.selectbox(
            "Tỷ lệ video", _ASPECTS, index=_index(_ASPECTS, s.get("video_aspect")),
        )
        clip_duration = st.number_input(
            "Thời lượng mỗi clip (giây)", min_value=3, max_value=15,
            value=min(max(int(s.get("video_clip_duration", 5)), 3), 15),
        )

        font_dir = Path(__file__).parent.parent.parent.parent / "resource" / "fonts"
        fonts = (
            sorted(f for f in os.listdir(font_dir) if f.endswith((".ttf", ".ttc")))
            if font_dir.exists() else []
        )
        current_font = s.get("font_name", "STHeitiMedium.ttc")
        if fonts:
            font_name = st.selectbox("Font phụ đề", fonts, index=_index(fonts, current_font))
        else:
            font_name = st.text_input("Font phụ đề", current_font)

        voice_name = st.selectbox(
            "Giọng đọc", _VOICE_NAMES_VI,
            index=_index(_VOICE_NAMES_VI, s.get("voice_name", "")),
            format_func=lambda v: v or "Mặc định của hệ thống",
        )
        bgm_volume = st.slider(
            "Âm lượng nhạc nền", 0.0, 1.0, float(s.get("bgm_volume", 0.2)), 0.05,
        )

        if st.button("Lưu cài đặt video", key="save_video", type="primary"):
            for key, val in {
                "video_source": video_source,
                "video_aspect": video_aspect,
                "video_clip_duration": clip_duration,
                "font_name": font_name,
                "voice_name": voice_name,
                "bgm_volume": bgm_volume,
            }.items():
                store.set_setting(key, str(val))
            st.success("Đã lưu cài đặt video.")


# ── Facebook Pages ─────────────────────────────────────────────────────────────

def _required(value: str, what: str, how: str) -> str:
    return "" if (value or "").strip() else f"Chưa có {what}. {how}"


def _mark_touched(flag_key: str):
    st.session_state[flag_key] = True


def _facebook_settings():
    ss = st.session_state
    st.markdown("**Page đã kết nối**")
    pages = store.list_pages()
    if pages:
        for p in pages:
            with st.container(key=f"af-row-page-{p['id']}"):
                col_name, col_del = st.columns([5, 1], vertical_alignment="center")
                col_name.markdown(
                    f"{theme.esc(p['name'])}<br><span class='af-help'>ID {theme.esc(p['page_id'])}</span>",
                    unsafe_allow_html=True,
                )
                if col_del.button("Xoá Page", key=f"del_page_{p['page_id']}",
                                  use_container_width=True):
                    store.delete_page(p["page_id"])
                    st.rerun()
    else:
        st.caption("Chưa có Page nào. Thêm Page bằng form bên dưới.")

    st.divider()
    st.markdown("**Thêm Page mới**")
    gen = ss.setdefault("page_gen", 0)
    fields = [
        ("name", "Tên Page", "Tên hiển thị trong công cụ, ví dụ: Mẹo nhà cửa.",
         "Nhập tên để nhận ra Page này, ví dụ: Mẹo nhà cửa.", {}),
        ("id", "Page ID", "Dãy số trong mục Giới thiệu → Tính minh bạch của Trang.",
         "Sao chép Page ID (dãy số) từ mục Giới thiệu của Trang trên Facebook.", {}),
        ("token", "Page Access Token", "Token dài hạn có quyền pages_manage_posts.",
         "Tạo Page Access Token trong Graph API Explorer rồi dán vào đây.",
         {"type": "password"}),
    ]
    values = {}
    with st.container(key="af-form-page"):
        for fid, label, hint, how, extra in fields:
            key = f"page_{fid}_{gen}"
            touched = f"page_touched_{fid}_{gen}"
            error = _required(ss.get(key, ""), label, how) if ss.get(touched) else ""
            with st.container(key=f"af-err-page-{fid}-{gen}" if error else f"af-fld-page-{fid}-{gen}"):
                values[fid] = st.text_input(
                    label, key=key, on_change=_mark_touched, args=(touched,), **extra)
                theme.field_error(error) if error else theme.field_help(hint)

        missing = [f for f in fields if not values[f[0]].strip()]

        if st.button("Kiểm tra token", key=f"verify_page_{gen}"):
            for f in fields[1:]:
                ss[f"page_touched_{f[0]}_{gen}"] = True
            if values["id"].strip() and values["token"].strip():
                with st.spinner("Đang kiểm tra token…"):
                    ok, name = fb_svc.validate_page_token(values["id"].strip(), values["token"].strip())
                if ok:
                    st.success(f"Token hợp lệ cho Page “{name}”.")
                else:
                    st.error(
                        f"Token không dùng được ({name}). Tạo lại Page Access Token và "
                        "kiểm tra Page ID khớp với Trang.")
            else:
                st.rerun()

        if st.button("Thêm Page", key=f"add_page_{gen}", type="primary"):
            for f in fields:
                ss[f"page_touched_{f[0]}_{gen}"] = True
            if not missing:
                store.add_page(values["name"].strip(), values["id"].strip(), values["token"].strip())
                ss["page_gen"] = gen + 1
            st.rerun()

    st.divider()
    with st.container(key="af-form-autopost"):
        auto_post_hour = st.slider(
            "Giờ đăng mặc định", min_value=6, max_value=23,
            value=int(store.get_setting("auto_post_hour", "19")),
            help="Giờ gợi ý khi lên lịch đăng video.",
        )
        if st.button("Lưu giờ đăng", key="save_fb"):
            store.set_setting("auto_post_hour", str(auto_post_hour))
            st.success("Đã lưu giờ đăng.")


# ── Affiliate ──────────────────────────────────────────────────────────────────

def _shopee_settings():
    s = store.get_all_settings()
    with st.container(key="af-form-affiliate"):
        st.caption("Caption mang giá trị và không chứa link. Link affiliate nằm ở bình luận ghim.")

        default_link = st.text_input(
            "Link affiliate mặc định",
            value=s.get("default_affiliate_link", ""),
            placeholder="https://shopee.vn/...",
            help="Dùng cho video sinh từ chủ đề, vốn không có link sản phẩm riêng.",
        )
        tracking_id = st.text_input(
            "Tracking ID",
            value=s.get("shopee_tracking_id", ""),
            placeholder="vd: reels_thang11",
            help="Gắn vào link để biết click đến từ đâu.",
        )
        caption_cta = st.text_input(
            "Lời nhắc trong caption",
            value=s.get("caption_cta", "💬 Link sản phẩm mình để ở bình luận ghim 👇"),
        )
        comment_cta = st.text_input(
            "Lời dẫn trong bình luận",
            value=s.get("comment_cta", "🛒 Sản phẩm trong video nhé cả nhà:"),
        )
        default_hashtags = st.text_area(
            "Hashtag mặc định",
            value=s.get("default_hashtags", "#meohay #tips #review #shopee"),
            height=70,
        )

        with st.expander("Mẫu nâng cao"):
            caption_template = st.text_area(
                "Mẫu caption",
                value=s.get("caption_template", "{script_hook}\n\n{cta}\n\n{hashtags}"),
                height=90,
                help="Biến dùng được: {script_hook}, {cta}, {hashtags}",
            )
            comment_template = st.text_area(
                "Mẫu bình luận",
                value=s.get("comment_template", "{cta_comment}\n🔗 {affiliate_link}"),
                height=70,
                help="Biến dùng được: {cta_comment}, {affiliate_link}",
            )

        if st.button("Lưu cài đặt affiliate", key="save_shopee", type="primary"):
            for key, val in {
                "default_affiliate_link": default_link.strip(),
                "shopee_tracking_id": tracking_id.strip(),
                "caption_cta": caption_cta,
                "comment_cta": comment_cta,
                "default_hashtags": default_hashtags,
                "caption_template": caption_template,
                "comment_template": comment_template,
            }.items():
                store.set_setting(key, val)
            st.success("Đã lưu cài đặt affiliate.")
