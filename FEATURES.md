# FEATURES — Tính năng đã làm (fork sirnvad)

File này liệt kê **tất cả tính năng đã hoàn thành** trong fork này.
- Phần 1: **AffiliateStudio** (`webui/affiliate/`) — toàn bộ tính năng.
- Phần 2: **MoneyPrinterTurbo** — chỉ những phần thêm/sửa so với repo gốc `harry0703/MoneyPrinterTurbo`.

Branch: `feature/shopee-affiliate-studio` · Đã merge upstream tới **v1.3.10**.

---

## Phần 1 — AffiliateStudio

Công cụ tạo video ngắn faceless (Facebook Reels / TikTok) theo hướng **Content Factory**:
nội dung giá trị để nuôi kênh, kiếm tiền affiliate Shopee **mềm** (link ở comment/bio, video không phải quảng cáo).

Chạy: `streamlit run webui/affiliate/main.py --server.port 8502` (cần backend API `python main.py` ở cổng 8080 để render thật).

### 1.1 Kiến trúc

| Thành phần | File | Vai trò |
|---|---|---|
| Entry point | `main.py` | Header + 3 tab: Dashboard / Pipeline / Cài đặt |
| Design system | `theme.py` | Màu, spacing, typography, CSS, helper `chip()`, `field_error()`, `field_help()` |
| Lưu trữ | `store/db.py` | SQLite `storage/affiliate.db`: products, campaigns, fb_pages, settings |
| Engine nội dung | `services/content.py` | 10 ngách, sinh kịch bản 2 giai đoạn, kiểm soát độ dài |
| Phân tích Shopee | `services/shopee.py` | Scrape + phân tích sản phẩm AI 2 giai đoạn |
| Render video | `services/video_client.py` | Gọi API `POST /api/v1/videos` của MoneyPrinterTurbo |
| Facebook | `services/facebook.py` | Đăng Reels qua Graph API, ghim comment chứa link |
| Caption | `services/caption.py` | Dựng caption + gắn tracking ID affiliate |
| Giao diện | `views/dashboard.py`, `views/pipeline.py`, `views/settings.py` | 3 màn hình |

### 1.2 Pipeline — 2 chế độ tạo nội dung

**a) Chế độ Chủ đề (Topic mode, khuyến nghị)** — nội dung giá trị theo ngách:
- 10 ngách: 🪷 Phật giáo & triết lý sống · 🚀 Cải thiện bản thân · 🧠 Tâm lý học đời sống ·
  💰 Tiết kiệm & chi tiêu · 🏠 Mẹo nhà cửa · 💪 Sức khỏe & thói quen · 📚 Học tập & năng suất ·
  🐶 Thú cưng · 👶 Mẹ & bé · 🪴 Cây cảnh.
- **Sinh 2 giai đoạn**: (1) brainstorm các góc tiếp cận khác nhau → (2) viết riêng từng kịch bản.
- **Soft monetization**: `_strip_cta` loại câu bán hàng khỏi lời đọc; caption không chứa link;
  link affiliate nằm ở comment đầu và được ghim tự động.
- `_sanitize_terms`: từ khoá tìm footage luôn là tiếng Anh (hợp Pexels).
- `_call_json`: retry khi LLM trả rỗng/JSON hỏng; prefix `/no_think` cho model reasoning.

**b) Chế độ Sản phẩm Shopee**:
- Dán 1 link hoặc nhập hàng loạt (nhiều dòng / CSV / TXT).
- Phân tích AI 2 giai đoạn: chân dung khách hàng, điểm đau, USP, trigger cảm xúc… → viết 5–10 kịch bản,
  mỗi kịch bản một loại hook (curiosity, shock, benefit, story, compare, problem, testimonial, tips, trend, fomo).

### 1.3 Kiểm soát độ dài lời đọc (video 30s–1 phút)
- Tốc độ đọc giả định 3.4 từ/giây ở rate 1.0 (theo đo giọng Edge NamMinh).
- Mục tiêu **45–55 giây** (~153–187 từ), giới hạn cứng **30–60 giây**.
- Prompt chia ngân sách từ theo 5 phần: hook · tình huống · insight · áp dụng · kết.
- `_fit_length`: nếu lệch, tự yêu cầu LLM kéo dài/rút gọn (tối đa 2 lần), giữ bản gần nhất.
- UI hiển thị chip "≈ 51s · 172 từ" (đỏ khi ngoài khoảng) + đếm từ dưới ô sửa kịch bản.

