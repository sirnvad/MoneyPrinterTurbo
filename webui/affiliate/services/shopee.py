"""
Shopee product analysis service — quy trình 2 giai đoạn:

  1. scrape_product(url)        → thông tin thô (name, price, image, description)
  2. analyze_product_deep(...)  → PHÂN TÍCH sâu sản phẩm bằng AI
                                  (chân dung KH, điểm đau, mong muốn, USP, trigger...)
  3. generate_scripts(...)      → VIẾT kịch bản dựa trên kết quả phân tích,
                                  mỗi kịch bản kèm từ khóa tìm video footage.

Shopee chặn request headless khá gắt. Ta thử scrape nhẹ bằng UA trình duyệt thật;
nếu thất bại trả về stub để user nhập tay trước khi phân tích.
"""

import json
import re

import requests

from webui.affiliate.store import db as store


# ── Scraper ────────────────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

_HOOK_TYPES = [
    ("curiosity", "Tò mò / Câu hỏi khiến xem tiếp"),
    ("shock",     "Shock / Bất ngờ / Số liệu ấn tượng"),
    ("benefit",   "Lợi ích trực tiếp / Giải pháp rõ ràng"),
    ("story",     "Kể chuyện / Trải nghiệm cá nhân"),
    ("compare",   "So sánh / Trước-sau"),
]


def scrape_product(url: str) -> dict:
    """Lấy thông tin sản phẩm từ Shopee. Trả stub nếu thất bại."""
    stub = {"name": "", "price": "", "image_url": "", "description": "", "url": url}
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return stub
        html = resp.text

        def og(prop):
            m = re.search(rf'<meta[^>]+property="og:{prop}"[^>]+content="([^"]+)"', html)
            return m.group(1) if m else ""

        name = og("title") or ""
        image_url = og("image") or ""
        description = og("description") or ""

        price_m = re.search(r'"price":\s*(\d+)', html)
        price = ""
        if price_m:
            raw = int(price_m.group(1))
            if raw > 1_000_000:
                raw = raw // 100000
            price = f"{raw:,} ₫"

        stub.update(name=name, price=price, image_url=image_url, description=description)
    except Exception:
        pass
    return stub


# ── LLM helpers ────────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> str:
    """Gọi LLM qua cấu hình của MoneyPrinterTurbo (app.services.llm)."""
    from app.services import llm as _llm  # import trễ tránh vòng lặp

    return _llm._generate_response(prompt)


