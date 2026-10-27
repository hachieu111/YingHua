# YingHua (映画) — hướng dẫn cho Claude

Ứng dụng web học tiếng Trung qua truyện tranh: nhận diện chữ trên ảnh, Hover & Dịch, tra cứu đa chiều,
phân rã chữ Hán, sổ tay, flashcard SRS, TTS. Đề tài học phần Phát triển ứng dụng — ĐH Lạc Hồng.

- `server/` — **code mới** (FastAPI, Clean Architecture) theo `docs/ke-hoach-trien-khai.md`.
- `Backend/` — bản cũ, chỉ tham khảo, **không sửa**. Trên Windows `backend/` trùng với `Backend/` — không tạo thư mục tên `backend`.
- `module xử lí ảnh/` — pipeline YOLO → PaddleOCR → dịch VietPhrase → inpaint → render; thư mục từ điển rất lớn.
- `thuyet minh/` — thuyết minh đề tài (PDF), nguồn sự thật về phạm vi.

Luôn trả lời bằng tiếng Việt.

## Rules bắt buộc (đọc trước khi làm)

- **HỎI TRƯỚC KHI SỬA**: mọi việc tạo/sửa/xóa file, thêm thư viện, đổi kiến trúc/CSDL/API đều phải đề xuất và chờ người dùng đồng ý — xem `.claude/rules/change-control.md` (ưu tiên cao nhất).
- Trước mọi việc viết code hoặc đổi cấu hình: dùng skill `yinghua-guardrails` (`.claude/skills/yinghua-guardrails/SKILL.md`).
- Bộ rules trong `.claude/rules/`: `tech-stack` (FastAPI + PostgreSQL, không C#), `system-design` và `project-structure` (Modular Monolith + **Clean Architecture**), `clean-code`, `code-style`, `naming-conventions`, `api-conventions`, `database`, `error-handling`, `security`, `testing`, `git-workflow`, `monitoring`, `frontend-react` (Rules of React, React Router, bảo mật frontend theo OWASP), `dev-workflow` (một tài khoản QA cố định, giữ server chạy, tính năng UI thiếu → thêm vào hệ thống + cập nhật SRS, được chỉnh UI nhưng giữ màu/font/logo).
- Tài liệu nguồn của thiết kế: `docs/user-stories.md`, `docs/modules-functions.md`, `docs/danh-gia-luong-2-3.md`.

## Điều phối công việc cho subagent (tự động)

Người dùng cho phép Claude **tự giao việc** cho các subagent trong `.claude/agents/` mà không cần hỏi lại,
mỗi agent chạy model phù hợp với độ khó:

| Loại việc | Agent | Model |
|---|---|---|
| Tìm file/endpoint/bảng, trả lời "ở đâu, cái gì" — chỉ đọc | `yinghua-explorer` | haiku |
| Phân tích thiết kế: actor, use case, UML, ERD, kiến trúc, đối chiếu thuyết minh ↔ code | `yinghua-analyst` | opus |
| Sửa/thêm code Backend (FastAPI) | `yinghua-backend-dev` | sonnet |
| Module xử lý ảnh: YOLO, OCR, dịch, inpaint, đắp chữ | `yinghua-vision` | opus |
| Tích hợp giao diện React `frontend/frontend-YingHua/` | `yinghua-frontend-dev` | sonnet |
| Chạy test, kiểm tra hồi quy, kiểm tra API, lập bảng test case | `yinghua-tester` | haiku |
| Viết báo cáo, README, hướng dẫn, nội dung slide | `yinghua-doc-writer` | sonnet |

Nguyên tắc:
- Việc có sửa file: xin người dùng đồng ý **trước khi giao**; brief ghi rõ phạm vi đã duyệt và yêu cầu agent tuân thủ `.claude/rules/`.
- Việc nhỏ (vài lệnh, một chỗ sửa, câu hỏi ngắn) thì tự làm, không giao.
- Việc lớn có nhiều phần độc lập thì giao song song cho các agent tương ứng; phần nào phụ thuộc kết quả phần khác thì chạy tuần tự.
- Khi giao việc, brief phải đủ ngữ cảnh (file liên quan, mục tiêu, tiêu chí hoàn thành) vì agent bắt đầu từ đầu.
- Phân công theo model: Opus (phiên chính) ra quyết định, thiết kế, rà kết quả; Sonnet viết code (kèm test của phần mình viết); Haiku làm việc lặp lại (chạy test, kiểm tra hồi quy, tìm kiếm).
- Sau khi agent sửa code, giao `yinghua-tester` (Haiku) chạy lại toàn bộ kiểm tra trước khi báo hoàn thành.
- Kết quả của agent chỉ là báo cáo — kiểm tra diff/file trước khi khẳng định với người dùng.
