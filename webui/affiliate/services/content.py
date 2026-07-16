"""
Content Engine — sinh loạt video "tip-based, giá trị trước" theo NGÁCH.

Khác với shopee.py (phân tích 1 sản phẩm để bán), module này nhận một CHỦ ĐỀ
trong một ngách hợp tool (nội dung dạng mẹo/kiến thức, stock footage tải được)
và sinh nhiều video mang giá trị. Sản phẩm affiliate KHÔNG phải chủ thể video —
nó chỉ được gợi ý mềm ở phần comment.

Triết lý (xem memory content-factory-vision):
  - Giá trị trước, không biến video thành quảng cáo.
  - Link Shopee ở comment/bio, không nhồi vào caption/lời thoại.
  - Một ngách → nhiều góc → nuôi kênh + xây niềm tin.
"""

import json

from webui.affiliate.store import db as store
from webui.affiliate.services import shopee as _shopee  # tái dùng _call_llm, _parse_json


# ── Ngách hợp tool (nội dung tip-based, stock footage tải được) ─────────────────

NICHES: dict[str, dict] = {
    "phat_giao": {
        "label": "🪷 Phật giáo & triết lý sống",
        "audience": "người tìm sự an yên, muốn buông bỏ, sống tỉnh thức",
        "pillars": ["lời Phật dạy", "buông bỏ", "vô thường", "chánh niệm",
                    "nhân quả", "câu chuyện thiền"],
        "stock_terms": ["buddha statue", "meditation zen", "lotus flower",
                        "peaceful temple", "calm nature sunrise"],
        "product_hint": "sách Phật giáo, chuông xoay, nhang trầm, vòng tay gỗ/đá, tượng Phật",
        "warning": "Giữ giọng nhẹ nhàng, chiêm nghiệm, TÔN TRỌNG. Không xuyên tạc giáo lý, "
                   "không cổ xúy mê tín dị đoan, không phán xét tôn giáo khác.",
    },
    "phat_trien_ban_than": {
        "label": "🚀 Cải thiện bản thân",
        "audience": "người trẻ muốn tiến bộ, kỷ luật và thành công hơn",
        "pillars": ["thói quen tốt", "kỷ luật bản thân", "tư duy phát triển",
                    "quản lý thời gian", "vượt sự trì hoãn", "bài học thành công"],
        "stock_terms": ["sunrise running", "person reading book", "focused work",
                        "morning discipline", "journaling desk"],
        "product_hint": "sách self-help, sổ habit tracker, planner, bút, đèn học",
    },
    "tam_ly_hoc": {
        "label": "🧠 Tâm lý học đời sống",
        "audience": "người tò mò về hành vi, cảm xúc và các mối quan hệ",
        "pillars": ["sự thật tâm lý", "thiên kiến nhận thức", "ngôn ngữ cơ thể",
                    "tâm lý mối quan hệ", "tâm lý nơi công sở", "mẹo giao tiếp"],
        "stock_terms": ["two people talking", "human emotion face", "brain concept",
                        "people crowd city", "thoughtful person"],
        "product_hint": "sách tâm lý, sách kỹ năng giao tiếp, sổ tay ghi chép",
        "warning": "Trình bày dạng KIẾN THỨC PHỔ THÔNG. KHÔNG chẩn đoán, không đưa lời khuyên "
                   "lâm sàng, không thay thế chuyên gia tâm lý/y tế.",
    },
    "tiet_kiem": {
        "label": "💰 Tiết kiệm & quản lý chi tiêu",
        "audience": "người trẻ, gia đình muốn quản lý tiền tốt hơn",
        "pillars": ["mẹo tiết kiệm", "sai lầm chi tiêu", "thói quen tài chính", "so sánh lựa chọn"],
        "stock_terms": ["saving money", "budget planning", "vietnamese family home", "counting money"],
        "product_hint": "sổ chi tiêu, máy đếm tiền, sách tài chính, ống heo",
    },
    "nha_cua": {
        "label": "🏠 Mẹo nhà cửa & sắp xếp",
        "audience": "nội trợ, người thuê trọ, gia đình trẻ",
        "pillars": ["mẹo dọn dẹp", "khử mùi", "sắp xếp gọn", "tận dụng không gian"],
        "stock_terms": ["clean kitchen", "home organization", "tidy room", "storage boxes"],
        "product_hint": "hộp đựng, kệ, túi hút chân không, móc treo",
    },
    "suc_khoe": {
        "label": "💪 Sức khỏe & thói quen tốt",
        "audience": "người bận rộn muốn sống khỏe hơn",
        "pillars": ["thói quen buổi sáng", "mẹo giữ dáng", "uống đủ nước", "giãn cơ tại nhà"],
        "stock_terms": ["morning routine", "healthy lifestyle", "drinking water", "home workout"],
        "product_hint": "bình nước, thảm yoga, máy massage, dây kháng lực",
        "warning": "TUYỆT ĐỐI không đưa lời khuyên/claim y tế cụ thể (vi phạm chính sách).",
    },
    "hoc_tap": {
        "label": "📚 Mẹo học tập & năng suất",
        "audience": "học sinh, sinh viên, người đi làm",
        "pillars": ["phương pháp học", "chống trì hoãn", "sắp xếp thời gian", "ghi chú hiệu quả"],
        "stock_terms": ["study desk", "student writing notes", "productivity laptop", "planner"],
        "product_hint": "văn phòng phẩm, đèn bàn, bảng kế hoạch, đồ desk",
    },
    "thu_cung": {
        "label": "🐶 Chăm sóc thú cưng",
        "audience": "người nuôi chó mèo",
        "pillars": ["mẹo chăm nuôi", "sai lầm khi nuôi", "huấn luyện cơ bản", "dinh dưỡng"],
        "stock_terms": ["cute dog", "cat playing", "pet care", "puppy training"],
        "product_hint": "đồ ăn, phụ kiện, đồ chơi, lược chải lông",
    },
    "me_be": {
        "label": "👶 Mẹo mẹ & bé",
        "audience": "mẹ bỉm, gia đình có con nhỏ",
        "pillars": ["kinh nghiệm chăm con", "an toàn cho bé", "ăn dặm", "giấc ngủ của bé"],
        "stock_terms": ["mother and baby", "baby playing", "toddler home", "baby care"],
        "product_hint": "đồ dùng cho bé, đồ an toàn, đồ chơi giáo dục",
    },
    "cay_canh": {
        "label": "🪴 Chăm cây & vườn nhỏ",
        "audience": "người thích trồng cây tại nhà, ban công",
        "pillars": ["cách chăm cây", "cây dễ trồng", "sai lầm tưới nước", "trang trí xanh"],
        "stock_terms": ["indoor plants", "gardening hands", "watering plants", "balcony garden"],
        "product_hint": "chậu, hạt giống, dụng cụ làm vườn, phân bón",
    },
}


