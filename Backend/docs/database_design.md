# YingHua — Thiết kế Database (v0.2)

Schema SQL đầy đủ: [`../db/schema.sql`](../db/schema.sql) (bản nháp, chưa migrate).
Stack: React + FastAPI + PostgreSQL (SQLAlchemy 2 + Alembic).

## 0. Các quyết định đã chốt

| # | Vấn đề | Quyết định |
|---|---|---|
| 1 | Nguồn truyện | **Cả hai**: thư viện chung (admin đăng, public) + người dùng tự upload (private) |
| 2 | Hiển thị | **2 chế độ**: *Học* = ảnh gốc tiếng Trung + popup + bôi đen trực tiếp trên ảnh; *Đọc* = ảnh đã đắp chữ Việt (vẽ thẳng vào ảnh, tải xuống được), không popup |
| 3 | SRS | **SM-2** trước (đã chừa cột cho FSRS) |
| 4 | Gợi ý từ vựng | **Xếp hạng theo luật** trước, LLM là giai đoạn 2 |
| 5 | Khách | **Bắt buộc đăng nhập** |
| 6 | Giữ ảnh upload | **7 ngày** |
| 7 | Floating text / SFX | **Tắt**, tập trung bong bóng thoại |
| 8 | TTS | **edge-tts** (server, miễn phí) + cache, dự phòng Web Speech API |

---

## 1. Hiện trạng đã có (từ code `module xử lí ảnh`)

- `POST /process-page` chạy: YOLO-seg tìm bong bóng → PaddleOCR → gom theo `bubble_id` → dịch bằng từ điển 4 lớp
  (LuatNhan → Names → VietPhrase → PhienAm) + `pypinyin` → inpaint OpenCV → đắp chữ PIL.
- Output mỗi bubble: `text_zh`, `pinyin`, `vi` (theo **cả bong bóng**), bbox + polygon, và các dòng OCR kèm polygon.
- **Chưa có**: lưu ảnh gốc/ảnh đã đắp chữ, hash/cache, tách từ (jieba), từ điển có cấu trúc (CC-CEDICT, HSK), DB.

Vấn đề cần sửa khi ghép vào Backend:
| Vấn đề | Vị trí | Hướng xử lý |
|---|---|---|
| Hardcode `D:\PTUD\...` cho model YOLO và font → nếu sai đường dẫn sẽ **âm thầm** chạy `ocr_only_fallback` | `pipeline.py:502`, `text_renderer.py:36-49` | Đưa vào `.env`/settings; lỗi thì log rõ ràng |
| Tên file inpainted chỉ đến giây → 2 request cùng giây ghi đè | `inpainter.py:419-423` | Đặt tên theo sha256 |
| `vi`/`pinyin` lặp lại ở mọi dòng của cùng bubble | `main.py:183-206` | Lưu 1 lần ở bảng `bubbles` |

---

## 2. Luồng dữ liệu chính

```
Upload ảnh ─► sha256 trùng? ──có──► dùng lại translation cũ
                 │ không
                 ▼
           pHash gần giống (Hamming ≤ 4)? ──có──► dùng lại translation cũ
                 │ không
                 ▼
     translations(status=queued) ─► worker chạy pipeline
                                      ├► lưu original + inpainted + rendered (stored_files)
                                      ├► bubbles (+ lines có toạ độ, + tokens jieba)
                                      └► chapter_vocab (từ của chương)

Chế độ Đọc : hiện rendered (ảnh đã đắp chữ Việt) — có nút Tải xuống
Chế độ Học : hiện original + lớp text trong suốt phủ đúng vị trí chữ Hán
             hover bubble → popup (Hán / pinyin / nghĩa Việt)
             bôi đen chữ trên ảnh → tra từ → [Lưu] → user_vocab + vocab_contexts (ảnh cắt .webp) + flashcards
Ôn tập     : flashcards đến hạn → review_logs → cập nhật SM-2
Cá nhân hoá: lookup_events + user_vocab + review_logs + hsk_level → vocab_suggestions
```

---

## 3. Bôi đen chữ trực tiếp trên ảnh — làm thế nào

