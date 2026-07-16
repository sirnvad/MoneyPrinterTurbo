"""
Caption + Comment cho từng video — theo mô hình MONETIZE MỀM.

Triết lý (xem memory content-factory-vision):
  - Caption = nội dung GIÁ TRỊ, KHÔNG chứa link (tránh nền tảng bóp reach).
  - Link affiliate nằm ở COMMENT đầu tiên (ghim), người xem chủ động bấm.
  - CTA nhẹ trong caption: "Link ở bình luận 👇".

Hai hàm chính:
  - build_value_caption(campaign)     → caption giá trị + hashtag + CTA mềm
  - build_comment(campaign, product)  → comment chứa link affiliate (gắn tracking)
"""

from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from webui.affiliate.store import db as store


_DEFAULT_CAPTION_TEMPLATE = "{script_hook}\n\n{cta}\n\n{hashtags}"
_DEFAULT_COMMENT_TEMPLATE = "{cta_comment}\n🔗 {affiliate_link}"


def append_tracking(url: str, tracking_id: str) -> str:
    """Gắn tracking ID vào link Shopee qua query param (không lộ ở caption)."""
    if not url or not tracking_id:
        return url
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    query.setdefault("utm_source", "affiliatestudio")
    query["utm_content"] = tracking_id
    return urlunparse(parts._replace(query=urlencode(query)))


def _affiliate_link(product: dict) -> str:
    """Link sản phẩm: ưu tiên link của product, fallback link mặc định trong settings."""
    url = (product or {}).get("shopee_url", "") or store.get_setting("default_affiliate_link", "")
    return append_tracking(url, store.get_setting("shopee_tracking_id", ""))


# ── Caption giá trị (KHÔNG link) ────────────────────────────────────────────────

def build_value_caption(campaign: dict) -> str:
    s = store.get_all_settings()
    template = s.get("caption_template", _DEFAULT_CAPTION_TEMPLATE)
    # Template cũ (bán hàng) chứa {affiliate_link} — không dùng cho caption giá trị.
    if "{affiliate_link}" in template:
        template = _DEFAULT_CAPTION_TEMPLATE
    hashtags = s.get("default_hashtags", "#meohay #tips #review")
    cta = s.get("caption_cta", "💬 Link sản phẩm mình để ở bình luận ghim 👇")
    hook = campaign.get("hook_text", "")
    try:
        return template.format(script_hook=hook, cta=cta, hashtags=hashtags)
    except (KeyError, IndexError):
        return f"{hook}\n\n{cta}\n\n{hashtags}"


# ── Comment chứa link ───────────────────────────────────────────────────────────

def build_comment(campaign: dict, product: dict) -> str:
    s = store.get_all_settings()
    template = s.get("comment_template", _DEFAULT_COMMENT_TEMPLATE)
    cta_comment = s.get("comment_cta", "🛒 Sản phẩm trong video nhé cả nhà:")
    link = _affiliate_link(product)
    if not link:
        return ""
    try:
        return template.format(cta_comment=cta_comment, affiliate_link=link)
    except (KeyError, IndexError):
        return f"{cta_comment}\n🔗 {link}"


# ── Backward-compat: caption cũ có link (mode bán hàng trực tiếp) ────────────────

def build_caption(campaign: dict, product: dict) -> str:
    """Giữ cho code cũ: caption + link (dùng khi muốn bán trực tiếp)."""
    hook = campaign.get("hook_text", "")
    link = _affiliate_link(product)
    hashtags = store.get_setting("default_hashtags", "#shopee #review")
    return f"{hook}\n\n🛒 Mua ngay: {link}\n\n{hashtags}" if link else f"{hook}\n\n{hashtags}"


# ── Ensure (lấy/dựng + lưu) ─────────────────────────────────────────────────────

def _get_campaign(campaign_id: int) -> dict | None:
    return next((c for c in store.list_all_campaigns() if c["id"] == campaign_id), None)


def ensure_caption(campaign_id: int) -> str:
    campaign = _get_campaign(campaign_id)
    if not campaign:
        return ""
    if campaign.get("caption"):
        return campaign["caption"]
    caption = build_value_caption(campaign)
    store.update_campaign(campaign_id, caption=caption)
    return caption


def ensure_comment(campaign_id: int) -> str:
    campaign = _get_campaign(campaign_id)
    if not campaign:
        return ""
    if campaign.get("comment_text"):
        return campaign["comment_text"]
    product = store.get_product(campaign["product_id"])
    comment = build_comment(campaign, product or {})
    store.update_campaign(campaign_id, comment_text=comment)
    return comment
