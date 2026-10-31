# Kế hoạch triển khai YingHua

> Căn cứ: `docs/modules-functions.md` (17 module, 153 chức năng; cập nhật 31/10/2026 với F02.05, F02.06), `docs/user-stories.md` (146 user story), `.claude/rules/*`, skill `yinghua-guardrails`.
> Trạng thái (24/10/2026): GĐ0, GĐ0.5, GĐ1 **xong**. **GĐ2 (M06 Từ điển) xong**: migration 0003–0004, nạp CVDICT/HSK/Tatoeba/Thiên Chửu/tu tiên, 180 test (Haiku kiểm độc lập), giao diện Navbar/Catalog/khung tra từ đã nối. **GĐ3 (M03 Thư viện, M04 Xử lý ảnh + worker, M05 Đọc truyện, M15 Tác vụ nền) xong (24/10/2026)**: migration 0005, 304 test qua, worker dịch ảnh chạy thật (YOLO → OCR → dịch → xóa chữ → đắp chữ), giao diện Catalog/Thư viện/Upload/Đọc truyện đã nối; còn mở: chống ảnh trùng theo pHash, giới hạn Khách theo IP, một số luật LuatNhan. **GĐ4 (M07 Sổ tay, M08 Ôn tập FSRS, M11 Phát âm) xong (24/10/2026)**: migration 0006, lưu từ kèm ảnh ngữ cảnh + 3 thẻ trong một giao dịch, ôn thẻ FSRS 4 mức (chống bấm đúp), Edge TTS có cache và dự phòng Web Speech; bổ sung F07.09 (đánh dấu sao), F07.10 (âm Hán Việt), F08.10 (bộ thẻ theo truyện) và F13.07 (admin xem/sửa toàn bộ dữ liệu người dùng, có nhật ký; US-QT-14) theo quyết định 24/10/2026; 408 test qua; giao diện Flashcard/Sổ tay/phát âm/trang quản trị đã nối. Việc còn mở: `docs/ton-dong-gd3.md` (mục GĐ3 và GĐ4). **GĐ5 xong (25/10/2026)**: migration 0007–0008, M09 Kiểm tra (đề AI Gemini + đề dự phòng, câu ví dụ có lọc độ khó, 15% từ mở rộng), M10 Gợi ý (từ trong chương, gợi ý truyện, độ phủ), thêm F07.11, F07.12, F08.11, F02.04, xóa avatar, danh sách giọng; 554 test qua; giao diện bài kiểm tra/gợi ý/câu thoại/Flashcard AI/cài đặt học tập/trang quản trị xử lý ảnh–tác vụ nền đã nối; LLM: Google Gemini (chọn 25/10/2026). Việc còn mở: `docs/ton-dong-gd3.md` (mục GĐ5). **GĐ6 đang làm (25/10/2026): phần backend đã xong, giao diện đang nối.** Migration 0009–0010. Đã xong: nhóm A1 (M12 thống kê và chuỗi ngày F12.01–F12.03; báo lỗi F14.01–F14.02; thông báo F14.05 và hộp thông báo F14.06, bổ sung US-NH-82; nhắc ôn F14.03–F14.04; xuất sổ tay F07.08; job tối ưu FSRS F08.08 và job nhắc ôn trong worker); nhóm A2 (cấu hình hệ thống F13.05 với 11 khóa và `GET /system/status`, kiểm duyệt F13.04, nhật ký quản trị, trang mẫu F04.16, ghi nhớ đăng nhập F01.11, ảnh đại diện có sẵn F01.10, chế độ bảo trì); nhóm AI (F05.09 phân tích ngữ pháp, F09.10 "Vì sao sai?"); F12.04 "Hôm nay nên học gì" (không gọi LLM). Hạn mức mọi tính năng AI đọc từ cấu hình hệ thống (F13.05), admin đổi có hiệu lực ngay. **Tối ưu xử lý ảnh (30/10/2026):** đo thời gian từng bước pipeline; sửa bước dịch tra từ điển (bớt ~2,5 s/trang, ~8 s → ~5,5 s); lưu bong bóng ngay sau giai đoạn chữ để chế độ Học mở trước khi xong ảnh dịch (F04.01, F04.02, F05.01); giới hạn 20 ảnh mỗi lượt tải (F03.07). **Chọn nguồn đọc trong trình đọc (F05.10, US-NH-83; 30/10/2026):** chỉ thay đổi giao diện, dùng API sẵn có, không thêm bảng hay migration. **Việc treo của GĐ6:** (1) OCR khi tải lên (`ocr_on_upload_enabled`) đã lưu được nhưng chưa có tác dụng, chờ duyệt vì cần trạng thái bản dịch mới và migration; (2) công tắc `admin_notifications_enabled` chỉ lưu, vì chưa có loại thông báo nào gửi cho quản trị viên; (3) F13.08, F13.09 và M18 thuộc GĐ6.6. **GĐ6.5 (M16 Gamification, M17 VIP & Phần thưởng) xong (31/10/2026)**: 21 chức năng mới, 20 user story mới, 12 bảng, migration 0012–0013; 816 test qua, 2 bỏ qua; giao diện bảng xếp hạng, mùa thi đua, nhiệm vụ, huy hiệu, ví, cửa hàng `/cua-hang`, mini-game `/mini-game-bo-thu`, truyện VIP và trang quản trị đã nối. **Tiếp theo: GĐ6.6.**

