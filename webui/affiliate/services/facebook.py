"""
Facebook Graph API — đăng Reels lên Page.

Quy trình đăng video (Reels):
  1. Upload video lên resumable upload endpoint → video_id
  2. Publish: POST /{page_id}/video_reels với video_id + caption

Docs: https://developers.facebook.com/docs/video-api/guides/reels-publishing
"""

import os
import time
from pathlib import Path

import requests

from webui.affiliate.store import db as store


GRAPH_API = "https://graph.facebook.com/v19.0"


def _page_token(page_id: str) -> str:
    pages = store.list_pages()
    for p in pages:
        if p["page_id"] == page_id:
            return p["token"]
    return ""


# ── Video upload ───────────────────────────────────────────────────────────────

def _init_upload_session(page_id: str, token: str, file_size: int) -> str:
    """Tạo upload session, trả về upload_url."""
    resp = requests.post(
        f"{GRAPH_API}/{page_id}/video_reels",
        params={"access_token": token},
        json={
            "upload_phase": "start",
            "file_size": file_size,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    video_id = data.get("video_id", "")
    upload_url = data.get("upload_url", "")
    return video_id, upload_url


def _upload_video_bytes(upload_url: str, token: str, video_bytes: bytes) -> bool:
    resp = requests.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {token}",
            "Content-Type": "application/octet-stream",
            "file_size": str(len(video_bytes)),
            "file_offset": "0",
        },
        data=video_bytes,
        timeout=300,
    )
    return resp.status_code == 200


def _publish_reel(page_id: str, token: str, video_id: str, caption: str) -> str:
    """Publish Reels. Trả về post_id."""
    resp = requests.post(
        f"{GRAPH_API}/{page_id}/video_reels",
        params={"access_token": token},
        json={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("post_id", "")


# ── Public API ─────────────────────────────────────────────────────────────────

def post_reel(page_id: str, video_path: str, caption: str) -> str:
    """
    Đăng video lên Facebook Reels.
    Trả về post_id hoặc raise Exception nếu lỗi.
    """
    token = _page_token(page_id)
    if not token:
        raise ValueError(f"Không tìm thấy token cho page_id={page_id}")

    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video không tồn tại: {video_path}")

    video_bytes = video_file.read_bytes()
    video_id, upload_url = _init_upload_session(page_id, token, len(video_bytes))
    ok = _upload_video_bytes(upload_url, token, video_bytes)
    if not ok:
        raise RuntimeError("Upload video thất bại")

    post_id = _publish_reel(page_id, token, video_id, caption)
    return post_id


def post_campaign(campaign_id: int, caption_template: str = "") -> str:
    """
    Đăng campaign lên Facebook Page.
    caption_template có thể chứa {affiliate_link} và {hashtags}.
    Trả về post_id.

    Nếu setting "test_mode" bật → dry-run: không gọi Graph API, chỉ đánh dấu
    đã đăng với post_id giả + vài số liệu mẫu để kiểm tra dashboard.
    """
    campaigns = store.list_all_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} không tồn tại")

    product = store.get_product(campaign["product_id"])
    if not product:
        raise ValueError("Product không tồn tại")

    # ── Dry-run / chế độ thử nghiệm ──────────────────────────────────────────
    if store.get_setting("test_mode", "") == "1":
        import random
        fake_post_id = f"TEST_{campaign_id}_{int(time.time())}"
        store.update_campaign(
            campaign_id,
            status="posted",
            post_id=fake_post_id,
            posted_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            views=random.randint(500, 15000),
            likes=random.randint(20, 600),
        )
        return fake_post_id

    pages = store.list_pages()
    page = next((p for p in pages if p["id"] == product.get("page_id")), None)
    if not page:
        raise ValueError("Chưa chọn Facebook Page cho sản phẩm này")

    if not campaign.get("video_path"):
        raise ValueError("Video chưa được render")

    # Caption GIÁ TRỊ (không link) — monetize mềm
    from webui.affiliate.services import caption as caption_svc
    caption = campaign.get("caption") or caption_svc.build_value_caption(campaign)

    post_id = post_reel(page["page_id"], campaign["video_path"], caption)
    store.update_campaign(
        campaign_id,
        status="posted",
        post_id=post_id,
        posted_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )

    # Tự động comment đầu tiên chứa link affiliate (ghim)
    comment = campaign.get("comment_text") or caption_svc.build_comment(campaign, product)
    if comment:
        try:
            post_comment(page["page_id"], post_id, comment, pin=True)
        except Exception as e:
            # Không làm hỏng việc đăng nếu comment lỗi
            pass

    return post_id


def post_comment(page_id: str, post_id: str, message: str, pin: bool = False) -> str:
    """Đăng comment lên một post. Trả về comment_id. Tùy chọn ghim."""
    token = _page_token(page_id)
    if not token:
        raise ValueError(f"Không tìm thấy token cho page_id={page_id}")
    resp = requests.post(
        f"{GRAPH_API}/{post_id}/comments",
        params={"access_token": token},
        json={"message": message},
        timeout=30,
    )
    resp.raise_for_status()
    comment_id = resp.json().get("id", "")
    if pin and comment_id:
        try:
            requests.post(
                f"{GRAPH_API}/{comment_id}",
                params={"access_token": token},
                json={"is_pinned": True},
                timeout=15,
            )
        except Exception:
            pass
    return comment_id


# ── Page validation ────────────────────────────────────────────────────────────

def validate_page_token(page_id: str, token: str) -> tuple[bool, str]:
    """
    Kiểm tra token có hợp lệ không.
    Trả về (ok, page_name).
    """
    try:
        resp = requests.get(
            f"{GRAPH_API}/{page_id}",
            params={"access_token": token, "fields": "name,id"},
            timeout=10,
        )
        data = resp.json()
        if "error" in data:
            return False, data["error"].get("message", "Unknown error")
        return True, data.get("name", "")
    except Exception as e:
        return False, str(e)


def get_reel_insights(post_id: str, page_id: str) -> dict:
    """Lấy views/likes từ Graph API."""
    token = _page_token(page_id)
    if not token:
        return {}
    try:
        resp = requests.get(
            f"{GRAPH_API}/{post_id}",
            params={
                "access_token": token,
                "fields": "insights.metric(post_video_views,post_reactions_by_type_total)",
            },
            timeout=10,
        )
        data = resp.json()
        insights = data.get("insights", {}).get("data", [])
        result = {}
        for item in insights:
            if item["name"] == "post_video_views":
                result["views"] = item["values"][0].get("value", 0) if item.get("values") else 0
            elif item["name"] == "post_reactions_by_type_total":
                vals = item["values"][0].get("value", {}) if item.get("values") else {}
                result["likes"] = vals.get("LIKE", 0)
        return result
    except Exception:
        return {}
