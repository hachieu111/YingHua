# Kế hoạch triển khai YingHua

> Căn cứ: `docs/modules-functions.md` (15 module, 124 chức năng), `docs/user-stories.md` (118 user story), `.claude/rules/*`, skill `yinghua-guardrails`.
> Trạng thái (24/10/2026): GĐ0, GĐ0.5, GĐ1 **xong**. **GĐ2 (M06 Từ điển) xong**: migration 0003–0004, nạp CVDICT/HSK/Tatoeba/Thiên Chửu/tu tiên, 180 test (Haiku kiểm độc lập), giao diện Navbar/Catalog/khung tra từ đã nối. **GĐ3 (M03 Thư viện, M04 Xử lý ảnh + worker, M05 Đọc truyện, M15 Tác vụ nền) xong (24/10/2026)**: migration 0005, 304 test qua, worker dịch ảnh chạy thật (YOLO → OCR → dịch → xóa chữ → đắp chữ), giao diện Catalog/Thư viện/Upload/Đọc truyện đã nối; còn mở: chống ảnh trùng theo pHash, giới hạn Khách theo IP, một số luật LuatNhan. **GĐ4 (M07 Sổ tay, M08 Ôn tập FSRS, M11 Phát âm) xong (24/10/2026)**: migration 0006, lưu từ kèm ảnh ngữ cảnh + 3 thẻ trong một giao dịch, ôn thẻ FSRS 4 mức (chống bấm đúp), Edge TTS có cache và dự phòng Web Speech; bổ sung F07.09 (đánh dấu sao), F07.10 (âm Hán Việt), F08.10 (bộ thẻ theo truyện) và F13.07 (admin xem/sửa toàn bộ dữ liệu người dùng, có nhật ký; US-QT-14) theo quyết định 24/10/2026; 408 test qua; giao diện Flashcard/Sổ tay/phát âm/trang quản trị đã nối. Việc còn mở: `docs/ton-dong-gd3.md` (mục GĐ3 và GĐ4). **GĐ5 xong (25/10/2026)**: migration 0007–0008, M09 Kiểm tra (đề AI Gemini + đề dự phòng, câu ví dụ có lọc độ khó, 15% từ mở rộng), M10 Gợi ý (từ trong chương, gợi ý truyện, độ phủ), thêm F07.11, F07.12, F08.11, F02.04, xóa avatar, danh sách giọng; 554 test qua; giao diện bài kiểm tra/gợi ý/câu thoại/Flashcard AI/cài đặt học tập/trang quản trị xử lý ảnh–tác vụ nền đã nối; LLM: Google Gemini (chọn 25/10/2026). Việc còn mở: `docs/ton-dong-gd3.md` (mục GĐ5). **Tiếp theo: GĐ6.**

## 1. Hiện trạng (rà soát ngày 23/10/2026)

| Thành phần | Tình trạng | Quyết định |
|---|---|---|
| `Backend/` (FastAPI, ~5.200 dòng) | Chạy được; cấu trúc `routers/ + services/` (không Clean Architecture); SQLAlchemy **sync** + psycopg2; bcrypt; **SM-2**; chưa có test đơn vị; chưa có Alembic | **Không mở rộng.** Dùng làm nguồn tham khảo, chuyển logic tốt sang cấu trúc mới (bảng dưới). Xong giai đoạn 8 thì chuyển vào `legacy/` (hỏi trước). |
| `Backend/db/schema.sql` (24 bảng) | Thiết kế bảng khá đầy đủ (truyện, trang, bong bóng, sổ tay, thẻ, từ điển, tu tiên, TTS cache) | Làm **cơ sở** cho ORM + migration Alembic đầu tiên, chỉnh tên theo `naming-conventions.md`, thêm bảng còn thiếu (HSK, quiz, job, báo lỗi, thông báo, nhật ký quản trị, đặt lại mật khẩu). |
| CSDL `ptud_db` (PostgreSQL 16 đang chạy) | Đã nạp: 12.139 mục từ, 9.574 chữ Hán, 1.018.937 mục tu tiên, 118 luật nhân | Giữ nguyên làm nguồn; tạo CSDL mới `yinghua_db` và **chép dữ liệu từ điển** sang bằng script (không nạp lại từ file). |
| `module xử lí ảnh/` (YOLO, PaddleOCR, inpaint, render, ~3.000 dòng) | Hoạt động; `Backend/app/services/pipeline_runner.py` đã bọc được | Giữ nguyên module; worker mới gọi qua adapter (chuyển từ `pipeline_runner.py`). |
| `Backend/ui/` (JS thuần, ~1.500 dòng) | Màn đọc, thư viện, học, cá nhân | Chuyển dần sang `frontend/`, gọi `/api/v1`. |
| Môi trường | **Python 3.10.11**; đã có fastapi, SQLAlchemy 2.0.45, alembic 1.12, pydantic 2, PyJWT, edge-tts, jieba, paddle, ultralytics | **Thiếu**: asyncpg, argon2-cffi, fsrs, pytest, pytest-asyncio, ruff, mypy. **Chưa có danh sách HSK 3.0** trong repo. |