## 1. Hiện trạng (rà soát ngày 23/10/2026)

| Thành phần | Tình trạng | Quyết định |
|---|---|---|
| `Backend/` (FastAPI, ~5.200 dòng) | Chạy được; cấu trúc `routers/ + services/` (không Clean Architecture); SQLAlchemy **sync** + psycopg2; bcrypt; **SM-2**; chưa có test đơn vị; chưa có Alembic | **Không mở rộng.** Dùng làm nguồn tham khảo, chuyển logic tốt sang cấu trúc mới (bảng dưới). Xong giai đoạn 8 thì chuyển vào `legacy/` (hỏi trước). |
| `Backend/db/schema.sql` (24 bảng) | Thiết kế bảng khá đầy đủ (truyện, trang, bong bóng, sổ tay, thẻ, từ điển, tu tiên, TTS cache) | Làm **cơ sở** cho ORM + migration Alembic đầu tiên, chỉnh tên theo `naming-conventions.md`, thêm bảng còn thiếu (HSK, quiz, job, báo lỗi, thông báo, nhật ký quản trị, đặt lại mật khẩu). |
| CSDL `ptud_db` (PostgreSQL 16 đang chạy) | Đã nạp: 12.139 mục từ, 9.574 chữ Hán, 1.018.937 mục tu tiên, 118 luật nhân | Giữ nguyên làm nguồn; tạo CSDL mới `yinghua_db` và **chép dữ liệu từ điển** sang bằng script (không nạp lại từ file). |
| `module xử lí ảnh/` (YOLO, PaddleOCR, inpaint, render, ~3.000 dòng) | Hoạt động; `Backend/app/services/pipeline_runner.py` đã bọc được | Giữ nguyên module; worker mới gọi qua adapter (chuyển từ `pipeline_runner.py`). |
| `Backend/ui/` (JS thuần, ~1.500 dòng) | Màn đọc, thư viện, học, cá nhân | Chuyển dần sang `frontend/`, gọi `/api/v1`. |
| Môi trường | **Python 3.10.11**; đã có fastapi, SQLAlchemy 2.0.45, alembic 1.12, pydantic 2, PyJWT, edge-tts, jieba, paddle, ultralytics | **Thiếu**: asyncpg, argon2-cffi, fsrs, pytest, pytest-asyncio, ruff, mypy. **Chưa có danh sách HSK 3.0** trong repo. |

### Logic tái sử dụng từ `Backend/`

