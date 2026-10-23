# Xử lý lỗi

## Phân loại
- **Lỗi nghiệp vụ** (domain/application): lớp con của `DomainError` có `code` cố định và thông điệp tiếng Việt.
  Vd. `WordAlreadySavedError`, `NotEnoughWordsForQuizError`, `PermissionDeniedError`, `NotFoundError`.
- **Lỗi hạ tầng** (DB, file, dịch vụ ngoài): bắt ở infrastructure, chuyển thành lỗi của port
  (vd. `TtsUnavailableError`, `QuizGeneratorError`) — không để lộ exception của thư viện lên application.
- **Lỗi không lường trước**: để exception handler toàn cục bắt, trả `500` thông báo chung, log đầy đủ kèm `request_id`.

## Ánh xạ sang HTTP
Một exception handler duy nhất ở tầng api ánh xạ `DomainError.code` → mã HTTP theo `api-conventions.md`. Router không tự `try/except` để dựng response lỗi.

## Dịch vụ ngoài
- Mọi lời gọi ra ngoài có **timeout** (LLM 20 s, TTS 10 s) và số lần thử lại giới hạn (tối đa 1 lần, có backoff).
- Có **phương án dự phòng** theo user story: LLM lỗi → đề dự phòng (F09.07); TTS lỗi → báo người học, trang vẫn dùng được.
- Job xử lý ảnh lỗi → trạng thái `failed` + lý do đọc được; cho phép chạy lại (F04, US-QT-07).

## Cấm
- `except Exception: pass` hoặc nuốt lỗi không log.
- Trả stack trace, câu SQL, đường dẫn máy chủ cho client.
- Dùng exception cho luồng điều khiển bình thường.