### Logic tái sử dụng từ `Backend/`

| Nguồn cũ | Chuyển sang |
|---|---|
| `security.py` (JWT, refresh token xoay vòng, thu hồi cả family) | `core/security.py` + `modules/auth/` (đổi bcrypt → Argon2id, vẫn đọc được hash bcrypt cũ khi chép user) |
| `services/dictionary.py`, `scripts/import_dictionaries.py` | `modules/dictionary/infrastructure/` + `server/scripts/` |
| `services/pipeline_runner.py` | `worker/pipeline_adapter.py` (M04) |
| `services/tts.py` | `modules/tts/infrastructure/edge_tts_gateway.py` |
| `services/suggestions.py` (công thức xếp hạng) | `modules/suggestions/domain/` |
| `services/library.py` (sha256 + pHash chống trùng) | `modules/library/` + `modules/imaging/` |
| `services/srs.py` (SM-2) | **Bỏ**, thay bằng FSRS |

## 2. Cách làm

- **Mỗi giai đoạn là một lát cắt dọc** (CSDL → domain → use case → API → giao diện → test) và **dùng thử được** khi kết thúc.
- **Đầu mỗi giai đoạn**: tôi gửi đề xuất chi tiết (file, bảng, endpoint) theo mẫu `change-control.md`. Bạn duyệt xong mới làm.
- **Cuối mỗi giai đoạn**: chạy `ruff`, `mypy`, `pytest`, demo, rồi báo kết quả thật. Chỉ commit khi bạn yêu cầu.
- **Giao việc** theo `CLAUDE.md`:
  - Giai đoạn 0 tôi tự làm, vì đây là phần dựng khung mẫu.
  - Các module sau giao cho `yinghua-backend-dev` (sonnet).
  - Worker xử lý ảnh giao cho `yinghua-vision` (opus).
  - Giao diện giao cho `yinghua-frontend-dev` (sonnet).
  - Kiểm thử giao cho `yinghua-tester` (haiku).
  - Tôi rà diff của mọi agent trước khi báo bạn.

## 3. Các giai đoạn

