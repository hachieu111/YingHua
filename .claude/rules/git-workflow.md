# Quy trình Git

- Nhánh chính: `main` (ổn định). Nhánh làm việc của thành viên: `hieu`, ... hoặc nhánh tính năng `feat/F07.01-save-word`, `fix/...`, `docs/...`.
- **Không commit, push, merge, rebase, reset, force-push khi người dùng chưa yêu cầu.** Không bao giờ force-push lên `main`.
- Commit nhỏ, một mục đích. Thông điệp theo Conventional Commits, mô tả tiếng Việt:
  `feat(vocab): lưu từ kèm ảnh ngữ cảnh (F07.01, US-NH-31)`
  Loại: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`.
- Không commit: `.env`, khóa, file dữ liệu lớn (model `.pt`, từ điển nặng, ảnh upload, `storage/`), `__pycache__`, `.venv`.
  Kiểm tra `git status` trước khi commit.
- Trước khi đề nghị commit: lint + test qua.
- Pull request: tiêu đề như commit; mô tả gồm mục tiêu, mã US/F, cách kiểm tra, ảnh chụp giao diện nếu có.