def _parse_json(raw: str):
    """Bóc JSON từ phản hồi LLM (bỏ markdown fence, lấy object/array đầu tiên)."""
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        # Lấy đoạn { ... } hoặc [ ... ] dài nhất
        for pattern in (r"\{.*\}", r"\[.*\]"):
            m = re.search(pattern, raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    continue
        raise


# ── Giai đoạn 1: Phân tích sản phẩm ─────────────────────────────────────────────

def analyze_product_deep(product: dict, language: str = "vi") -> dict:
    """
    Phân tích sâu sản phẩm bằng AI.

    Returns dict:
        {
          "category":           "ngành hàng",
          "target_audience":    "chân dung khách hàng mục tiêu",
          "demographics":       "tuổi / giới tính / thu nhập / khu vực",
          "pain_points":        ["điểm đau 1", ...],
          "desires":            ["mong muốn 1", ...],
          "usps":               ["điểm bán hàng độc nhất 1", ...],
          "emotional_triggers": ["trigger cảm xúc 1", ...],
          "objections":         ["lý do do dự khi mua 1", ...],
          "use_cases":          ["tình huống dùng 1", ...],
          "tone":               "giọng điệu nội dung phù hợp"
        }
    """
    name = product.get("name") or product.get("url", "")
    price = product.get("price", "")
    description = product.get("description", "")

    prompt = f"""Bạn là chuyên gia nghiên cứu thị trường và hành vi khách hàng cho affiliate Shopee tại Việt Nam.
Hãy PHÂN TÍCH SÂU sản phẩm dưới đây (chỉ phân tích, CHƯA viết kịch bản).

Sản phẩm: {name}
Giá: {price}
Mô tả: {description}

Suy luận kỹ về khách hàng tiềm năng tại Việt Nam: họ là ai, vì sao họ mua, điều gì khiến họ do dự,
và những "insight" tâm lý sâu sắc nhất có thể khai thác để làm video bán hàng viral.

Trả về JSON thuần (không markdown, tiếng Việt):
{{
  "category": "ngành hàng cụ thể",
  "target_audience": "mô tả chân dung khách hàng mục tiêu (1-2 câu)",
  "demographics": "độ tuổi, giới tính, thu nhập, khu vực điển hình",
  "pain_points": ["điểm đau/khó chịu thực tế của khách (3-5 ý)"],
  "desires": ["mong muốn/khát khao ẩn sau (3-5 ý)"],
  "usps": ["điểm bán hàng độc nhất của sản phẩm (3-5 ý)"],
  "emotional_triggers": ["đòn bẩy cảm xúc để thuyết phục (3-4 ý)"],
  "objections": ["lý do khiến khách do dự không mua (3-4 ý)"],
  "use_cases": ["tình huống/dịp sử dụng cụ thể (3-4 ý)"],
  "tone": "giọng điệu nội dung phù hợp nhất với nhóm khách này"
}}"""

    raw = _call_llm(prompt)
    return _parse_json(raw)


# ── Giai đoạn 2: Viết kịch bản dựa trên phân tích ───────────────────────────────

def generate_scripts(product: dict, analysis: dict, script_count: int = 3) -> list[dict]:
    """
    Viết kịch bản video ngắn dựa trên kết quả phân tích sản phẩm.

    Returns list (script_count phần tử), mỗi phần tử:
        {
          "hook_type":   "curiosity"|"shock"|"benefit"|"story"|"compare",
          "angle":       "góc tiếp cận / insight được khai thác",
          "hook_text":   "câu mở đầu 3 giây đầu",
          "script":      "kịch bản đầy đủ 60-90s (Hook→Vấn đề→Giải pháp→CTA)",
          "video_terms": ["từ khóa tìm video footage tiếng Anh", ...]
        }
    """
    name = product.get("name") or product.get("url", "")
    price = product.get("price", "")

    hook_menu = "\n".join(
        f'  - "{ht}": {desc}' for ht, desc in _HOOK_TYPES[:max(script_count, 3)]
    )
    analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)

    prompt = f"""Bạn là copywriter video bán hàng cho TikTok/Reels affiliate Shopee tại Việt Nam.
Dưới đây là KẾT QUẢ PHÂN TÍCH sản phẩm "{name}" (giá {price}):

{analysis_json}

Dựa CHẶT CHẼ vào phân tích trên, hãy viết {script_count} kịch bản video ngắn (60-90 giây), MỖI kịch bản
khai thác một điểm đau / mong muốn / insight KHÁC NHAU và dùng một loại hook khác nhau:
{hook_menu}

Quy tắc:
- Mỗi kịch bản theo cấu trúc: HOOK (3s đầu giữ chân) → VẤN ĐỀ (đồng cảm điểm đau) → GIẢI PHÁP (sản phẩm + USP) → CTA ("Link mua trong bio nhé!").
- Văn nói tự nhiên, như đang tâm sự với người xem, KHÔNG quảng cáo lộ liễu.
- Xử lý ít nhất 1 "objection" trong mỗi kịch bản.
- "video_terms": 4-6 từ khóa TIẾNG ANH mô tả cảnh quay phù hợp để tải footage (vd: "woman applying skincare", "morning routine").

Trả về JSON thuần (không markdown):
{{
  "scripts": [
    {{
      "hook_type": "curiosity",
      "angle": "insight/điểm đau được khai thác",
      "hook_text": "...",
      "script": "...",
      "video_terms": ["...", "..."]
    }}
  ]
}}
Chú ý: trả về ĐÚNG {script_count} kịch bản."""

    raw = _call_llm(prompt)
    data = _parse_json(raw)
    scripts = data.get("scripts", data) if isinstance(data, dict) else data
    if not isinstance(scripts, list):
        raise ValueError("LLM không trả về danh sách kịch bản hợp lệ")
    return scripts


# ── Full pipeline: phân tích → kịch bản → lưu DB ────────────────────────────────