| Nguồn cũ | Chuyển sang |
|---|---|
| `security.py` (JWT, refresh token xoay vòng, thu hồi cả family) | `core/security.py` + `modules/auth/` (đổi bcrypt → Argon2id, vẫn đọc được hash bcrypt cũ khi chép user) |
| `services/dictionary.py`, `scripts/import_dictionaries.py` | `modules/dictionary/infrastructure/` + `server/scripts/` |
| `services/pipeline_runner.py` | `worker/pipeline_adapter.py` (M04) |
| `services/tts.py` | `modules/tts/infrastructure/edge_tts_gateway.py` |
| `services/suggestions.py` (công thức xếp hạng) | `modules/suggestions/domain/` |
| `services/library.py` (sha256 + pHash chống trùng) | `modules/library/` + `modules/imaging/` |
| `services/srs.py` (SM-2) | **Bỏ**, thay bằng FSRS |

## 2. Cách làm

- **Mỗi giai đoạn là một lát cắt dọc** (CSDL → domain → use case → API → giao diện → test) và **dùng thử được** khi kết thúc.
- **Đầu mỗi giai đoạn**: tôi gửi đề xuất chi tiết (file, bảng, endpoint) theo mẫu `change-control.md`. Bạn duyệt xong mới làm.
- **Cuối mỗi giai đoạn**: chạy `ruff`, `mypy`, `pytest`, demo, rồi báo kết quả thật. Chỉ commit khi bạn yêu cầu.
- **Giao việc** theo `CLAUDE.md`:
  - Giai đoạn 0 tôi tự làm, vì đây là phần dựng khung mẫu.
  - Các module sau giao cho `yinghua-backend-dev` (sonnet).
  - Worker xử lý ảnh giao cho `yinghua-vision` (opus).
  - Giao diện giao cho `yinghua-frontend-dev` (sonnet).
  - Kiểm thử giao cho `yinghua-tester` (haiku).
  - Tôi rà diff của mọi agent trước khi báo bạn.

## 3. Các giai đoạn

