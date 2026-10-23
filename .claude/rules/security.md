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
- Dữ liệu cá nhân (sổ tay, thẻ, bài kiểm tra, cài đặt) chỉ chủ sở hữu truy cập. Truy cập tài nguyên người khác → `404`.
- Truyện riêng tư chỉ chủ sở hữu và admin xem; chỉ admin đăng truyện công khai.

## Dữ liệu đầu vào
- Validate mọi input bằng Pydantic (độ dài, khoảng giá trị).
- Upload: kiểm MIME thật bằng đọc header file, chỉ jpg/png/webp, ≤ 10 MB, đặt tên file ngẫu nhiên, lưu ngoài thư mục web tĩnh; không dùng tên file của người dùng làm đường dẫn (chống path traversal).
- Không ghép chuỗi vào SQL, lệnh shell, hay đường dẫn.
- Frontend không dùng `innerHTML` với dữ liệu người dùng (chống XSS).

## Dịch vụ ngoài
- Gửi cho LLM **chỉ** từ, pinyin, nghĩa — không email, tên, id người dùng.
- Không tin dữ liệu LLM trả về: validate schema, đối chiếu từ điển, escape khi hiển thị.
- Giới hạn số đề LLM mỗi người mỗi ngày.

## Hạ tầng
- CORS chỉ cho origin của frontend (không `*` khi có cookie/credential).
- Header bảo mật cơ bản; HTTPS khi triển khai.
- Phụ thuộc ghim phiên bản; không cài gói từ nguồn lạ.
