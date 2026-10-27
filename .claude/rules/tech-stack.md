# Công nghệ sử dụng (đã chốt)

Chỉ dùng công nghệ trong danh sách này. Muốn thêm, thay hoặc nâng phiên bản lớn → hỏi người dùng trước (xem `change-control.md`).

## Backend
| Hạng mục | Công nghệ | Ghi chú |
|---|---|---|
| Ngôn ngữ | Python 3.10+ | Type hint bắt buộc; 3.10 vì môi trường paddle/YOLO hiện có (đã chốt 23/10/2026) |
| Web framework | **FastAPI** | **Không dùng C#/ASP.NET, Django, Flask** |
| Validate / DTO | Pydantic v2, pydantic-settings | Cấu hình đọc từ biến môi trường / `.env` |
| ORM | SQLAlchemy 2.0 (async) + asyncpg | Chỉ dùng ở tầng infrastructure |
| Migration | Alembic | Không sửa CSDL bằng tay |
| CSDL | PostgreSQL 16 | Không dùng MySQL/SQLite cho môi trường thật (SQLite chỉ cho test đơn vị nếu cần) |
| Xác thực | JWT (PyJWT) access token + refresh token xoay vòng | Mật khẩu băm **Argon2id** (`argon2-cffi`) |
| Hàng đợi xử lý ảnh | Bảng job trong PostgreSQL (`FOR UPDATE SKIP LOCKED`) + process worker riêng | Không thêm Redis/Celery khi chưa được duyệt |
| Lưu trữ file | Hệ thống file cục bộ sau một port `FileStorage` | Có thể đổi sang S3/MinIO bằng adapter mới |

## Xử lý ảnh & ngôn ngữ (module `module xử lí ảnh/`, chạy trong worker)
YOLO (ultralytics) phát hiện bong bóng · PaddleOCR · OpenCV inpaint · Pillow đắp chữ · jieba tách từ · bộ từ điển VietPhrase/LuatNhan/Names/PhienAm (dịch offline).

## Học tập
- Lặp lại ngắt quãng: **FSRS** (thư viện `fsrs`), 4 mức Quên/Khó/Được/Dễ. Không dùng SM-2.
- Cấp HSK: **tra bảng** danh sách HSK 3.0; không có thì lấy cấp cao nhất của chữ cấu thành. **Không dùng mô hình AI** để phân loại HSK.

## Dịch vụ ngoài
- TTS: `edge-tts`, có cache.
- LLM (sinh đề kiểm tra, Flashcard AI): **Google Gemini** (người dùng chọn 25/10/2026), gọi REST bằng `httpx` qua port
  (`QuizGenerator`, `AiNoteGenerator`), không dùng SDK riêng. Model và mức "thinking" đặt trong `.env` (`LLM_MODEL`,
  `LLM_THINKING_LEVEL`; hiện `gemini-flash-lite-latest` + `low`). Khóa API chỉ để trong `.env`, gửi qua header, không đặt trong URL.
  Đổi nhà cung cấp khác phải hỏi người dùng.

## Frontend
**React 19 + TypeScript + Vite + Tailwind CSS** — giao diện của người dùng ở `frontend/frontend-YingHua/` (chốt 23/10/2026).
Claude tích hợp (thay dữ liệu giả bằng gọi API, thêm lớp gọi API) và **được tự điều chỉnh giao diện** cho hợp lý, nhưng giữ bộ màu, font, logo (xem `dev-workflow.md`); bỏ qua phần server/Express/Gemini trong thư mục đó. Thêm thư viện frontend mới → hỏi trước.
Điều hướng: **React Router 8** (gói `react-router`, chế độ declarative; `react-router-dom` đã bị bỏ từ v8), chọn 25/10/2026 để mỗi trang
có URL riêng. Quy tắc code React và bảo mật frontend: `frontend-react.md`.

## Công cụ phát triển
pytest, pytest-asyncio, httpx (test API) · ruff (lint + format) · mypy · pre-commit (tùy chọn).

## Cấm
- Thêm thư viện chỉ để làm việc mà thư viện chuẩn/đã có làm được.
- Dùng thư viện không còn bảo trì hoặc tải từ nguồn không chính thống.
- Ghim phiên bản lỏng (`*`); `requirements.txt` phải ghi phiên bản cụ thể.
