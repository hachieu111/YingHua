# Kế hoạch triển khai YingHua

> Căn cứ: `docs/modules-functions.md` (15 module, 104 chức năng), `docs/user-stories.md`, `.claude/rules/*`, skill `yinghua-guardrails`.
> Trạng thái: **đã duyệt 23/10/2026**. Giai đoạn 0 **xong** (23/10/2026): ruff, mypy, 13 test qua; health chạy thật OK. Tiếp theo: Giai đoạn 1.

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
  - Kiểm thử giao cho `yinghua-tester` (sonnet).
  - Tôi rà diff của mọi agent trước khi báo bạn.

## 3. Các giai đoạn

| GĐ | Nội dung | Chức năng | Kết quả dùng thử được |
|---|---|---|---|
| **0** | **Nền tảng.** Khung `server/` theo `project-structure.md`. `core/` gồm: config, CSDL async + Unit of Work, lỗi chuẩn, logging + request_id, security. Alembic, cấu hình pytest/ruff/mypy, `GET /api/v1/health`. Cài thư viện còn thiếu. Tạo `yinghua_db`. | — | Server chạy, health OK, test mẫu qua. |
| **1** | **Tài khoản & quyền.** M01 (trừ quên mật khẩu qua email thật: dùng adapter "hộp thư giả" ghi ra file), M02, phần người dùng của M13. | F01.01–09, F02.01–03, F13.01–03, F13.06 | Đăng ký, đăng nhập, làm mới phiên, đổi mật khẩu, cài đặt HSK/giọng, admin khóa/đổi vai trò. |
| **2** | **Từ điển.** M06. Script chép dữ liệu từ `ptud_db`. Nạp danh sách HSK. Xác định cấp HSK (F06.08). | F06.01–08 | Tra từ, tìm kiếm, tu tiên, tách câu, phân rã chữ Hán. |
| **3** | **Thư viện, xử lý ảnh, đọc truyện.** M03, M04 (hàng đợi bằng bảng job + worker riêng + adapter pipeline), M05, M15 (dọn file hết hạn, dọn phiên). | F03.*, F04.*, F05.*, F15.* | Tải ảnh lên, worker nhận diện và dịch, đọc 3 dạng, Hover & Dịch, sửa bản dịch. |
| **4** | **Sổ tay, Ôn tập, Phát âm.** M07, M08 (FSRS, 3 loại thẻ), M11 (Edge TTS + cache). | F07.01–07, F08.01–07, F08.09, F11.* | Lưu từ kèm ảnh ngữ cảnh, ôn thẻ 4 mức, nghe phát âm. |
| **5** | **Kiểm tra & Gợi ý.** M09: làm **đề dự phòng trước**, sau đó thêm adapter LLM. M10. | F09.*, F10.* | Tạo đề, nộp bài, chấm ở máy chủ, từ sai về ôn sớm. Gợi ý từ theo chương. |
| **6** | **Thống kê, Quản trị, Thông báo.** M12, phần còn lại của M13 (kiểm duyệt, cấu hình LLM/TTS), M14. Xuất sổ tay (F07.08). Tối ưu FSRS (F08.08). | F12.*, F13.04–05, F14.*, F07.08, F08.08 | Bảng thống kê, báo lỗi, nhắc ôn, xuất CSV/Anki. |
| **7** | **Giao diện hoàn chỉnh.** Hoàn thiện `frontend/` (mỗi giai đoạn 1–6 đã có màn hình cơ bản): trang giới thiệu, đọc thử cho Khách (F03.01, F03.03, F05.04), responsive, rà UX. | F03.01, F03.03, F05.04 + UI | Chạy được toàn bộ luồng trên trình duyệt và điện thoại. |
| **8** | **Hoàn thiện.** Test E2E theo tiêu chí chấp nhận, rà bảo mật (`/security-review`), tài liệu cài đặt và API, chuyển `Backend/` cũ vào `legacy/` (hỏi trước). | — | Bản nộp đồ án. |

Thứ tự phụ thuộc: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Phần giao diện của giai đoạn N có thể làm song song với backend của giai đoạn N+1.

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
| LLM tốn phí, chưa chọn nhà cung cấp | Giai đoạn 5 làm đề dự phòng trước. Adapter LLM để sau, khóa API do bạn tự điền vào `.env`. |
| Gửi email thật (đặt lại mật khẩu, nhắc ôn) | Port `EmailSender`; khi dev dùng adapter ghi ra file. SMTP thật thêm sau nếu cần. |
| 104 chức năng, thời gian có hạn | Ưu tiên Must → Should → Could theo user story. Giai đoạn 6 có thể cắt bớt phần Could. |

## 6. Quyết định đã chốt (23/10/2026)

1. **Python 3.10+** (đã sửa `tech-stack.md`).
2. **CSDL mới `yinghua_db`** (+ `yinghua_test` cho kiểm thử) qua Alembic; chép dữ liệu từ điển từ `ptud_db`, giữ nguyên `ptud_db`.
3. **Được cài** asyncpg, argon2-cffi, fsrs, pytest, pytest-asyncio, ruff, mypy, nâng alembic; ghim phiên bản trong `server/requirements*.txt`.
5. **Code mới ở `server/`** (không dùng `backend/` vì trùng `Backend/` trên Windows); `Backend/` cũ giữ nguyên.
4. **Danh sách HSK 3.0**: chưa chốt — sẽ hỏi (tên file, nguồn, dung lượng) ở đầu Giai đoạn 2.