def niche_labels() -> dict[str, str]:
    return {k: v["label"] for k, v in NICHES.items()}


# ── Sinh loạt video tip-based ──────────────────────────────────────────────────

def generate_content_series(
    niche_key: str,
    topic: str,
    count: int = 5,
    product_hint: str = "",
) -> list[dict]:
    """
    Sinh `count` video giá trị cho một chủ đề trong ngách.

    Returns list, mỗi phần tử:
        {
          "title":       "tiêu đề video",
          "hook_type":   "tip|list|myth|mistake|howto|compare",
          "hook_text":   "câu mở đầu 3s giữ chân",
          "script":      "kịch bản 30-60s, GIÁ TRỊ, KHÔNG bán hàng",
          "video_terms": ["từ khóa tìm footage tiếng Anh", ...],
          "product_suggestion": "gợi ý loại sản phẩm để gắn ở comment (mềm)"
        }
    """
    niche = NICHES.get(niche_key, {})
    label = niche.get("label", niche_key)
    audience = niche.get("audience", "khán giả phổ thông")
    pillars = ", ".join(niche.get("pillars", []))
    default_hint = product_hint or niche.get("product_hint", "")
    warning = niche.get("warning", "")
    stock_examples = ", ".join(f'"{t}"' for t in niche.get("stock_terms", ["calm nature"]))

    prompt = f"""Bạn là nhà sáng tạo nội dung ngắn (Reels/TikTok) chuyên ngách "{label}" tại Việt Nam.
Đối tượng: {audience}.

Hãy tạo {count} ý tưởng video ngắn (30-60 giây) xoay quanh chủ đề: "{topic}".

## NGUYÊN TẮC BẮT BUỘC

1. GIÁ TRỊ THẬT: người xem phải học/nhận ra được điều gì đó cụ thể.

2. KHÔNG QUẢNG CÁO — TUYỆT ĐỐI:
   - Lời thoại KHÔNG được nhắc: link, bình luận, mua hàng, sản phẩm, "xem link", "inbox".
   - Kết thúc bằng một câu chốt Ý NGHĨA (đọng lại suy ngẫm), KHÔNG kêu gọi hành động thương mại.

3. TRÁNH SÁO MÒN — quan trọng nhất:
   - CẤM dùng các ví dụ đã quá quen thuộc trên mạng (vd: "ly nước cầm lâu mỏi tay",
     "oán giận như uống thuốc độc", "con ếch trong nồi nước sôi", "hai con sói trong tâm").
   - Ưu tiên góc nhìn MỚI, tình huống ĐỜI THƯỜNG VIỆT NAM cụ thể (kẹt xe, deadline, họp gia đình,
     tin nhắn chưa trả lời, ở trọ, chợ, quán cà phê...).
   - Dùng chi tiết cụ thể, không nói chung chung sáo rỗng.

4. ĐA DẠNG: mỗi video một góc + một dạng khác nhau ({pillars}).
   Khác nhau cả nhịp điệu và độ dài, đừng viết {count} bài cùng một khuôn.

5. Văn nói tự nhiên, như đang tâm sự với một người bạn.
{f'6. LƯU Ý ĐẶC THÙ: {warning}' if warning else ''}

## video_terms — RẤT QUAN TRỌNG
Dùng để tải footage từ Pexels/Pixabay (chỉ hiểu TIẾNG ANH).
- BẮT BUỘC viết bằng TIẾNG ANH, 4-6 từ khóa.
- Mô tả CẢNH QUAY CỤ THỂ NHÌN THẤY ĐƯỢC, không phải khái niệm trừu tượng.
- ĐÚNG: {stock_examples}
- SAI: "vô thường", "chấp nhận", "impermanence", "acceptance" (trừu tượng, không quay được).

## product_suggestion
Gợi ý loại sản phẩm để đặt link ở comment (KHÔNG xuất hiện trong lời thoại),
tham khảo nhóm: {default_hint}.

Trả về JSON thuần (không markdown), đúng {count} phần tử:
{{
  "videos": [
    {{
      "title": "...",
      "hook_type": "một trong: {pillars}",
      "hook_text": "câu mở đầu 3 giây giữ chân",
      "script": "kịch bản đầy đủ, KHÔNG nhắc link/sản phẩm",
      "video_terms": ["english scene 1", "english scene 2", "english scene 3", "english scene 4"],
      "product_suggestion": "..."
    }}
  ]
}}"""

    raw = _shopee._call_llm(prompt)
    data = _shopee._parse_json(raw)
    videos = data.get("videos", data) if isinstance(data, dict) else data
    if not isinstance(videos, list):
        raise ValueError("Content engine không trả về danh sách video hợp lệ")

    fallback_terms = niche.get("stock_terms", ["calm nature"])
    for v in videos:
        v["video_terms"] = _sanitize_terms(v.get("video_terms"), fallback_terms)
        v["script"] = _strip_cta(v.get("script", ""))
    return videos