Đây là kỹ thuật **"text layer" giống PDF đã OCR** (giống PDF.js, Google Lens): ảnh gốc ở dưới, phía trên phủ
các `<span>` chữ Hán **trong suốt** (`color: transparent`), mỗi span được đặt đúng toạ độ và giãn đúng kích thước
dòng chữ trên ảnh. Người dùng thấy như đang bôi đen chữ trong ảnh, nhưng thực ra đang chọn text HTML thật,
nên `window.getSelection()` lấy được chữ.

Dữ liệu cần có, và module 1 **đã có sẵn**: mỗi dòng OCR có `text` + `polygon` (PaddleOCR). Lưu vào `bubbles.lines`:
```json
[{"text": "现在你每日正午时分", "x": 412, "y": 820, "w": 260, "h": 34,
  "polygon": [[...]], "vertical": false, "confidence": 0.97, "char_boxes": null}]
```
- **Toạ độ từng chữ:** chữ Hán gần như vuông và đều nhau, nên frontend chia đều `w` (hoặc `h` nếu chữ dọc) cho số
  ký tự là đủ chính xác. Nếu cần chính xác hơn, PaddleOCR bản mới có `return_word_box=True` để lấy box từng ký tự,
  lưu vào `char_boxes`.
- **Chữ dọc** (`vertical: true`): dùng CSS `writing-mode: vertical-rl`.
- **Co giãn:** toạ độ lưu theo pixel ảnh gốc. Frontend nhân tỉ lệ `displayWidth / width` để vẽ.
- **Popup:** hover vào polygon của bubble thì hiện `text_zh`, `pinyin`, `text_vi`. Bôi đen trong popup vẫn hoạt
  động, làm phương án dự phòng.

---

## 4. Các nhóm bảng (16 bảng)

| Nhóm | Bảng | Ghi chú |
|---|---|---|
| Người dùng | `users`, `user_settings` | `role` user/admin; `hsk_level`, `default_mode` (read/learn) |
| File | `stored_files` | DB **chỉ lưu đường dẫn**, file nằm ở `storage/`. `expires_at` để cronjob dọn |
| Nội dung | `series`, `chapters`, `pages` | `series.owner_id` NULL = thư viện chung; có giá trị = truyện user tự upload (private) |
| Kết quả dịch | `translations`, `bubbles`, `bubble_edits` | `translations` gắn với **ảnh**, không gắn với page → dùng chung khi trùng ảnh |
| Tiến độ | `reading_progress` | đọc tiếp chương/trang đang dở, nhớ chế độ đang dùng |
| Từ điển | `dict_entries`, `dict_examples`, `hanzi` | dữ liệu tĩnh, import bằng script |
| Sổ tay | `user_vocab`, `vocab_contexts` | 1 từ — nhiều ngữ cảnh (ảnh cắt + câu) |
| SRS | `flashcards`, `review_logs` | 3 loại thẻ: Hán→Việt, Việt→Hán, nghe→Hán |
| Cá nhân hoá | `lookup_events`, `chapter_vocab`, `vocab_suggestions` | |
| TTS | `tts_cache` | không gọi lại TTS cho cùng câu |

**Vì sao `bubbles` là bảng riêng chứ không chỉ là 1 cột JSONB?** Sổ tay (`vocab_contexts.bubble_id`), bản sửa
(`bubble_edits`), lịch sử tra cứu và gợi ý đều cần trỏ khoá ngoại tới **từng bong bóng**.

**Vì sao `vocab_contexts` lưu snapshot câu?** Ảnh upload hết hạn sau 7 ngày, nhưng thẻ flashcard vẫn phải hiện câu
ngữ cảnh và ảnh cắt bubble (file `snippet` không có `expires_at`).

---

## 5. Lưu trữ ảnh

| Loại file | Dùng cho | Thư viện chung | Ảnh user upload |
|---|---|---|---|
| `original` | chế độ Học | vĩnh viễn | 7 ngày |
| `rendered` (đã đắp chữ Việt) | chế độ Đọc + tải xuống | vĩnh viễn | 7 ngày |
| `inpainted` (đã xoá chữ) | render lại khi sửa bản dịch / nâng cấp bộ dịch | vĩnh viễn | 7 ngày |
| `snippet` (.webp cắt bubble, khoảng 15 KB) | ảnh ngữ cảnh trên flashcard | vĩnh viễn | vĩnh viễn |
| `audio` TTS (.mp3) | phát âm | vĩnh viễn (cache) | vĩnh viễn (cache) |

