# Quy ước API (FastAPI)

- Tiền tố: `/api/v1/...`. Đổi phiên bản API phải hỏi.
- REST theo tài nguyên: `GET` đọc, `POST` tạo / hành động, `PATCH` sửa một phần, `PUT` thay toàn bộ, `DELETE` xóa.
  Hành động không phải CRUD dùng động từ con: `POST /api/v1/cards/{id}/grade`, `POST /api/v1/pages/{id}/retranslate`.
- Mã trạng thái: `200` đọc/sửa, `201` tạo (kèm tài nguyên), `202` đã nhận việc nền (job), `204` xóa/không nội dung,
  `400` dữ liệu sai, `401` chưa đăng nhập, `403` không có quyền, `404` không thấy (cũng dùng khi tài nguyên của người khác để không lộ tồn tại),
  `409` trùng/xung đột, `413` file quá lớn, `422` validate, `429` vượt giới hạn, `503` dịch vụ ngoài lỗi.
- Lỗi luôn theo một dạng:
  ```json
  { "error": { "code": "VOCAB_ALREADY_SAVED", "message": "Từ này đã có trong sổ tay", "details": {} } }
  ```
- Danh sách có phân trang: `?page=1&size=20` (size ≤ 100), trả `{ "items": [...], "total": n, "page": 1, "size": 20 }`.
- Thời gian: ISO 8601, UTC. Tiền tệ/số đo không dùng float cho giá trị cần chính xác.
- Mọi endpoint khai báo `response_model` và `summary` tiếng Việt; tag theo module (`M07 Sổ tay`).
- Router mỏng: nhận request → gọi **một** use case → map kết quả sang schema. Không truy vấn CSDL trong router.
- Việc lâu (xử lý ảnh, tạo đề LLM > 2 s) trả `202` + id job, client hỏi trạng thái hoặc chờ có timeout.
- Upload: kiểm MIME thật + đuôi + dung lượng ở tầng api trước khi gọi use case.
- Không bao giờ trả về: mật khẩu băm, token băm, khóa API, đường dẫn file tuyệt đối trên máy chủ.
