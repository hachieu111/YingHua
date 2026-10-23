# Kiểm thử

- Công cụ: **pytest**, pytest-asyncio, httpx `AsyncClient`.
- **Unit test** cho domain và use case, dùng fake repository/gateway (không cần DB, mạng). Mỗi use case mới phải có test.
- **Integration test** cho repository với PostgreSQL thật (CSDL test riêng, tạo bằng migration).
- **API test** cho luồng chính: đăng ký/đăng nhập, lưu từ, chấm thẻ, tạo và nộp bài kiểm tra, phân quyền (403/404).
- Test đặt tên theo hành vi: `test_save_word_twice_adds_context_instead_of_duplicate`.
- Tiêu chí chấp nhận trong `docs/user-stories.md` là nguồn test case; ghi mã US trong docstring test.
- Dịch vụ ngoài (LLM, TTS) **luôn mock** trong test; không gọi dịch vụ trả phí khi chạy test.
- Thời gian dùng `Clock` giả để test FSRS/hạn lưu file.
- Trước khi báo "xong": `ruff check`, `mypy`, `pytest` phải qua. Test lỗi thì báo nguyên văn, không giấu, không xóa/skip test để cho qua.
- Mục tiêu độ phủ: domain + application ≥ 80%.