def run_product_analysis(product_id: int):
    """
    scrape (nếu cần) → phân tích sâu → viết kịch bản → lưu insights + campaigns.
    Chạy đồng bộ (gọi trong st.spinner).
    """
    product = store.get_product(product_id)
    if not product:
        return

    script_count = product.get("script_count", 3)
    test_mode = store.get_setting("test_mode", "") == "1"

    # ── Dry-run ──
    if test_mode:
        if not product.get("name"):
            store.update_product(product_id, name="[TEST] Sản phẩm mẫu", price="199.000 ₫")
            product["name"] = "[TEST] Sản phẩm mẫu"
        analysis, scripts = _sample_analysis(product["name"], script_count)
        _save_results(product_id, analysis, scripts)
        return

    # ── Bước 1: scrape ──
    if not product.get("name"):
        scraped = scrape_product(product["shopee_url"])
        store.update_product(
            product_id,
            name=scraped["name"], price=scraped["price"],
            image_url=scraped["image_url"], status="analyzing",
        )
        product.update(scraped)

    # ── Bước 2: phân tích sâu ──
    store.update_product(product_id, status="analyzing")
    analysis = analyze_product_deep(product)

    # ── Bước 3: viết kịch bản ──
    scripts = generate_scripts(product, analysis, script_count=script_count)

    _save_results(product_id, analysis, scripts)


def _save_results(product_id: int, analysis: dict, scripts: list[dict]):
    """Lưu phân tích vào products.insights và mỗi kịch bản thành 1 campaign."""
    store.update_product(
        product_id,
        insights=json.dumps(analysis, ensure_ascii=False),
        status="scripted",
    )
    for s in scripts:
        cid = store.add_campaign(
            product_id=product_id,
            hook_type=s.get("hook_type", ""),
            hook_text=s.get("hook_text", ""),
            script=s.get("script", ""),
        )
        # Lưu thêm angle + video_terms
        store.update_campaign(
            cid,
            video_terms=json.dumps(s.get("video_terms", []), ensure_ascii=False),
        )


# ── Dữ liệu mẫu cho test mode ───────────────────────────────────────────────────

def _sample_analysis(name: str, script_count: int):
    analysis = {
        "category": "Ngành hàng mẫu (test)",
        "target_audience": f"Khách hàng quan tâm tới {name}",
        "demographics": "20-35 tuổi, nữ, thành thị, thu nhập trung bình khá",
        "pain_points": ["Tốn thời gian", "Sợ mua nhầm hàng kém", "Giá cao ở nơi khác"],
        "desires": ["Tiện lợi", "Hiệu quả nhanh", "Đáng đồng tiền"],
        "usps": ["Chất lượng ổn định", "Giá tốt trên Shopee", "Nhiều người dùng tin tưởng"],
        "emotional_triggers": ["FOMO", "An tâm", "Tự thưởng bản thân"],
        "objections": ["Liệu có thật sự hiệu quả?", "Ship có lâu không?"],
        "use_cases": ["Dùng hằng ngày", "Làm quà tặng"],
        "tone": "Thân thiện, gần gũi",
    }
    samples = {
        "curiosity": (f"Vì sao {name} lại được săn lùng đến vậy?",
                      "Sợ mua nhầm hàng kém"),
        "shock":     (f"Tôi đã thử {name} và bất ngờ với kết quả!",
                      "Liệu có thật sự hiệu quả?"),
        "benefit":   (f"3 lý do {name} đáng mua nhất tầm giá này.",
                      "Giá cao ở nơi khác"),
    }
    order = ["curiosity", "shock", "benefit"]
    scripts = []
    for ht in order[:script_count]:
        hook_text, angle = samples[ht]
        scripts.append({
            "hook_type": ht,
            "angle": angle,
            "hook_text": hook_text,
            "script": (f"[{ht}] {hook_text} "
                       f"Đồng cảm với điểm đau '{angle}'. "
                       f"Giới thiệu {name} như giải pháp. "
                       f"Kết: 'Link mua trong bio nhé!'"),
            "video_terms": ["product showcase", "happy customer", "unboxing"],
        })
    return analysis, scripts