| GĐ | Nội dung | Chức năng | Kết quả dùng thử được |
|---|---|---|---|
| **0** | **Nền tảng.** Khung `server/` theo `project-structure.md`. `core/` gồm: config, CSDL async + Unit of Work, lỗi chuẩn, logging + request_id, security. Alembic, cấu hình pytest/ruff/mypy, `GET /api/v1/health`. Cài thư viện còn thiếu. Tạo `yinghua_db`. | — | Server chạy, health OK, test mẫu qua. |
| **0.5** | **Thiết kế CSDL** cho cả 16 module (M16 Gamification bổ sung 25/10/2026): `docs/database-design.md`. Bảng được tạo dần theo từng giai đoạn, đúng thiết kế đã duyệt. | — | Thiết kế được duyệt. |
| **1** | **Tài khoản & quyền.** M01 (trừ quên mật khẩu qua email thật: dùng adapter "hộp thư giả" ghi ra file), M02, phần người dùng của M13. | F01.01–09, F02.01–03, F13.01–03, F13.06 | Đăng ký, đăng nhập, làm mới phiên, đổi mật khẩu, cài đặt HSK/giọng, admin khóa/đổi vai trò. |
| **2** | **Từ điển.** M06. Script chép dữ liệu từ `ptud_db`. Nạp danh sách HSK. Xác định cấp HSK (F06.08). | F06.01–08 | Tra từ, tìm kiếm, tu tiên, tách câu, phân rã chữ Hán. |
| **3** | **Thư viện, xử lý ảnh, đọc truyện.** M03, M04 (hàng đợi bằng bảng job + worker riêng + adapter pipeline), M05, M15 (dọn file hết hạn, dọn phiên). | F03.* (gồm F03.13 thư viện/yêu thích, F03.14 chấm sao), F04.*, F05.* (gồm F05.07 lưu trang, F05.08 ghi chú), F15.*, F01.10 (avatar) | Tải ảnh lên, worker nhận diện và dịch, đọc 3 dạng, Hover & Dịch, sửa bản dịch. |
| **4** | **Sổ tay, Ôn tập, Phát âm.** M07, M08 (FSRS, 3 loại thẻ), M11 (Edge TTS + cache). | F07.01–07, F07.09, F07.10, F08.01–07, F08.09, F08.10, F11.*, **F13.07** (bổ sung theo yêu cầu người dùng 24/10/2026: admin xem/sửa dữ liệu học tập của người dùng, làm sau khi M07, M08 có) | Lưu từ kèm ảnh ngữ cảnh, ôn thẻ 4 mức, nghe phát âm; admin xem và sửa sổ tay, thẻ, cài đặt của người dùng. |
| **5** | **Kiểm tra & Gợi ý.** M09: làm **đề dự phòng trước**, sau đó thêm adapter LLM. M10. | F09.* (gồm **F09.09** câu hỏi từ mở rộng, bổ sung 25/10/2026), F10.* (gồm **F10.04** gợi ý truyện theo trình độ, **F10.05** độ phủ từ vựng của chương), **F07.11** lưu câu thoại, **F07.12** lưu tất cả từ của trang, **F08.11** Flashcard AI, **F02.04** cỡ chữ bong bóng dịch (bổ sung 25/10/2026; thêm bảng `saved_sentences`, `vocab_ai_notes` và cột `user_settings.bubble_font_scale`); nối giao diện: tải avatar (F01.10), xóa ảnh tải nhanh và sửa/xóa truyện, chương (F03.09), cài đặt người học (F02.01–F02.03), giám sát xử lý ảnh (F04.05), tác vụ nền (F15.03) | Tạo đề (mỗi câu có câu ví dụ, 15% từ mở rộng), nộp bài, chấm ở máy chủ, từ sai về ôn sớm. Gợi ý từ theo chương, gợi ý truyện và độ phủ từ vựng. Lưu câu thoại, lưu cả trang, Flashcard AI (Gemini, có dự phòng khi LLM lỗi). |
| **6** | **Thống kê, Quản trị, Thông báo.** M12, phần còn lại của M13 (kiểm duyệt, cấu hình LLM/TTS), M14. Xuất sổ tay (F07.08). Tối ưu FSRS (F08.08). | F12.*, F13.04–05 (F13.05 mở rộng: chế độ bảo trì, kiểm duyệt ảnh tự động, OCR khi tải, thông báo quản trị), F14.* (gồm **F14.06** hộp thông báo trong ứng dụng, bổ sung 25/10/2026; cột `notifications.data`), F07.08, F08.08, **F01.11** ghi nhớ đăng nhập, **F04.16** thử với trang mẫu; mở rộng F01.10 (chọn avatar có sẵn, thêm cột `users.avatar_preset`). **Nhóm AI (bổ sung 25/10/2026, theo thứ tự ưu tiên):** (1) **F05.09** phân tích ngữ pháp câu thoại (bảng `grammar_analyses`, `grammar_requests`), (2) **F09.10** giải thích lỗi sai và câu luyện thêm trong kết quả kiểm tra (cột `quiz_questions.mistake_review`, `mistake_review_at`), (3) **F12.04** trang chủ "Hôm nay nên học gì" (không thêm bảng). Cả ba theo nguyên tắc "AI chỉ sinh dữ liệu theo lược đồ cố định, máy chủ kiểm tra, giao diện hiển thị bằng component viết sẵn", gọi Gemini qua REST bằng `httpx`, có cache, hạn mức và phương án dự phòng. | Bảng thống kê, báo lỗi, nhắc ôn, xuất CSV/Anki. Ghi nhớ đăng nhập, trang mẫu, chọn avatar có sẵn, công tắc hệ thống. Phân tích ngữ pháp câu thoại, "Vì sao sai?" ở kết quả kiểm tra, trang chủ gợi ý việc học hôm nay. |
| **6.5** | **M16 Gamification** và **M17 VIP & Phần thưởng**. **Đã viết user story + đặc tả (30/10/2026), chờ người dùng duyệt trước khi làm.** Quyết định của người dùng: không thanh toán tiền thật (VIP, xu chỉ kiếm bằng học tập); quyền lợi VIP = hạn mức AI cao hơn, khung/dấu VIP, truyện VIP; mùa theo tuần giờ Việt Nam; bảng xếp hạng không hiện email, cho phép ẩn. Migration **0012** (`xp_events`, `seasons`, `season_results`, `achievements` + 7 dòng khởi tạo, `user_achievements`, `minigame_sessions`, cột `user_settings.show_on_leaderboard`) và **0013** (`wallets`, `wallet_ledger`, `vip_unlocks`, `avatar_frames` + 5 khung, `user_frames`, `reward_items` + 5 món, `reward_redemptions`, cột `series.is_vip`). Không thêm thư viện, dịch vụ ngoài hay Redis. **Chia ba đợt:** **Đợt 1 (nền, tuần tự):** migration 0012–0013; port `LearningEventPort` ở `core/` và móc vào use case đọc trang, chấm thẻ, lưu từ, nộp bài (F16.02); sổ phần thưởng và ví (F17.01); trạng thái VIP, quà chào mừng (F17.03); xem XP (F16.03). **Đợt 2 (hai nhánh song song, cùng phụ thuộc đợt 1):** nhánh M16: F16.04 nhiệm vụ ngày, F16.05 mục tiêu tuần, F16.06 mốc chuỗi, F16.07 bảng xếp hạng, F16.08 ẩn danh, F16.09 mùa, F16.11 huy hiệu, F16.12 đeo huy hiệu, F16.01 mini-game; nhánh M17: F17.02 ví, F17.04 hạn mức AI theo VIP (đổi chữ ký port `AiPolicy`, sửa F08.11, F13.05), F17.05 đọc truyện VIP (port `VipAccessPort` của M03, quy tắc xem tệp F03.10), F17.06 vé, F17.07 cửa hàng, F17.08 khung, F17.09, F17.10 quản trị. **Đợt 3 (tích hợp):** F16.10 chốt mùa và trao thưởng (cần F16.11 và F17.01), tác vụ nền `finalize_seasons`, `evaluate_achievements`, `remind_vip_expiry` (F15.03); nối giao diện; kiểm thử hồi quy toàn bộ. | F16.01 (bổ sung 25/10/2026); **F16.02–F16.12, F17.01–F17.10** (bổ sung 30/10/2026; US-NH-84 … US-NH-99, US-QT-17, US-QT-18, US-HG-05, US-HG-06); sửa F08.11, F13.05 | Bảng xếp hạng 4 chỉ số × 3 khoảng, mùa thi đua có đếm ngược và tự trao thưởng, nhiệm vụ ngày, mục tiêu tuần, huy hiệu, ví xu, VIP, truyện VIP, cửa hàng đổi thưởng, khung avatar chạy bằng dữ liệu thật; chơi mini-game luyện bộ thủ yếu. |
| **6.6** | **M18 Nội dung cộng đồng** (gửi bài, hàng chờ duyệt, duyệt tác giả), **M19 OAuth** (Google/WeChat/Apple), đổi email. Viết user story + đặc tả, trình duyệt trước khi làm. Đã có SRS: **F13.08** trang nội dung pháp lý, **F13.09** xuất báo cáo vi phạm; M18 còn có "duyệt nhanh tự động" (sắp xếp hàng chờ bằng luật, quản trị viên vẫn quyết định; viết mã F khi làm M18). | F13.08, F13.09 (bổ sung) | Mọi nút trên giao diện đều có chức năng thật. |