# ── Lưới an toàn ───────────────────────────────────────────────────────────────

_VI_CHARS = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"

def _is_english(term: str) -> bool:
    """Từ khóa hợp lệ để search Pexels: không chứa dấu tiếng Việt."""
    return not any(ch in _VI_CHARS for ch in (term or "").lower())


def _sanitize_terms(terms, fallback: list[str]) -> list[str]:
    """
    Pexels/Pixabay chỉ hiểu tiếng Anh. Nếu LLM trả từ khóa tiếng Việt
    (search sẽ ra 0 kết quả → video không có footage), thay bằng stock_terms của ngách.
    """
    if not isinstance(terms, list):
        return list(fallback)
    clean = [t for t in terms if isinstance(t, str) and t.strip() and _is_english(t)]
    return clean if clean else list(fallback)


# Lời thoại KHÔNG được chứa CTA thương mại (xem content-factory-vision).
_CTA_PATTERNS = [
    "link ở bình luận", "link trong bình luận", "xem link", "link bio",
    "link trong bio", "mua ngay", "inbox", "bình luận nếu cần", "link dưới",
]

def _strip_cta(script: str) -> str:
    """Bỏ câu CTA thương mại nếu LLM lỡ chèn vào lời thoại."""
    if not script:
        return script
    import re as _re
    sentences = _re.split(r"(?<=[.!?])\s+", script.strip())
    kept = [s for s in sentences if not any(p in s.lower() for p in _CTA_PATTERNS)]
    return " ".join(kept).strip() or script