### 1.4 Quản lý video
- Danh sách dạng dòng: thumbnail, chip hook, chip trạng thái, chip độ dài.
- Trạng thái: `Nháp → Render → Lên lịch → Đã đăng` (hoặc `Lỗi`).
- Thao tác hàng loạt: chọn nhiều → tạo video / đăng / xoá.
- Sửa kịch bản, caption trực tiếp.

### 1.5 Dashboard
- KPI cards (thẻ chính: "Chờ đăng"), tổng đăng, lượt xem, lượt thích.
- Lịch tháng truy cập được bằng bàn phím (link có `aria-label`, `aria-current`).
- Thẻ video của ngày đã chọn, top video, danh sách Page.

### 1.6 Cài đặt
- URL backend + kiểm tra kết nối.
- Video: nguồn footage, tỉ lệ, font, giọng đọc, nhạc nền.
- Facebook Pages: thêm Page (ID + token), kiểm tra token.
- Shopee Affiliate: tracking ID, CTA, hashtag, template caption.
- **🧪 Chế độ thử nghiệm**: chạy toàn bộ luồng không cần LLM/backend/Facebook.

### 1.7 UI / UX / Accessibility (WCAG 2.2 AA)
- Design system 5 màu (INK, MUTED, LINE, CANVAS, ACCENT), spacing 4/8/12/16/24/32, cỡ chữ 12/14/16/20/28.
- Form 1 cột, validate khi rời ô (on blur) với hướng dẫn sửa cụ thể, lỗi có `role="alert"`.
- Trạng thái busy: khoá input, đổi nhãn nút; thông báo flash sau thao tác.
- Responsive 390 / 768 / 1440 px: dưới 768px cột chuyển thành card xếp chồng, không cuộn ngang.
- Vùng chạm tối thiểu 44px, focus hiển thị rõ, hỗ trợ `prefers-reduced-motion`.
- Thay nút chỉ có icon bằng nút có chữ.

---

## Phần 2 — MoneyPrinterTurbo (chỉ phần tôi thêm)

| Tính năng | File | Mô tả |
|---|---|---|
| Nguồn video `local_cache` | `app/services/task.py`, `webui/Main.py`, i18n | "Reuse Downloaded Videos": dùng lại video trong `storage/cache_videos` thay vì gọi API; đã thêm vào whitelist `_SUPPORTED_VIDEO_SOURCES`, lỗi được đánh dấu bằng `_mark_task_failed` |
| Social metadata `.md` | `app/services/task.py` | Sau khi render, tự sinh title/caption/hashtag cho TikTok, YouTube Shorts, Instagram Reels, Facebook Reels → `storage/tasks/<id>/social_metadata.md`; lỗi không làm hỏng task |
| Ghi nguồn footage | `app/services/task.py` | `_build_attribution_section` thêm phần ghi công tác giả footage vào metadata |
| LLM provider LM Studio | `app/models/llm_provider.py` | Provider `lmstudio` (OpenAI-compatible, `localhost:1234`) |
| TTS OpenAI-compatible fallback wav | `app/services/voice.py` | Server TTS không hỗ trợ mp3 (vd. VieNeu-TTS) → tự thử lại với `wav` rồi chuyển sang mp3 bằng ffmpeg |
| Bản dịch Tiếng Việt | `webui/i18n/vi.json` | Bổ sung key còn thiếu (Match Materials to Script Order, …) |
| Sửa test | `test/services/test_llm.py` | Cập nhật thứ tự provider có `lmstudio` |

> Các tính năng cũ đã bỏ khi merge v1.3.10: provider `claude` tự viết (upstream đã có `anthropic`, `claude_code`),
> `terms_per_sentence`, `page_url`.

### Tích hợp giọng đọc local VieNeu-TTS
- Cài ở `D:\Github\VieNeu-TTS`, chạy `.venv\Scripts\python -m apps.openai_speech` (cổng 8000).
- Khai báo trong `config.toml` mục `[chatterbox]` (base_url `http://127.0.0.1:8000/v1`, model `vieneu-v3-turbo`, 10 giọng).

---

## Việc còn dở
- Chọn giọng VieNeu chính thức; khi dùng VieNeu chuyển `subtitle_provider = "whisper"` và tính tốc độ đọc theo từng giọng.
- Chạy lại toàn bộ test suite upstream.
- Xuất ảnh chụp responsive (PNG).
