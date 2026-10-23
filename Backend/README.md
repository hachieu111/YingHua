# YingHua Backend (FastAPI + PostgreSQL)

## Chạy

```bash
cd Backend
pip install -r requirements.txt
cp .env.example .env            # điền DATABASE_URL, JWT_SECRET
python -m uvicorn app.main:app --port 8001
```

- Giao diện test toàn bộ API: http://localhost:8001/
- Swagger: http://localhost:8001/docs
- `PIPELINE_ENABLED=false` trong `.env` để chạy API nhanh, không nạp YOLO/PaddleOCR.
- Email nằm trong `ADMIN_EMAILS` khi đăng ký sẽ tự thành admin.

Database: tạo mới từ `db/schema.sql`. DB cũ thì chạy lần lượt `db/migrations/*.sql`. Nạp từ điển bằng
`scripts/import_dictionaries.py` (xem docstring đầu file).

Kiểm thử end-to-end (server phải đang chạy, có chạy pipeline thật): `python tests/smoke_e2e.py`

## Cấu trúc

```
app/
  main.py              app, CORS, worker pipeline, job dọn file hết hạn (mỗi 60 phút)
  config.py            đọc .env
  models.py            ORM khớp db/schema.sql
  security.py          bcrypt, JWT access token, refresh token xoay vòng
  routers/             auth, me, library, dictionary, vocab, review, suggestions, tts, admin
  services/
    pipeline_runner.py worker 1 luồng gọi module xử lí ảnh (YOLO → OCR → dịch → xoá chữ → đắp chữ)
    library.py         upload, chống trùng sha256 + pHash, hạn lưu 7 ngày cho ảnh upload
    dictionary.py      tra 2 bộ từ điển (đầy đủ / tu tiên), jieba tách từ
    vocab.py           sổ tay + ngữ cảnh + ảnh cắt bong bóng (.webp)
    srs.py             SM-2
    suggestions.py     gợi ý từ theo chương (xếp hạng theo luật)
    tts.py             edge-tts + cache
ui/                    giao diện HTML/JS thuần để chạy thử mọi API
```

## Đăng nhập & refresh token

- `POST /api/auth/login` trả `access_token` (JWT, 15 phút) và `refresh_token` (chuỗi ngẫu nhiên, 30 ngày).
  DB chỉ lưu SHA-256 của refresh token.
- `POST /api/auth/refresh` **xoay vòng**: token cũ bị vô hiệu, trả cặp token mới cùng "family".
  Nếu một token đã bị thay thế mà vẫn được gửi lại (dấu hiệu bị đánh cắp), **cả phiên đăng nhập bị thu hồi**.
- `logout` thu hồi phiên hiện tại. `logout-all` và `change-password` thu hồi mọi phiên.

## Nhóm API chính

| Nhóm | Endpoint |
|---|---|
| Auth | `/api/auth/register, login, refresh, logout, logout-all, me, change-password` |
| Cá nhân | `/api/me/settings, progress, stats` |
| Thư viện | `/api/series`, `/api/series/{id}/chapters`, `/api/chapters/{id}`, `/api/chapters/{id}/pages` (upload), `/api/uploads/quick`, `/api/chapters/{id}/progress` |
| Trang | `/api/pages/{id}` (bubbles + lines + tokens), `/api/pages/{id}/image/{original\|rendered\|inpainted}?download=true`, `/api/pages/{id}/retranslate`, `/api/translations/{id}` |
| Sửa dịch | `PUT/DELETE /api/bubbles/{id}/edit` (chỉ áp dụng cho người sửa) |
| Từ điển | `/api/dict/lookup, search, xianxia/search, hanzi/{ch}, segment, events` |
| Sổ tay | `/api/vocab`, `/api/vocab/{id}`, `/api/vocab/{id}/contexts`, `/api/vocab/contexts/{id}/snippet` |
| Ôn tập | `/api/review/due`, `POST /api/review/{card_id}`, `/api/review/history`, `/api/flashcards/{id}`, `/api/flashcards/{id}/reset` |
| Gợi ý | `/api/chapters/{id}/suggestions`, `/api/suggestions/{id}/accept, dismiss` |
| TTS | `/api/tts?text=`, `/api/tts/voices` |
| Admin | `/api/admin/users, translations, translations/{id}/retry, stats` |

## Ghi chú

- Backend **không sửa code** của `module xử lí ảnh`. Nó chỉ trỏ lại 3 đường dẫn đang hardcode trước khi khởi tạo:
  model YOLO, thư mục font, và thư mục từ điển tu tiên. `translator.py` vẫn trỏ tới `từ điển/`, trong khi 4 file
  đã được chuyển sang `từ điển tu tiên/`, nên nếu chạy `main.py` cũ trực tiếp, bộ dịch sẽ không nạp được từ điển.
- Hàm `process_and_save` của module tự ghi 1 file vào `dataset/inpainted/`. Worker xoá file đó ngay sau khi đọc kết quả.
- Từ điển đầy đủ hiện **chưa có cấp HSK** nên điểm gợi ý chủ yếu dựa vào tần suất trong chương và lịch sử tra cứu.
- Xoá truyện/chương thì file ảnh của thư viện chung vẫn còn trên đĩa (không có hạn). Ảnh upload tự xoá sau 7 ngày.
