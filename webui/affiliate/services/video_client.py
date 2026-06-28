"""
HTTP client gọi MoneyPrinterTurbo API để tạo video.

API base URL lấy từ settings DB (key: api_base_url), mặc định localhost:8080.
"""

import time
from typing import Any

import requests

from webui.affiliate.store import db as store


def _base_url() -> str:
    return store.get_setting("api_base_url", "http://localhost:8080")


def _video_params_from_settings() -> dict:
    s = store.get_all_settings()
    return {
        "video_aspect": s.get("video_aspect", "9:16"),
        "video_concat_mode": s.get("video_concat_mode", "random"),
        "video_clip_duration": int(s.get("video_clip_duration", "5")),
        "video_source": s.get("video_source", "pexels"),
        "voice_name": s.get("voice_name", ""),
        "voice_volume": float(s.get("voice_volume", "1.0")),
        "voice_rate": float(s.get("voice_rate", "1.0")),
        "bgm_type": s.get("bgm_type", "random"),
        "bgm_volume": float(s.get("bgm_volume", "0.2")),
        "subtitle_enabled": s.get("subtitle_enabled", "true") == "true",
        "font_name": s.get("font_name", "STHeitiMedium.ttc"),
        "font_size": int(s.get("font_size", "60")),
        "text_fore_color": s.get("text_fore_color", "#FFFFFF"),
        "stroke_color": s.get("stroke_color", "#000000"),
        "stroke_width": float(s.get("stroke_width", "1.5")),
        "n_threads": int(s.get("n_threads", "2")),
        "paragraph_number": int(s.get("paragraph_number", "1")),
        "video_count": 1,
    }


def start_video_task(campaign_id: int) -> str | None:
    """
    Khởi động task tạo video cho campaign.
    Trả về task_id hoặc None nếu lỗi.
    Cập nhật campaign status → 'rendering'.
    """
    from webui.affiliate.store import db as store

    campaign_row = None
    for c in store.list_all_campaigns():
        if c["id"] == campaign_id:
            campaign_row = c
            break

    if not campaign_row:
        return None

    product = store.get_product(campaign_row["product_id"])
    if not product:
        return None

    # ── Dry-run: bỏ qua backend, đánh dấu sẵn sàng đăng ──
    if store.get_setting("test_mode", "") == "1":
        fake_task = f"TEST_TASK_{campaign_id}"
        store.update_campaign(
            campaign_id,
            task_id=fake_task,
            status="scheduled",   # bỏ qua 'rendering', sẵn sàng để (giả) đăng
            video_path="",
        )
        return fake_task

    params = _video_params_from_settings()
    params.update(
        video_subject=product.get("name") or product["shopee_url"],
        video_script=campaign_row["script"],
        video_terms=campaign_row.get("video_terms") or "",
    )

    try:
        resp = requests.post(
            f"{_base_url()}/api/v1/video/create",
            json=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("data", {}).get("task_id", "")
        if task_id:
            store.update_campaign(campaign_id, task_id=task_id, status="rendering")
        return task_id
    except Exception as e:
        store.update_campaign(campaign_id, status="error")
        return None


def poll_task(task_id: str) -> dict:
    """
    Poll trạng thái task.
    Returns: {state: int, progress: int, videos: [...], combined_videos: [...]}
    state: 0=pending, 1=processing, 2=complete, -1=failed
    """
    try:
        resp = requests.get(
            f"{_base_url()}/api/v1/tasks/{task_id}",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})
    except Exception:
        return {"state": -1, "progress": 0}


def wait_for_task(task_id: str, timeout: int = 600, poll_interval: int = 5) -> dict:
    """Block cho đến khi task xong hoặc timeout. Dùng trong background thread."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = poll_task(task_id)
        state = data.get("state", 0)
        if state == 2:  # complete
            return data
        if state == -1:  # failed
            return data
        time.sleep(poll_interval)
    return {"state": -1, "progress": 0, "error": "timeout"}


def sync_campaign_video(campaign_id: int):
    """
    Poll task của campaign và cập nhật video_path khi xong.
    Dùng trong background thread.
    """
    campaigns = store.list_all_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign or not campaign.get("task_id"):
        return

    result = wait_for_task(campaign["task_id"])
    if result.get("state") == 2:
        videos = result.get("combined_videos") or result.get("videos") or []
        video_path = videos[0] if videos else ""
        store.update_campaign(campaign_id, video_path=video_path, status="scheduled")
    else:
        store.update_campaign(campaign_id, status="error")