| GĐ | Nội dung | Chức năng | Kết quả dùng thử được |
|---|---|---|---|
| **0** | **Nền tảng.** Khung `server/` theo `project-structure.md`. `core/` gồm: config, CSDL async + Unit of Work, lỗi chuẩn, logging + request_id, security. Alembic, cấu hình pytest/ruff/mypy, `GET /api/v1/health`. Cài thư viện còn thiếu. Tạo `yinghua_db`. | — | Server chạy, health OK, test mẫu qua. |
| **0.5** | **Thiết kế CSDL** cho cả 15 module: `docs/database-design.md`. Bảng được tạo dần theo từng giai đoạn, đúng thiết kế đã duyệt. | — | Thiết kế được duyệt. |
| **1** | **Tài khoản & quyền.** M01 (trừ quên mật khẩu qua email thật: dùng adapter "hộp thư giả" ghi ra file), M02, phần người dùng của M13. | F01.01–09, F02.01–03, F13.01–03, F13.06 | Đăng ký, đăng nhập, làm mới phiên, đổi mật khẩu, cài đặt HSK/giọng, admin khóa/đổi vai trò. |
| **2** | **Từ điển.** M06. Script chép dữ liệu từ `ptud_db`. Nạp danh sách HSK. Xác định cấp HSK (F06.08). | F06.01–08 | Tra từ, tìm kiếm, tu tiên, tách câu, phân rã chữ Hán. |
| **3** | **Thư viện, xử lý ảnh, đọc truyện.** M03, M04 (hàng đợi bằng bảng job + worker riêng + adapter pipeline), M05, M15 (dọn file hết hạn, dọn phiên). | F03.* (gồm F03.13 thư viện/yêu thích, F03.14 chấm sao), F04.*, F05.* (gồm F05.07 lưu trang, F05.08 ghi chú), F15.*, F01.10 (avatar) | Tải ảnh lên, worker nhận diện và dịch, đọc 3 dạng, Hover & Dịch, sửa bản dịch. |
| **4** | **Sổ tay, Ôn tập, Phát âm.** M07, M08 (FSRS, 3 loại thẻ), M11 (Edge TTS + cache). | F07.01–07, F07.09, F07.10, F08.01–07, F08.09, F08.10, F11.*, **F13.07** (bổ sung theo yêu cầu người dùng 24/10/2026: admin xem/sửa dữ liệu học tập của người dùng, làm sau khi M07, M08 có) | Lưu từ kèm ảnh ngữ cảnh, ôn thẻ 4 mức, nghe phát âm; admin xem và sửa sổ tay, thẻ, cài đặt của người dùng. |
| **5** | **Kiểm tra & Gợi ý.** M09: làm **đề dự phòng trước**, sau đó thêm adapter LLM. M10. | F09.* (gồm **F09.09** câu hỏi từ mở rộng, bổ sung 25/10/2026), F10.* (gồm **F10.04** gợi ý truyện theo trình độ, **F10.05** độ phủ từ vựng của chương), **F07.11** lưu câu thoại, **F07.12** lưu tất cả từ của trang, **F08.11** Flashcard AI, **F02.04** cỡ chữ bong bóng dịch (bổ sung 25/10/2026; thêm bảng `saved_sentences`, `vocab_ai_notes` và cột `user_settings.bubble_font_scale`); nối giao diện: tải avatar (F01.10), xóa ảnh tải nhanh và sửa/xóa truyện, chương (F03.09), cài đặt người học (F02.01–F02.03), giám sát xử lý ảnh (F04.05), tác vụ nền (F15.03) | Tạo đề (mỗi câu có câu ví dụ, 15% từ mở rộng), nộp bài, chấm ở máy chủ, từ sai về ôn sớm. Gợi ý từ theo chương, gợi ý truyện và độ phủ từ vựng. Lưu câu thoại, lưu cả trang, Flashcard AI (Gemini, có dự phòng khi LLM lỗi). |
| **6** | **Thống kê, Quản trị, Thông báo.** M12, phần còn lại của M13 (kiểm duyệt, cấu hình LLM/TTS), M14. Xuất sổ tay (F07.08). Tối ưu FSRS (F08.08). | F12.*, F13.04–05 (F13.05 mở rộng: chế độ bảo trì, kiểm duyệt ảnh tự động, OCR khi tải, thông báo quản trị), F14.*, F07.08, F08.08, **F01.11** ghi nhớ đăng nhập, **F04.16** thử với trang mẫu; mở rộng F01.10 (chọn avatar có sẵn, thêm cột `users.avatar_preset`) | Bảng thống kê, báo lỗi, nhắc ôn, xuất CSV/Anki. Ghi nhớ đăng nhập, trang mẫu, chọn avatar có sẵn, công tắc hệ thống. |
| **6.5** | **M16 Gamification** (XP, nhiệm vụ ngày, bảng xếp hạng, huy hiệu, mục tiêu) và **M17 VIP & Phần thưởng**. Viết user story + đặc tả, trình duyệt trước khi làm. Giới hạn Flashcard AI theo VIP (F08.11, giao diện quảng cáo "3 ngày mở khóa VIP & Flashcard AI") làm ở M17. | (bổ sung) | Bảng xếp hạng, huy hiệu, VIP chạy bằng dữ liệu thật. |
| **6.6** | **M18 Nội dung cộng đồng** (gửi bài, hàng chờ duyệt, duyệt tác giả), **M19 OAuth** (Google/WeChat/Apple), đổi email. Viết user story + đặc tả, trình duyệt trước khi làm. Đã có SRS: **F13.08** trang nội dung pháp lý, **F13.09** xuất báo cáo vi phạm; M18 còn có "duyệt nhanh tự động" (sắp xếp hàng chờ bằng luật, quản trị viên vẫn quyết định; viết mã F khi làm M18). | F13.08, F13.09 (bổ sung) | Mọi nút trên giao diện đều có chức năng thật. |