> **Nguyên tắc (23/10/2026): không xóa giao diện nào.** Mọi tính năng trên giao diện React đều được làm, theo bảng ở `docs/database-design.md` §8; tính năng ngoài SRS được thêm vào đúng giai đoạn của module liên quan.
| **7** | **Hoàn thiện tích hợp giao diện.** Đọc thử cho Khách (F03.01, F03.03, F05.04), rà toàn bộ luồng trên giao diện React. | F03.01, F03.03, F05.04 | Chạy được toàn bộ luồng trên trình duyệt và điện thoại. |
| **8** | **Hoàn thiện.** Test E2E theo tiêu chí chấp nhận, rà bảo mật (`/security-review`), tài liệu cài đặt và API, chuyển `Backend/` cũ vào `legacy/` (hỏi trước). | — | Bản nộp đồ án. |

**Quy trình (`.claude/rules/dev-workflow.md`, 24/10/2026):** Claude được tự điều chỉnh giao diện nhưng giữ bộ màu, font, logo; tính năng có trên giao diện mà thiếu trong hệ thống thì thêm vào code và SRS cho đồng bộ; kiểm thử thủ công dùng một tài khoản QA cố định và giữ server chạy liên tục.

Thứ tự phụ thuộc: 0 → 0.5 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.

**Luồng giao diện (chạy song song).** Giao diện là React của người dùng ở `frontend/frontend-YingHua/`. Claude không thiết kế lại, chỉ tích hợp: thêm lớp gọi API (`src/api/`), thay dữ liệu giả (mock) bằng dữ liệu thật, và bỏ qua phần Express/Gemini. Mỗi giai đoạn backend xong thì tích hợp ngay các màn hình liên quan:

