# Quy ước đặt tên

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Module/package, file Python | `snake_case` | `use_cases/save_word.py` |
| Lớp | `PascalCase` | `VocabEntry`, `SaveWordUseCase` |
| Hàm, biến | `snake_case`, hàm bắt đầu bằng động từ | `grade_card()`, `due_cards` |
| Hằng số | `UPPER_SNAKE_CASE` | `MAX_UPLOAD_MB` |
| Port (interface) | `<Tên>Repository`, `<Tên>Gateway`, `<Tên>Port` | `VocabRepository`, `TtsGateway` |
| Hiện thực port | `<Công nghệ><Port>` | `SqlVocabRepository`, `EdgeTtsGateway` |
| Use case | `<ĐộngTừ><DanhTừ>UseCase` | `GenerateQuizUseCase` |
| Schema API | `<Tên>Request`, `<Tên>Response` | `SaveWordRequest` |
| Lỗi nghiệp vụ | `<Tên>Error` | `WordAlreadySavedError` |
| Bảng CSDL | `snake_case`, số nhiều | `vocab_entries`, `review_logs` |
| Cột khóa ngoại | `<bảng_số_ít>_id` | `user_id`, `card_id` |
| Cột thời gian | `<động_từ>_at` (UTC, timestamptz) | `created_at`, `due_at` |
| Endpoint | danh từ số nhiều, `kebab-case` | `/api/v1/vocab-entries` |
| Migration Alembic | `<số>_<mô_tả>` | `0005_add_quiz_tables` |
| Nhánh git | `<loại>/<mã>-<mô-tả>` | `feat/F07.01-save-word` |
| Biến môi trường | `UPPER_SNAKE_CASE` | `DATABASE_URL`, `LLM_API_KEY` |

Thuật ngữ nghiệp vụ thống nhất (tiếng Anh trong code ↔ tiếng Việt trong UI): vocab entry ↔ mục từ sổ tay · context ↔ ngữ cảnh · card ↔ thẻ · review log ↔ lượt ôn · quiz ↔ bài kiểm tra · bubble ↔ bong bóng · series/chapter/page ↔ truyện/chương/trang.