# ── Pipeline: sinh + lưu DB ────────────────────────────────────────────────────

def run_topic_analysis(product_id: int):
    """
    Chạy content engine cho một 'product' loại topic → lưu campaigns.
    (Tái dùng bảng products với source_type='topic', name = chủ đề, niche = ngách.)
    """
    product = store.get_product(product_id)
    if not product:
        return

    topic = product.get("name") or ""
    niche_key = product.get("niche") or ""
    count = product.get("script_count", 5)
    test_mode = store.get_setting("test_mode", "") == "1"

    if test_mode:
        videos = _sample_series(niche_key, topic, count)
    else:
        videos = generate_content_series(niche_key, topic, count)

    # Lưu "insights" gọn để hiển thị (ngách + chủ đề)
    meta = {
        "niche": NICHES.get(niche_key, {}).get("label", niche_key),
        "topic": topic,
        "type": "content_series",
    }
    store.update_product(
        product_id,
        insights=json.dumps(meta, ensure_ascii=False),
        status="scripted",
    )
    for v in videos:
        cid = store.add_campaign(
            product_id=product_id,
            hook_type=v.get("hook_type", "tip"),
            hook_text=v.get("hook_text") or v.get("title", ""),
            script=v.get("script", ""),
        )
        store.update_campaign(
            cid,
            video_terms=json.dumps(v.get("video_terms", []), ensure_ascii=False),
        )


def _sample_series(niche_key: str, topic: str, count: int) -> list[dict]:
    """Dữ liệu mẫu cho test mode."""
    niche = NICHES.get(niche_key, {})
    hint = niche.get("product_hint", "sản phẩm liên quan")
    terms = niche.get("stock_terms", ["lifestyle"])
    types = ["tip", "list", "mistake", "howto", "myth", "compare"]
    out = []
    for i in range(count):
        t = types[i % len(types)]
        out.append({
            "title": f"[{t}] {topic} #{i+1}",
            "hook_type": t,
            "hook_text": f"Mẹo {i+1} về '{topic}' mà ít người biết!",
            "script": (f"[{t}] Chia sẻ một góc nhìn giá trị về '{topic}'. "
                       f"Giải thích ngắn gọn vì sao hữu ích. "
                       f"Chốt bằng một câu đọng lại suy ngẫm."),
            "video_terms": terms,
            "product_suggestion": hint,
        })
    return out
