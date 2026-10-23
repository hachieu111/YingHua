# Quy tắc CSDL (PostgreSQL + SQLAlchemy 2.0 + Alembic)

## Chung
- **Không viết SQL thô trong domain/application.** Mọi truy cập dữ liệu đi qua repository ở infrastructure.
- Trong repository ưu tiên SQLAlchemy Core/ORM; SQL thô chỉ khi cần tính năng đặc thù (vd. `FOR UPDATE SKIP LOCKED`, full-text) và luôn dùng tham số bind — **không nối chuỗi**.
- Thao tác nhiều bước dùng **Unit of Work / một giao dịch** (vd. lưu từ = mục từ + ngữ cảnh + thẻ; chấm thẻ = cập nhật thẻ + ghi lượt ôn).
- Dùng connection pool của engine async; không tạo engine/kết nối mới mỗi request. Session theo request qua dependency.

## Schema
- Mọi thay đổi schema qua **migration Alembic mới**. Không sửa migration đã chạy. Đổi schema phải hỏi trước.
- Khóa chính `BIGINT GENERATED ALWAYS AS IDENTITY` (hoặc UUID nếu được duyệt).
- Thời gian `TIMESTAMPTZ`, lưu UTC; có `created_at`, `updated_at` ở bảng nghiệp vụ.
- Enum dùng `VARCHAR + CHECK` hoặc enum PostgreSQL — chọn một cách cho toàn dự án (mặc định `VARCHAR + CHECK`).
- Ràng buộc nghiệp vụ đặt cả ở CSDL: `UNIQUE (user_id, term)` cho sổ tay, `CHECK (rating BETWEEN 1 AND 4)`, khóa ngoại có `ON DELETE` rõ ràng.
- Đánh index cho cột lọc thường dùng: `(user_id, due_at)` của thẻ, `(status)` của job, cột tìm kiếm từ điển.

## Truy vấn
- Chỉ lấy cột cần dùng; tránh N+1 (dùng `selectinload`/join).
- Danh sách luôn phân trang hoặc có `LIMIT`.
- Mọi truy vấn dữ liệu cá nhân **phải lọc theo `user_id`** của người đang đăng nhập.

## Dữ liệu
- Không lưu file nhị phân trong CSDL; chỉ lưu khóa/đường dẫn tương đối tới FileStorage.
- Script nạp từ điển/HSK chạy theo lô, idempotent (chạy lại không nhân bản dữ liệu).
- Không chạy `DROP`, `TRUNCATE`, `DELETE` không điều kiện trên CSDL thật khi chưa hỏi.
