# Bảo mật

## Bí mật & cấu hình
- Bí mật (`JWT_SECRET`, `DATABASE_URL`, `LLM_API_KEY`...) chỉ ở biến môi trường / `.env`. `.env` **không commit**; chỉ commit `.env.example` với giá trị giả.
- Không in, log, hay dán nội dung `.env` hoặc token vào chat/tài liệu.

## Xác thực
- Mật khẩu băm **Argon2id**; tối thiểu 8 ký tự. Không bao giờ lưu/log mật khẩu thô.
- Access token JWT 15 phút; refresh token ngẫu nhiên 30 ngày, **xoay vòng**, CSDL chỉ lưu SHA-256. Token cũ bị dùng lại → thu hồi cả phiên.
- Đổi mật khẩu / "đăng xuất mọi thiết bị" → thu hồi mọi refresh token.
- Đăng nhập sai: thông báo chung ("Email hoặc mật khẩu không đúng"), giới hạn số lần thử (rate limit).
- Liên kết đặt lại mật khẩu dùng một lần, hết hạn 30 phút.

## Phân quyền
- Kiểm tra quyền ở **application** (use case nhận `current_user`), không chỉ ở router.
- Vai trò: `user`, `admin`. Admin kế thừa quyền user. Admin không tự hạ quyền / tự khóa mình.
- Dữ liệu cá nhân (sổ tay, thẻ, bài kiểm tra, cài đặt) chỉ chủ sở hữu truy cập. Người dùng thường truy cập tài nguyên người khác → `404`.
- **Quản trị viên xem và sửa được toàn bộ dữ liệu** của mọi người dùng (sổ tay, ngữ cảnh, ảnh, thẻ ôn, lịch sử ôn, cài đặt,
  tiến độ đọc, truyện riêng tư…) qua API quản trị `/api/v1/admin/users/{user_id}/...` (F13.07; người dùng chốt 24/10/2026).
  Mọi thao tác sửa/xóa của admin trên dữ liệu người khác ghi nhật ký quản trị (F13.06). API của người dùng thường vẫn lọc theo `user_id` của chính họ.
- Truyện riêng tư chỉ chủ sở hữu và admin xem; chỉ admin đăng truyện công khai.

## Dữ liệu đầu vào
- Validate mọi input bằng Pydantic (độ dài, khoảng giá trị).
- Upload: kiểm MIME thật bằng đọc header file, chỉ jpg/png/webp, ≤ 10 MB, đặt tên file ngẫu nhiên, lưu ngoài thư mục web tĩnh; không dùng tên file của người dùng làm đường dẫn (chống path traversal).
- Không ghép chuỗi vào SQL, lệnh shell, hay đường dẫn.
- Frontend không dùng `innerHTML` với dữ liệu người dùng (chống XSS).

## Dịch vụ ngoài
- Gửi cho LLM **chỉ** từ, pinyin, nghĩa, cấp HSK của từ và trình độ HSK của người học dạng một con số
  (người dùng chốt 25/10/2026), cùng dữ liệu từ điển công khai của từ đó (phân rã chữ Hán: bộ thủ, thành phần, âm Hán Việt)
  để LLM dựa vào dữ liệu thật thay vì tự bịa — không email, tên, id người dùng, ghi chú, câu thoại đã lưu hay dữ liệu nào
  định danh được người học.
- Không tin dữ liệu LLM trả về: validate schema, đối chiếu từ điển, escape khi hiển thị.
- Giới hạn số đề LLM mỗi người mỗi ngày.

## Hạ tầng
- CORS chỉ cho origin của frontend (không `*` khi có cookie/credential).
- Header bảo mật cơ bản; HTTPS khi triển khai.
- Phụ thuộc ghim phiên bản; không cài gói từ nguồn lạ.
