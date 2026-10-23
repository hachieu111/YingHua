# Log & giám sát

- Dùng module `logging` chuẩn, cấu hình ở `app/core/logging.py`; log dạng JSON một dòng ở môi trường triển khai.
- Mỗi request có `request_id` (middleware), gắn vào mọi log và trả trong header `X-Request-ID`.
- Mức log: `DEBUG` chi tiết dev · `INFO` sự kiện nghiệp vụ (đăng nhập, job xong) · `WARNING` dự phòng được kích hoạt (LLM lỗi → đề dự phòng, TTS lỗi) · `ERROR` lỗi cần xử lý.
- Log job xử lý ảnh: id job, từng bước, thời gian mỗi bước, lý do lỗi.
- Log lời gọi dịch vụ ngoài: tên dịch vụ, thời gian phản hồi, thành công/thất bại (không log nội dung nhạy cảm, không log khóa API).
- **Không log**: mật khẩu, token, nội dung `.env`, dữ liệu cá nhân không cần thiết.
- Endpoint `GET /api/v1/health` kiểm tra API + CSDL; worker ghi heartbeat để admin thấy trạng thái (M13).
- Hành động quản trị (đổi vai trò, khóa tài khoản, xóa truyện) ghi vào nhật ký quản trị (F13.06).
