# Clean Code

## Nguyên tắc
- **SOLID**, đặc biệt: một lớp/hàm một trách nhiệm; phụ thuộc vào interface (port), không phụ thuộc vào hiện thực.
- **DRY có chừng mực**: chỉ gom khi lặp ≥ 3 lần và cùng ý nghĩa nghiệp vụ.
- **YAGNI**: không viết trước cho tính năng chưa có user story.
- Hàm ≤ ~40 dòng, ≤ 4 tham số (nhiều hơn → gom vào dataclass/DTO), độ lồng ≤ 3 cấp (dùng return sớm).
- File ≤ ~300 dòng; vượt thì tách theo trách nhiệm.

## Viết code
- Không có "số ma thuật": giới hạn nghiệp vụ (10 MB, 10 câu/đề, 7 ngày lưu ảnh, timeout LLM 20 s...) để trong `Settings` hoặc hằng số có tên ở domain.
- Không bắt lỗi rồi bỏ qua (`except: pass`).
- Không dùng biến toàn cục có trạng thái; singleton duy nhất được phép là model AI nặng trong worker (qua adapter).
- Hàm thuần ở domain: không đọc thời gian hệ thống trực tiếp — nhận `now` hoặc `Clock` port để test được.
- Comment giải thích **vì sao**, không giải thích **làm gì**. Docstring cho use case và hàm công khai.
- Không để code chết, code comment-out, `print` debug khi hoàn thành.
- TODO phải kèm lý do và mã US/F: `# TODO(F09.07): bù câu dự phòng khi LLM thiếu câu`.