| GĐ backend | Màn hình React tích hợp |
|---|---|
| 1 | Đăng nhập / đăng ký, hồ sơ, cài đặt tài khoản, admin quản lý người dùng |
| 2 | Popup tra từ, phân rã chữ |
| 3 | Catalog, Thư viện, Upload, Đọc truyện (bong bóng, sửa dịch, ghi chú) |
| 4 | Flashcard, phát âm |
| 5 | Bài kiểm tra, gợi ý từ |
| 6 | Hồ sơ (thống kê, chuỗi ngày), Admin (khiếu nại, cài đặt), thông báo; khối "Cấu trúc trọng điểm" trên trình đọc (F05.09), nút "Vì sao sai?" ở kết quả kiểm tra (F09.10), khối "Hôm nay nên học gì" ở trang chủ (F12.04); chọn nguồn đọc trong trình đọc (F05.10, US-NH-83) |
| 6.5 | Mini-game luyện bộ thủ yếu (F16.01); Bảng xếp hạng (`LeaderboardPage`: mùa, đếm ngược, bục, danh sách, bộ lọc, phần thưởng mùa, nhiệm vụ kiếm EXP, hoạt động tuần); viên "+n XP" ở `Navbar`, `CatalogPage`; Hồ sơ (tab Huy hiệu, huy hiệu đang đeo, "Hạn VIP", Mục tiêu tuần); `EditProfileModal` (chọn huy hiệu, khung); nhãn và ổ khóa truyện VIP ở Thư viện/chi tiết truyện; ví, cửa hàng đổi thưởng; quản trị truyện VIP, danh mục đổi thưởng, ví người dùng |

## 4. Định nghĩa "xong" cho mỗi chức năng

1. Use case có docstring ghi mã F/US. Đúng tầng, đúng quy tắc phụ thuộc.
2. Có unit test cho tiêu chí chấp nhận chính, và API test cho đường đi chính + lỗi quyền (403/404).
3. `ruff check`, `mypy` (domain, application), `pytest` đều qua.
4. Endpoint có trong OpenAPI, có `summary` tiếng Việt.
5. Không bí mật trong code/log. Dữ liệu cá nhân lọc theo `user_id`.

