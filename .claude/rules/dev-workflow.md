# Quy trình làm việc hằng ngày (người dùng chốt 24/10/2026)

## 1. Kiểm thử thủ công: một tài khoản cố định
- Mọi lần kiểm thử thủ công (trình duyệt, curl, gọi API vào server đang chạy trên `yinghua_db`) dùng **một tài khoản QA cố định**
  (vai trò `user`), cộng với tài khoản admin có sẵn khi cần quyền quản trị.
- Thông tin đăng nhập nằm trong `server/.env` (`DEV_TEST_EMAIL`, `DEV_TEST_PASSWORD`, `DEV_ADMIN_EMAIL`, `DEV_ADMIN_PASSWORD`).
  `.env` không commit; **không in mật khẩu ra chat, log hay tài liệu**.
- **Không xóa rồi tạo lại** tài khoản này, không đăng ký tài khoản mới cho mỗi lần thử. Dữ liệu tài khoản QA tạo ra (truyện, từ, thẻ...)
  được giữ lại để dùng cho các lần sau.
- Test tự động (`pytest`) vẫn chạy trên `yinghua_test`, tách biệt; không đụng tới tài khoản QA trên `yinghua_db`.

## 2. Giữ nguyên server đang chạy
- API (`uvicorn --reload`, cổng 8000) và giao diện (Vite, cổng 3000) **để chạy liên tục**; không tắt/khởi động lại sau mỗi lần sửa.
  `--reload`/HMR tự nạp code mới.
- Chỉ khởi động lại khi bắt buộc (đổi `.env`, cài thư viện, server treo) và báo người dùng khi làm vậy.
- Trước khi khởi động server, kiểm tra cổng đã có tiến trình nghe chưa; có rồi thì dùng lại, không mở bản thứ hai.

## 3. Tính năng trên giao diện mà hệ thống chưa có
- Mọi tính năng/nút trên giao diện React mà chưa có trong module nào → **thêm vào hệ thống** (CSDL, use case, API) chứ không bỏ hay ẩn.
- Đồng thời **cập nhật SRS cho đồng bộ**: thêm user story vào `docs/user-stories.md`, chức năng (mã F mới) vào
  `docs/modules-functions.md`, bảng vào `docs/database-design.md`, và mốc giai đoạn trong `docs/ke-hoach-trien-khai.md`.
  Code, tài liệu và giao diện phải khớp nhau; không để tính năng "chỉ có trên UI" hoặc "chỉ có trong code".

## 4. Được tự điều chỉnh giao diện, nhưng giữ phần lõi
- Claude được tự điều chỉnh, cải tiến giao diện cho hợp lý và sáng tạo (bố cục, luồng thao tác, trạng thái rỗng/đang tải/lỗi,
  component mới), không bắt buộc giữ nguyên từng chi tiết thiết kế cũ.
- **Phần lõi bắt buộc giữ theo người dùng**: bộ màu (màu chủ đạo `#a43073` và bảng màu hiện có), font chữ, logo 映画 YingHua.
- Không xóa tính năng (mục 3). Thêm thư viện frontend mới vẫn phải hỏi (`tech-stack.md`).
