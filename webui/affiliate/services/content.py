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
import time

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
    on_progress=None,
) -> list[dict]:
    """
    Sinh `count` video giá trị cho một chủ đề trong ngách — theo 2 GIAI ĐOẠN:
      A. Brainstorm `count` góc nhìn KHÁC NHAU (1 lần gọi, đảm bảo đa dạng).
      B. Viết TỪNG kịch bản riêng lẻ (model dồn sức → sâu, ít sáo mòn).

    on_progress(i, count): callback tùy chọn để cập nhật tiến độ.

    Returns list, mỗi phần tử:
        {title, hook_type, hook_text, script, video_terms, product_suggestion}
    """
    niche = NICHES.get(niche_key, {})
    default_hint = product_hint or niche.get("product_hint", "")
    fallback_terms = niche.get("stock_terms", ["calm nature"])

    # ── Giai đoạn A: brainstorm góc nhìn ──
    angles = _brainstorm_angles(niche_key, topic, count)

    # ── Giai đoạn B: viết từng kịch bản ──
    videos: list[dict] = []
    for i, angle in enumerate(angles, 1):
        try:
            v = _write_one_script(niche_key, topic, angle, default_hint)
        except Exception:
            # Bỏ qua kịch bản lỗi, tiếp tục các cái khác
            continue
        v["video_terms"] = _sanitize_terms(v.get("video_terms"), fallback_terms)
        v["script"] = _strip_cta(v.get("script", ""))
        if not v.get("title"):
            v["title"] = angle.get("title", f"{topic} #{i}")
        videos.append(v)
        if on_progress:
            on_progress(i, len(angles))

    if not videos:
        raise ValueError("Content engine không sinh được kịch bản nào")
    return videos


def _call_json(prompt: str, retries: int = 2):
    """
    Gọi LLM + parse JSON, retry khi rỗng/lỗi parse.
    Xử lý cold-start của LM Studio (lần gọi đầu khi JIT-load model có thể trả rỗng).
    """
    last_err = None
    for _ in range(retries + 1):
        try:
            raw = _shopee._call_llm(prompt)
            if raw and raw.strip():
                return _shopee._parse_json(raw)
        except Exception as e:
            last_err = e
        time.sleep(2)  # chờ model ấm rồi thử lại
    raise last_err or ValueError("LLM trả về rỗng")


def _brainstorm_angles(niche_key: str, topic: str, count: int) -> list[dict]:
    """Giai đoạn A: nghĩ ra `count` góc nhìn khác nhau (title + dạng + insight)."""
    niche = NICHES.get(niche_key, {})
    label = niche.get("label", niche_key)
    audience = niche.get("audience", "khán giả phổ thông")
    pillars = ", ".join(niche.get("pillars", []))
    warning = niche.get("warning", "")

    prompt = f"""Bạn là nhà sáng tạo nội dung ngắn chuyên ngách "{label}" tại Việt Nam (đối tượng: {audience}).
Hãy nghĩ ra {count} GÓC NHÌN KHÁC NHAU cho các video ngắn về chủ đề: "{topic}".

Yêu cầu:
- Mỗi góc khai thác một khía cạnh/insight RIÊNG BIỆT, không trùng lặp.
- Gắn với tình huống ĐỜI THƯỜNG VIỆT NAM cụ thể (công việc, gia đình, mạng xã hội, đi lại, tiền bạc...).
- TRÁNH mọi ví dụ sáo mòn phổ biến (ly nước, thuốc độc, ếch trong nồi, hai con sói...).
- Đa dạng dạng nội dung: {pillars}.
{f'- LƯU Ý: {warning}' if warning else ''}

Trả về JSON thuần (không markdown), đúng {count} phần tử:
{{
  "angles": [
    {{"title": "tiêu đề ngắn", "hook_type": "một dạng trong: {pillars}", "angle": "1 câu mô tả insight/góc khai thác cụ thể"}}
  ]
}}"""
    data = _call_json(prompt)
    angles = data.get("angles", data) if isinstance(data, dict) else data
    if not isinstance(angles, list) or not angles:
        raise ValueError("Không brainstorm được góc nhìn")
    return angles[:count]


def _write_one_script(niche_key: str, topic: str, angle: dict, product_hint: str) -> dict:
    """Giai đoạn B: viết 1 kịch bản đầy đủ cho một góc nhìn."""
    niche = NICHES.get(niche_key, {})
    label = niche.get("label", niche_key)
    warning = niche.get("warning", "")
    stock_examples = ", ".join(f'"{t}"' for t in niche.get("stock_terms", ["calm nature"]))

    title = angle.get("title", topic)
    hook_type = angle.get("hook_type", "tip")
    angle_desc = angle.get("angle", "")

    prompt = f"""Bạn là copywriter video ngắn (Reels/TikTok) ngách "{label}" tại Việt Nam.
Viết MỘT kịch bản video 30-60 giây thật hay cho góc nhìn sau:

Chủ đề: "{topic}"
Tiêu đề: "{title}"
Góc khai thác: {angle_desc}
Dạng: {hook_type}

## YÊU CẦU CHẤT LƯỢNG
1. HOOK 3 giây đầu phải giữ chân ngay (câu hỏi/tình huống bất ngờ, KHÔNG mở bài sáo rỗng).
2. Thân bài: đi vào một tình huống ĐỜI THƯỜNG VIỆT NAM cụ thể, chi tiết, có hình ảnh.
3. Mang GIÁ TRỊ thật — người xem nhận ra/học được điều gì đó.
4. Kết bằng MỘT câu đọng lại suy ngẫm. TUYỆT ĐỐI không nhắc link/bình luận/mua hàng/sản phẩm.
5. CẤM ví dụ sáo mòn (ly nước, thuốc độc, ếch trong nồi, hai con sói, viên đá trong ba lô...).
6. Văn nói tự nhiên như tâm sự với một người bạn. Độ dài ~90-130 từ.
{f'7. LƯU Ý ĐẶC THÙ: {warning}' if warning else ''}

## video_terms
4-6 từ khóa TIẾNG ANH mô tả CẢNH QUAY CỤ THỂ để tải footage từ Pexels (chỉ hiểu tiếng Anh).
- ĐÚNG: {stock_examples}
- SAI: từ trừu tượng như "impermanence", "acceptance", hay tiếng Việt.

Trả về JSON thuần (không markdown):
{{
  "title": "{title}",
  "hook_type": "{hook_type}",
  "hook_text": "câu mở đầu 3 giây",
  "script": "kịch bản đầy đủ, KHÔNG nhắc link/sản phẩm",
  "video_terms": ["english scene 1", "english scene 2", "english scene 3", "english scene 4"],
  "product_suggestion": "loại sản phẩm gợi ý (tham khảo: {product_hint})"
}}"""
    data = _call_json(prompt)
    if not isinstance(data, dict):
        raise ValueError("Kịch bản trả về không hợp lệ")
    return data


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
