# Thiết kế hệ thống

Tài liệu nguồn: `docs/user-stories.md`, `docs/modules-functions.md`, `docs/danh-gia-luong-2-3.md`. Code phải khớp các tài liệu này; muốn lệch → hỏi trước.

## Kiến trúc tổng thể: Modular Monolith + Clean Architecture
```
Trình duyệt ──HTTP/JSON──> API FastAPI (1 process, 15 module M01–M15)
                              │            ├── PostgreSQL
                              │            ├── FileStorage (ảnh, audio)
                              │            ├── Edge TTS (ngoài)
                              │            └── LLM (ngoài)
                              └── bảng job ──> Worker xử lý ảnh (process riêng: YOLO → OCR → tách từ → dịch → inpaint → render)
```
- **Một ứng dụng FastAPI**, chia module theo `docs/modules-functions.md` (M01 Xác thực … M15 Tác vụ nền). Không tách microservice, không API Gateway riêng.
- Chỉ phần nặng (pipeline ảnh) chạy ở **worker riêng**; FSRS, tra HSK, chấm bài chạy ngay trong request.
- Tác vụ định kỳ (M15): dọn file hết hạn, tối ưu tham số FSRS, nhắc ôn — chạy bằng scheduler trong worker, không chạy trong process API.

## Clean Architecture — quy tắc phụ thuộc
```
presentation (api)  ──>  application (use case, port)  ──>  domain (entity, quy tắc)
infrastructure  ──implements──>  port của application
```
- **domain**: thuần Python. Không import FastAPI, SQLAlchemy, Pydantic, thư viện I/O.
- **application**: use case + interface (port). Chỉ phụ thuộc domain. Không biết HTTP, không biết SQL.
- **infrastructure**: hiện thực port (repository SQLAlchemy, storage, TTS, LLM, FSRS adapter, pipeline adapter).
- **presentation**: router FastAPI, schema request/response, dependency (lấy user hiện tại, tạo use case). Không chứa logic nghiệp vụ.
- Lắp ghép phụ thuộc (dependency injection) ở `container.py`/dependency của FastAPI — **không** khởi tạo repository trong use case.

## Giao tiếp giữa module
- Module A chỉ gọi module B qua **application interface công khai** của B (`<module>/application/public.py`), không import domain nội bộ, repository hay model ORM của B.
- Không có vòng phụ thuộc giữa các module.
- Sự kiện liên module (vd. "từ được lưu" → tạo thẻ) gọi qua use case của module đích trong cùng giao dịch hoặc qua domain event; chọn cách nào phải ghi rõ.

## Luồng nghiệp vụ đã chốt
- Lưu từ: tra HSK (bảng) → cắt ảnh ngữ cảnh → tạo mục từ + ngữ cảnh + thẻ FSRS trong **một giao dịch**.
- Ôn tập: thẻ đến hạn = `due <= now` khi truy vấn; mỗi lượt chấm cập nhật thẻ và ghi lượt ôn trong một giao dịch.
- Kiểm tra: chọn từ theo độ nhớ R → LLM sinh JSON → kiểm schema + đối chiếu từ điển → lỗi thì đề dự phòng → **chấm ở máy chủ** → từ sai đặt `due = now`.
