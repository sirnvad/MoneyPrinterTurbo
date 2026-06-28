# 🎬 AffiliateStudio — Shopee Affiliate Video Pipeline

Công cụ tạo video ngắn (Facebook Reels / TikTok / Instagram) để gắn link affiliate
Shopee kiếm tiền. Xây trên nền **MoneyPrinterTurbo**, bổ sung một giao diện Streamlit
độc lập trong thư mục `webui/affiliate/`.

Luồng làm việc:

```
Link Shopee → Phân tích sản phẩm (AI) → Viết kịch bản (AI)
            → Tạo video → Caption + link affiliate → Đăng Facebook Page
```

---

## 1. Tính năng

### Dashboard
- Lịch nội dung theo tháng (HTML card, click ngày để xem video của ngày đó)
- Thống kê: tổng video đã đăng, lượt xem, lượt thích, video chờ đăng
- Top video theo lượt xem + danh sách Facebook Page đã kết nối

### Pipeline (màn hình chính)
- **Thêm sản phẩm**: dán 1 link Shopee → chọn Page → chọn số video (5–10)
- **Nhập hàng loạt**: dán nhiều link (mỗi dòng 1 link) hoặc upload CSV/TXT
- **Phân tích sản phẩm bằng AI (2 giai đoạn)**:
  1. *Phân tích sâu*: ngành hàng, chân dung khách hàng, nhân khẩu học, điểm đau,
     mong muốn, USP, trigger cảm xúc, lý do do dự, tình huống dùng, giọng điệu
  2. *Viết kịch bản*: mỗi video một góc tiếp cận + loại hook khác nhau
     (curiosity, shock, benefit, story, compare, problem, testimonial, tips, trend, fomo),
     kèm từ khóa tìm video footage
- **Danh sách video dạng dòng ngang**: thumbnail + chip loại hook + chip trạng thái
- **Hành động hàng loạt**: chọn nhiều video → tạo video / đăng / xoá cùng lúc
- **Soạn caption**: tự sinh từ hook + link affiliate (gắn tracking ID) + hashtag, cho sửa
- Trạng thái mỗi video: `Nháp → Render → Lên lịch → Đã đăng` (hoặc `Lỗi`)

### Cài đặt
- **LLM/AI**: URL backend MoneyPrinterTurbo + kiểm tra kết nối
- **Video**: nguồn video, tỉ lệ, font phụ đề, giọng đọc, nhạc nền
- **Facebook Pages**: thêm Page (ID + Access Token), kiểm tra token, đăng tự động
- **Shopee Affiliate**: tracking ID, CTA, hashtag mặc định, template caption
- **🧪 Chế độ thử nghiệm**: chạy toàn bộ luồng KHÔNG cần LLM / backend / Facebook

---

## 2. Cấu trúc thư mục

```
webui/affiliate/
├── main.py                 # Entry point Streamlit (3 tab)
├── store/
│   └── db.py               # SQLite: products, campaigns, fb_pages, settings
├── services/
│   ├── shopee.py           # Scrape + phân tích AI 2 giai đoạn
│   ├── video_client.py     # Gọi API MoneyPrinterTurbo tạo video
│   ├── facebook.py         # Đăng Reels qua Facebook Graph API
│   └── caption.py          # Dựng caption + gắn tracking link
└── pages/
    ├── dashboard.py        # Lịch + thống kê
    ├── pipeline.py         # Quản lý sản phẩm & video
    └── settings.py         # Cấu hình
```

Dữ liệu lưu tại `storage/affiliate.db` (SQLite, tự tạo khi chạy lần đầu).

---

## 3. Cài đặt

> Yêu cầu: đã cài đặt môi trường của MoneyPrinterTurbo (Python 3.11+, đã `pip install -r requirements.txt`).

```bash
# 1. Vào thư mục dự án
cd MoneyPrinterTurbo

# 2. (Khuyến nghị) kích hoạt virtualenv của dự án
#    Windows:
.venv\Scripts\activate
#    macOS/Linux:
source .venv/bin/activate

# 3. Đảm bảo có streamlit (đã nằm trong requirements của dự án)
pip install streamlit requests
```

---

## 4. Chạy

```bash
# Chạy giao diện AffiliateStudio
streamlit run webui/affiliate/main.py
```

Mặc định mở tại http://localhost:8501
(đổi cổng: thêm `--server.port 8502`).

> **Để tạo video thật**, cần chạy song song backend API của MoneyPrinterTurbo
> (thường ở `http://localhost:8080`) — xem hướng dẫn gốc của dự án để khởi động backend.
> URL backend khai báo trong tab **Cài đặt → LLM/AI**.

---

## 5. Dùng thử nhanh (không cần cấu hình gì)

1. Mở app → tab **Cài đặt** → bật **🧪 Chế độ thử nghiệm**
2. Tab **Pipeline** → dán link Shopee bất kỳ → **Phân tích & Tạo**
   → sinh ngay 5 kịch bản mẫu (không gọi LLM)
3. Chọn vài video → **🎬 Tạo video (n)** → giả lập render xong
4. **📤 Đăng (thử)** → đánh dấu đã đăng + sinh số liệu mẫu
5. Tab **Dashboard** → xem thống kê & lịch cập nhật

Khi muốn dùng thật: **tắt** chế độ thử nghiệm, cấu hình LLM + backend video + Facebook Page.

---

## 6. Dùng thật — checklist cấu hình

| Mục | Nơi cấu hình | Ghi chú |
|---|---|---|
| LLM (phân tích & viết kịch bản) | `config.toml` của MoneyPrinterTurbo | OpenAI / Gemini / Claude / Ollama... |
| Backend video | Tab Cài đặt → LLM/AI → API URL | Mặc định `http://localhost:8080` |
| Nguồn video footage | Tab Cài đặt → Video | Pexels / Pixabay / Coverr (cần API key) |
| Font phụ đề tiếng Việt | Tab Cài đặt → Video | 50 font có sẵn trong `resource/fonts/` |
| Facebook Page | Tab Cài đặt → Facebook Pages | Cần Page ID + Page Access Token |
| Link affiliate | Tab Cài đặt → Shopee Affiliate | Tracking ID, hashtag, template caption |

### Lấy Facebook Page Access Token
1. Tạo app tại https://developers.facebook.com
2. Cấp quyền `pages_manage_posts`, `pages_read_engagement`
3. Lấy **Page Access Token** (token dài hạn) từ Graph API Explorer
4. Dán vào tab Cài đặt → Facebook Pages → kiểm tra token → Thêm Page

---

## 7. Lưu ý

- `storage/affiliate.db` chứa toàn bộ dữ liệu (sản phẩm, kịch bản, cấu hình).
  Sao lưu file này để giữ dữ liệu; xoá nó để reset sạch.
- Scrape Shopee có thể thất bại (Shopee chặn bot) → khi đó nhập tên sản phẩm thủ công.
- Mỗi Facebook Page nên dùng cho một dòng sản phẩm cụ thể.
