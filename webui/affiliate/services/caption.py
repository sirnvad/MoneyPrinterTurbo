"""
Tạo caption đăng bài cho từng kịch bản.

Caption = template điền sẵn {script_hook}, {affiliate_link}, {hashtags}.
Link affiliate được gắn thêm tracking ID (nếu có cấu hình) qua query param.
"""

from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from webui.affiliate.store import db as store


_DEFAULT_TEMPLATE = "{script_hook}\n\n🛒 Mua ngay: {affiliate_link}\n\n{hashtags}"


def append_tracking(url: str, tracking_id: str) -> str:
    """Gắn tracking ID vào link Shopee (param utm_content / af_id)."""
    if not url or not tracking_id:
        return url
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    query.setdefault("utm_source", "affiliatestudio")
    query["utm_content"] = tracking_id
    new_query = urlencode(query)
    return urlunparse(parts._replace(query=new_query))


def build_caption(campaign: dict, product: dict) -> str:
    """
    Dựng caption từ template trong settings.
    campaign: dict có hook_text. product: dict có shopee_url.
    """
    s = store.get_all_settings()
    template = s.get("caption_template", _DEFAULT_TEMPLATE)
    tracking_id = s.get("shopee_tracking_id", "")
    hashtags = s.get("default_hashtags", "#shopee #review #muasắm #affiliate")

    link = append_tracking(product.get("shopee_url", ""), tracking_id)

    try:
        return template.format(
            script_hook=campaign.get("hook_text", ""),
            affiliate_link=link,
            hashtags=hashtags,
        )
    except (KeyError, IndexError):
        # Template có biến lạ → fallback ghép thủ công
        return (
            f"{campaign.get('hook_text','')}\n\n"
            f"🛒 Mua ngay: {link}\n\n{hashtags}"
        )


def ensure_caption(campaign_id: int) -> str:
    """
    Lấy caption đã lưu; nếu chưa có thì dựng mới, lưu lại và trả về.
    """
    campaigns = store.list_all_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        return ""
    if campaign.get("caption"):
        return campaign["caption"]
    product = store.get_product(campaign["product_id"])
    caption = build_caption(campaign, product or {})
    store.update_campaign(campaign_id, caption=caption)
    return caption