- Dòng `translations` và `bubbles` (chỉ vài KB) **không xoá** khi file hết hạn, để sổ tay và thống kê vẫn trỏ được.
- **Chống trùng 2 tầng**: `sha256` (giống hệt file) và `pHash` (cùng trang nhưng nén hoặc resize khác).
  Nếu một file đang có hạn mà được dùng trong thư viện chung, đặt `expires_at = NULL`.
- Ảnh WebP thay JPEG cho `rendered` giúp giảm khoảng 30% dung lượng.

---

## 6. Hướng giải quyết cho từng tính năng

**Tách từ để tra / hover từng từ.** Sau khi dịch, backend tách `text_zh` bằng **jieba** (user dict lấy từ
`Names.txt` + từ điển) và lưu `bubbles.tokens = [{w, start, end, entry_id}]`. Khi người dùng bôi đen tuỳ ý, gửi
`term` lên API để tra `dict_entries`. Nếu không có thì ghép nghĩa từ VietPhrase/PhienAm.

**Từ điển**: CC-CEDICT (pinyin, nghĩa Anh) + danh sách HSK 3.0 (`hsk_level`) + VietPhrase/PhienAm (nghĩa Việt,
âm Hán-Việt) + makemeahanzi (bộ thủ, phân rã, thứ tự nét). Tất cả miễn phí, import một lần bằng script.

**Gợi ý từ vựng theo chương (giai đoạn 1, không cần LLM)**:
```
score = 3·[hsk_level == user_level + 1] + 1·[hsk_level == user_level]
      + 1.5·log(1 + occurrences trong chương)
      + 2·[user đã tra từ này ≥ 2 lần mà chưa lưu]
      − loại bỏ: từ đã có trong user_vocab, hoặc HSK thấp hơn trình độ user
```
`hsk_level` của user tự cập nhật: nếu tỉ lệ nhớ (rating ≥ 3) các thẻ ở cấp hiện tại > 85% thì lên cấp.

**LLM (giai đoạn 2) — không khó.** Chỉ là gọi một API trả về JSON rồi **cache** vào `dict_examples`
(source = `llm`), nên mỗi từ chỉ tốn 1 lần gọi. Có các bản miễn phí như Gemini API (free tier) hoặc Groq.
Dùng để: sinh ví dụ / giải thích cách dùng (chức năng F3 trong thuyết minh) và giải thích từ trong ngữ cảnh câu
truyện. Schema hiện tại đã đủ, không phải sửa.

**Flashcard SM-2**: rating 1–4 (Again/Hard/Good/Easy) → cập nhật `ease_factor`, `interval_days`, `due_at`. Mặt
sau thẻ: nghĩa, pinyin, Hán-Việt, ảnh cắt bubble, câu ngữ cảnh, nút phát âm.

**TTS — chọn edge-tts** (thư viện Python, dùng giọng neural của Microsoft Edge, miễn phí, không cần key):
- Giọng tiếng Trung chất lượng cao (`zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`), **giống nhau trên mọi trình
  duyệt**. Web Speech API thì phụ thuộc máy (Firefox/Windows nhiều khi không có giọng tiếng Trung).
- Backend sinh `.mp3` lần đầu, lưu `tts_cache`, các lần sau trả file luôn.
- Rủi ro: đây là API không chính thức, có thể bị chặn. Khi đó frontend tự chuyển sang **Web Speech API** dự phòng.

**Pipeline chạy lâu** (PaddleOCR trên CPU): API upload trả về `translation_id` ngay (status `queued`). Một worker
xử lý nền (FastAPI BackgroundTasks lúc đầu). Frontend poll trạng thái.

**Dọn file hết hạn**: job chạy mỗi ngày (APScheduler trong FastAPI) xoá file có `expires_at < now()` và set NULL
các khoá ngoại.
