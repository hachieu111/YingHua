# Code Style

## Python
- Format và lint bằng **ruff** (`ruff format`, `ruff check`), độ dài dòng 110.
- **Type hint bắt buộc** cho mọi hàm/phương thức; `mypy` không lỗi ở `domain/` và `application/`.
- Dùng `from __future__ import annotations` khi cần; ưu tiên `X | None` thay cho `Optional[X]`.
- Entity/value object dùng `@dataclass(slots=True)` (value object thêm `frozen=True`).
- Async: mọi I/O (DB, HTTP, file) trong API là `async`; việc nặng CPU không chạy trong event loop của API.
- Import theo thứ tự: chuẩn → bên thứ ba → nội bộ (ruff isort). Import tuyệt đối từ `app.`.
- Chuỗi hiển thị cho người dùng và thông báo lỗi: **tiếng Việt**. Tên biến, hàm, lớp: **tiếng Anh**.

## JavaScript (frontend)
- ES modules, `const`/`let` (không `var`), `async/await`, không jQuery.
- Gọi API qua một module `api.js` duy nhất (gắn token, xử lý 401 → làm mới phiên).
- Không chèn HTML từ dữ liệu người dùng bằng `innerHTML`; dùng `textContent` hoặc escape.

## SQL / Migration
- Từ khóa SQL viết HOA; tên bảng/cột `snake_case`.