## 5. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Paddle/YOLO nặng, chạy CPU chậm | Worker riêng, xử lý tuần tự. Có cờ `PIPELINE_ENABLED=false` để dev nhanh. |
| Danh sách HSK chưa có | Cần tải danh sách HSK 3.0 từ nguồn mở (xin phép trước khi tải). |
| LLM tốn phí | Nhà cung cấp: Google Gemini (chọn 25/10/2026). Giai đoạn 5 làm đề dự phòng trước, adapter LLM sau; mọi chỗ dùng LLM (F09.06, F08.11) đều có phương án dự phòng và hạn mức mỗi ngày. Khóa API do bạn tự điền vào `.env`. |
| Gửi email thật (đặt lại mật khẩu, nhắc ôn) | Port `EmailSender`; khi dev dùng adapter ghi ra file. SMTP thật thêm sau nếu cần. |
| 151 chức năng, thời gian có hạn | Ưu tiên Must → Should → Could theo user story. Giai đoạn 6 có thể cắt bớt phần Could. |
| Nội dung AI (phân tích ngữ pháp F05.09, giải thích lỗi sai F09.10) có thể sai | Chỉ nhận JSON theo lược đồ cố định; máy chủ kiểm lược đồ và đối chiếu câu gốc (các cụm ghép lại đúng câu, nhãn thuộc danh sách cho phép, ví dụ chứa cấu trúc) hoặc từ điển; phần sai bị bỏ; giao diện luôn gắn nhãn "Do AI phân tích/viết, có thể chưa chính xác"; có dự phòng khi không hợp lệ. |
| Tốn lượt Gemini miễn phí (F05.09, F09.10, F08.11, đề kiểm tra) | Cache kết quả (ngữ pháp theo nội dung câu, dùng chung mọi người; giải thích lỗi sai lưu theo câu hỏi), hạn mức mỗi người mỗi ngày đặt trong `system_settings`, chỉ gọi khi người học chủ động bấm, LLM tắt hoặc hết hạn mức thì dùng dự phòng và trang vẫn dùng bình thường. |

## 6. Quyết định đã chốt (23/10/2026)

1. **Python 3.10+** (đã sửa `tech-stack.md`).
2. **CSDL mới `yinghua_db`** (+ `yinghua_test` cho kiểm thử) qua Alembic; chép dữ liệu từ điển từ `ptud_db`, giữ nguyên `ptud_db`.
3. **Được cài** asyncpg, argon2-cffi, fsrs, pytest, pytest-asyncio, ruff, mypy, nâng alembic; ghim phiên bản trong `server/requirements*.txt`.
5. **Code mới ở `server/`** (không dùng `backend/` vì trùng `Backend/` trên Windows); `Backend/` cũ giữ nguyên.
4. **Danh sách HSK 3.0**: chưa chốt — sẽ hỏi (tên file, nguồn, dung lượng) ở đầu Giai đoạn 2.

## 7. Hướng phát triển (sau giai đoạn 6.6; ngoài 151 chức năng, chưa có mã F, ghi nhận 25/10/2026)

Hai ý tưởng sau chỉ được mô tả, chưa xếp vào giai đoạn nào; mô tả chi tiết ở `docs/modules-functions.md` mục 7, user story US-HP-01 và US-HP-02 ở `docs/user-stories.md` mục 11. Khi quyết định làm phải viết đặc tả đầy đủ và xin duyệt.

| Ý tưởng | Nội dung | Rủi ro và điều kiện |
|---|---|---|
| Trợ lý học tập dạng trò chuyện có công cụ (HP-01) | Người học gõ yêu cầu tự nhiên; Gemini (function calling) chọn một công cụ trong danh sách cố định (tạo bài kiểm tra, mở ôn thẻ, phân tích ngữ pháp, tra từ), máy chủ kiểm tra rồi giao diện mở component viết sẵn tương ứng. | Tốn lượt gọi LLM (cần hạn mức và cache); phải giới hạn danh sách công cụ, thao tác ghi phải được người học xác nhận; thêm port mới và cập nhật `tech-stack.md` (hỏi trước). |
| Chấm phát âm bằng biểu đồ thanh điệu (HP-02) | Thu âm câu thoại, so đường cao độ với giọng chuẩn của TTS, tô đỏ các âm tiết sai thanh. | Cần thư viện xử lý âm thanh hoặc nhận dạng giọng nói ngoài danh sách `tech-stack.md` (phải hỏi trước khi làm); xử lý nặng phải chạy ở worker; âm thanh là dữ liệu cá nhân, xóa sau khi chấm. |
