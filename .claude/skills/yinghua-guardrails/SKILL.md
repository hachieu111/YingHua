---
name: yinghua-guardrails
description: Bắt buộc dùng trước MỌI việc tạo/sửa/xóa file, viết code, đổi cấu hình, thêm thư viện, đổi schema CSDL hay API trong dự án YingHua. Kiểm tra yêu cầu với bộ rules (.claude/rules — bảo mật, Clean Architecture, công nghệ FastAPI/PostgreSQL, CSDL, API, đặt tên, test, git), đề xuất thay đổi và HỎI người dùng trước khi sửa, rồi tự rà soát sau khi làm.
---

# YingHua Guardrails

Quy trình bắt buộc để không làm vượt phạm vi, không dùng sai công nghệ, không phá kiến trúc.

## Bước 0 — Nạp rules liên quan
Đọc `.claude/rules/change-control.md` (luôn luôn), rồi các rule theo loại việc:

| Loại việc | Rule cần đọc |
|---|---|
| Bất kỳ code nào | `tech-stack.md`, `project-structure.md`, `system-design.md`, `clean-code.md`, `code-style.md`, `naming-conventions.md` |
| Endpoint / router | + `api-conventions.md`, `error-handling.md`, `security.md` |
| Bảng, migration, repository | + `database.md` |
| Đăng nhập, quyền, upload, dịch vụ ngoài | + `security.md`, `error-handling.md` |
| Test | + `testing.md` |
| Log, job nền | + `monitoring.md` |
| Commit / PR | + `git-workflow.md` |

## Bước 1 — Đối chiếu yêu cầu
- Gắn yêu cầu với mã chức năng/user story trong `docs/modules-functions.md` và `docs/user-stories.md`. Không có → đây là tính năng mới, phải nói rõ.
- Liệt kê rule mà yêu cầu có thể vi phạm (công nghệ ngoài danh sách, sai tầng, SQL thô trong use case, bỏ kiểm tra quyền...).

## Bước 2 — Đề xuất và HỎI (trừ khi yêu cầu đã nêu cụ thể đúng phạm vi đó)
Dùng mẫu trong `change-control.md` §3. Dừng lại chờ người dùng đồng ý. Nếu vi phạm rule: nêu rule, hậu quả, phương án đúng — người dùng quyết định.

## Bước 3 — Thực hiện trong phạm vi đã duyệt
- Đúng tầng: domain thuần → application (use case + port) → infrastructure (hiện thực) → api (router mỏng).
- Phát sinh việc ngoài phạm vi → dừng, báo lại, hỏi tiếp.
- Giao subagent: brief ghi rõ phạm vi đã duyệt + yêu cầu tuân thủ `.claude/rules/`.

## Bước 4 — Tự rà soát trước khi báo xong
- [ ] Domain không import FastAPI/SQLAlchemy/Pydantic; router không truy vấn DB; không có vòng phụ thuộc module.
- [ ] Chỉ dùng công nghệ trong `tech-stack.md`; phiên bản đã ghim.
- [ ] Truy vấn dữ liệu cá nhân lọc theo `user_id`; kiểm tra quyền ở use case.
- [ ] Không có bí mật trong code/log; input được validate; upload kiểm MIME + dung lượng.
- [ ] Thao tác nhiều bước nằm trong một giao dịch; đổi schema có migration Alembic mới.
- [ ] Lỗi theo dạng chuẩn; dịch vụ ngoài có timeout + dự phòng.
- [ ] Có test cho use case mới; `ruff check`, `mypy`, `pytest` đã chạy — báo đúng kết quả.
- [ ] Chỉ các file đã được duyệt bị thay đổi (`git status` / `git diff --stat`).

Báo cáo cuối: file đã đổi, rule đã kiểm, kết quả lint/test, việc chưa làm hoặc chưa kiểm được.