> **Nguyên tắc (23/10/2026): không xóa giao diện nào.** Mọi tính năng trên giao diện React đều được làm, theo bảng ở `docs/database-design.md` §8; tính năng ngoài SRS được thêm vào đúng giai đoạn của module liên quan.
| **7** | **Hoàn thiện tích hợp giao diện.** Đọc thử cho Khách (F03.01, F03.03, F05.04), rà toàn bộ luồng trên giao diện React. | F03.01, F03.03, F05.04 | Chạy được toàn bộ luồng trên trình duyệt và điện thoại. |
| **8** | **Hoàn thiện.** Test E2E theo tiêu chí chấp nhận, rà bảo mật (`/security-review`), tài liệu cài đặt và API, chuyển `Backend/` cũ vào `legacy/` (hỏi trước). | — | Bản nộp đồ án. |

**Quy trình (`.claude/rules/dev-workflow.md`, 24/10/2026):** Claude được tự điều chỉnh giao diện nhưng giữ bộ màu, font, logo; tính năng có trên giao diện mà thiếu trong hệ thống thì thêm vào code và SRS cho đồng bộ; kiểm thử thủ công dùng một tài khoản QA cố định và giữ server chạy liên tục.

Thứ tự phụ thuộc: 0 → 0.5 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.

**Luồng giao diện (chạy song song).** Giao diện là React của người dùng ở `frontend/frontend-YingHua/`. Claude không thiết kế lại, chỉ tích hợp: thêm lớp gọi API (`src/api/`), thay dữ liệu giả (mock) bằng dữ liệu thật, và bỏ qua phần Express/Gemini. Mỗi giai đoạn backend xong thì tích hợp ngay các màn hình liên quan:

| GĐ backend | Màn hình React tích hợp |
|---|---|
| 1 | Đăng nhập / đăng ký, hồ sơ, cài đặt tài khoản, admin quản lý người dùng |
| 2 | Popup tra từ, phân rã chữ |
| 3 | Catalog, Thư viện, Upload, Đọc truyện (bong bóng, sửa dịch, ghi chú) |
| 4 | Flashcard, phát âm |
| 5 | Bài kiểm tra, gợi ý từ |
| 6 | Hồ sơ (thống kê, chuỗi ngày), Admin (khiếu nại, cài đặt), thông báo |

## 4. Định nghĩa "xong" cho mỗi chức năng

1. Use case có docstring ghi mã F/US. Đúng tầng, đúng quy tắc phụ thuộc.
2. Có unit test cho tiêu chí chấp nhận chính, và API test cho đường đi chính + lỗi quyền (403/404).
3. `ruff check`, `mypy` (domain, application), `pytest` đều qua.
4. Endpoint có trong OpenAPI, có `summary` tiếng Việt.
5. Không bí mật trong code/log. Dữ liệu cá nhân lọc theo `user_id`.

## 5. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Paddle/YOLO nặng, chạy CPU chậm | Worker riêng, xử lý tuần tự. Có cờ `PIPELINE_ENABLED=false` để dev nhanh. |
| Danh sách HSK chưa có | Cần tải danh sách HSK 3.0 từ nguồn mở (xin phép trước khi tải). |
| LLM tốn phí | Nhà cung cấp: Google Gemini (chọn 25/10/2026). Giai đoạn 5 làm đề dự phòng trước, adapter LLM sau; mọi chỗ dùng LLM (F09.06, F08.11) đều có phương án dự phòng và hạn mức mỗi ngày. Khóa API do bạn tự điền vào `.env`. |
| Gửi email thật (đặt lại mật khẩu, nhắc ôn) | Port `EmailSender`; khi dev dùng adapter ghi ra file. SMTP thật thêm sau nếu cần. |
| 124 chức năng, thời gian có hạn | Ưu tiên Must → Should → Could theo user story. Giai đoạn 6 có thể cắt bớt phần Could. |

## 6. Quyết định đã chốt (23/10/2026)

1. **Python 3.10+** (đã sửa `tech-stack.md`).
2. **CSDL mới `yinghua_db`** (+ `yinghua_test` cho kiểm thử) qua Alembic; chép dữ liệu từ điển từ `ptud_db`, giữ nguyên `ptud_db`.
3. **Được cài** asyncpg, argon2-cffi, fsrs, pytest, pytest-asyncio, ruff, mypy, nâng alembic; ghim phiên bản trong `server/requirements*.txt`.
5. **Code mới ở `server/`** (không dùng `backend/` vì trùng `Backend/` trên Windows); `Backend/` cũ giữ nguyên.
4. **Danh sách HSK 3.0**: chưa chốt — sẽ hỏi (tên file, nguồn, dung lượng) ở đầu Giai đoạn 2.
