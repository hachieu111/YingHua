# Thiết kế cơ sở dữ liệu YingHua (v1.0)

> Căn cứ: `docs/modules-functions.md` (mục "Dữ liệu chính" của 17 module; M16 Gamification bổ sung 25/10/2026, đặc tả đầy đủ cùng M17 VIP & Phần thưởng ngày 30/10/2026), `docs/user-stories.md`, `.claude/rules/database.md`, `naming-conventions.md`.
> Kế thừa thiết kế cũ (`Backend/app/models.py`, `Backend/docs/database_design.md`, CSDL `ptud_db`), có chỉnh sửa và bổ sung.
> Trạng thái: **đã duyệt 23/10/2026** (gồm mục 6.2; phạm vi mục 6.3 chốt ở mục 8). Các bảng được tạo **theo từng giai đoạn** bằng Alembic, đúng như thiết kế này. Muốn đổi thiết kế thì phải duyệt lại.

## 1. Quy ước chung

| Hạng mục | Quy ước |
|---|---|
| Tên bảng / cột | `snake_case`. Tên bảng ở số nhiều (`vocab_entries`). Khóa ngoại đặt `<bảng_số_ít>_id`. |
| Khóa chính | `BIGINT GENERATED ALWAYS AS IDENTITY`. Bảng quan hệ 1–1 hoặc bảng nối dùng khóa ghép. |
| Thời gian | `TIMESTAMPTZ` (lưu UTC), tên cột `<động_từ>_at`. Bảng nghiệp vụ có `created_at`; bảng sửa được có thêm `updated_at`. |
| Enum | `VARCHAR(n)` + `CHECK (... IN (...))` |
| Tên ràng buộc | Sinh tự động theo `NAMING_CONVENTION` trong `server/app/core/db.py` |
| JSONB | Chỉ dùng cho dữ liệu có cấu trúc lồng, không cần lọc theo từng trường: polygon, các dòng OCR, token, tham số FSRS. |
| File | CSDL chỉ lưu khóa tương đối tới FileStorage (bảng `stored_files`), **không** lưu dữ liệu nhị phân. |
| Xóa | Dữ liệu cá nhân dùng `ON DELETE CASCADE` theo `users`. Liên kết tới nội dung có thể mất (bong bóng, trang, file) dùng `SET NULL`, để sổ tay và lịch sử vẫn còn. |

Ký hiệu trong bảng cột: **PK** khóa chính · **FK** khóa ngoại · **UQ** duy nhất · **NN** không rỗng · **IX** chỉ mục.

## 2. Tổng quan theo module và giai đoạn tạo bảng

| Module | Bảng | Giai đoạn tạo |
|---|---|---|
| M01 Xác thực & Tài khoản | `users`, `refresh_tokens`, `password_reset_tokens` | GĐ1 |
| M02 Cài đặt cá nhân | `user_settings` | GĐ1 |
| M13 Quản trị (phần người dùng) | `admin_audit_logs` | GĐ1 |
| M06 Từ điển & Tra cứu | `dict_entries`, `dict_examples`, `hanzi`, `xianxia_entries`, `xianxia_rules`, `hsk_words`, `lookup_events` | GĐ2 |
| Dùng chung (lưu trữ) | `stored_files` | GĐ3 |
| M03 Thư viện truyện | `series` (kèm cột `genres`), `chapters`, `pages`, `reading_progress`, `page_reads`, `library_items`, `series_ratings` | GĐ3 (migration 0005) |
| M04 Xử lý ảnh | `translations` (đồng thời là hàng đợi job), `bubbles` | GĐ3 |
| M05 Đọc & Hover-Dịch | `bubble_edits`, `guest_sessions`, `page_annotations` | GĐ3 (migration 0005) |
| M15 Tác vụ nền | `scheduled_jobs`, `job_runs` | GĐ3 |
| M07 Sổ tay | `vocab_entries`, `vocab_contexts` | GĐ4 |
| M08 Ôn tập FSRS | `cards`, `review_logs`, `fsrs_parameters` | GĐ4 |
| M11 Phát âm | `tts_cache`, `external_call_logs` | GĐ4 |
| M09 Kiểm tra | `quizzes`, `quiz_questions` | GĐ5 |
| M10 Gợi ý | `dismissed_suggestions` | GĐ5 |
| M07 Sổ tay (câu thoại đã lưu, F07.11) | `saved_sentences` | GĐ5 |
| M08 Flashcard AI (F08.11) | `vocab_ai_notes` | GĐ5 |
| M12 Thống kê | `daily_activities` | GĐ6 |
| M13 Quản trị (phần còn lại) | `system_settings`, `content_removals` | GĐ6 |
| M14 Phản hồi & Thông báo | `error_reports`, `notifications`, `reminder_logs` | GĐ6 |
| M05 Phân tích ngữ pháp (F05.09) | `grammar_analyses`, `grammar_requests` | GĐ6 |
| M16 Gamification (mini-game, F16.01) | `minigame_sessions` | GĐ6.5 (migration 0012) |
| M16 Gamification (XP, mùa, huy hiệu; F16.02–F16.12) | `xp_events`, `seasons`, `season_results`, `achievements`, `user_achievements` | GĐ6.5 (migration 0012) |
| M17 VIP & Phần thưởng (F17.01–F17.10) | `wallets`, `wallet_ledger`, `vip_unlocks`, `avatar_frames`, `user_frames`, `reward_items`, `reward_redemptions` | GĐ6.5 (migration 0013) |

Cột mới ở GĐ6.5 (30/10/2026, chờ duyệt): `user_settings.show_on_leaderboard` (F16.08, migration 0012), `series.is_vip` (F17.05, F17.09, migration 0013). Nhiệm vụ ngày (F16.04) và mục tiêu tuần (F16.05) **không thêm bảng**: tiến độ tính từ `daily_activities`, mục tiêu lấy từ `user_settings.weekly_page_goal` (đã có từ GĐ1), việc đã thưởng nhận biết qua khóa chống trùng của `xp_events`. Huy hiệu và khung đang đeo lưu ở bảng của module sở hữu (`user_achievements.is_equipped`, `wallets.equipped_frame_id`), **không** thêm cột vào `users` (M01) để giữ ranh giới module.

Cột mới ở GĐ6 (25/10/2026): `quiz_questions.mistake_review`, `quiz_questions.mistake_review_at` (F09.10); `users.avatar_preset` (F01.10, migration 0010); `notifications.data` JSONB (F14.05, F14.06: đích điều hướng của thông báo; tạo cùng bảng ở migration 0009). F12.04 không thêm bảng. F01.11 (ghi nhớ đăng nhập), F13.04 (cờ kiểm duyệt tự động) và F04.16 (trang mẫu) cũng không thêm bảng hay cột: chế độ ghi nhớ suy ra từ hạn của `refresh_tokens`, cờ kiểm duyệt tính khi liệt kê, trang mẫu là khóa `sample_page_id` trong `system_settings`.

Tổng (cập nhật 30/10/2026, mười hai bảng mới của GĐ6.5: 5 bảng M16 và 7 bảng M17): **57 bảng**. Trước đó (cập nhật 25/10/2026, ba bảng mới: `grammar_analyses`, `grammar_requests`, `minigame_sessions`): 44 bảng, gồm 41 bảng đã thiết kế trước đó (37 bảng gốc, thêm `library_items`, `page_annotations` theo mục 6.2 và `series_ratings` theo mục 4.6, cập nhật 24/10/2026; bỏ `chapter_vocab` ở GĐ5, thêm `saved_sentences` (F07.11) và `vocab_ai_notes` (F08.11), cập nhật 25/10/2026). So với bản cũ: giữ 18 bảng (có đổi tên hoặc thêm cột), bỏ `vocab_suggestions` (SRS yêu cầu gợi ý tính khi gọi, không lưu sẵn), thêm 23 bảng mới. Cột mới ở GĐ5: `user_settings.bubble_font_scale` (F02.04).

## 3. Sơ đồ ERD (PlantUML, chỉ ghi khóa và quan hệ chính)

```plantuml
@startuml
hide circle
skinparam linetype ortho

package "M01/M02/M13 Tài khoản" {
  entity users { *id }
  entity refresh_tokens { *id\n--\nuser_id }
  entity password_reset_tokens { *id\n--\nuser_id }
  entity user_settings { *user_id }
  entity admin_audit_logs { *id\n--\nadmin_id }
}
package "Lưu trữ" { entity stored_files { *id\n--\nowner_id } }
package "M03 Thư viện" {
  entity series { *id\n--\nowner_id\ncover_file_id }
  entity chapters { *id\n--\nseries_id }
  entity pages { *id\n--\nchapter_id\noriginal_file_id\ntranslation_id }
  entity reading_progress { *user_id\n*chapter_id }
  entity page_reads { *user_id\n*page_id }
  entity library_items { *user_id\n*series_id }
  entity series_ratings { *user_id\n*series_id }
}
package "M04/M05 Xử lý ảnh & Đọc" {
  entity translations { *id\n--\nsource_file_id\ninpainted_file_id\nrendered_file_id }
  entity bubbles { *id\n--\ntranslation_id }
  entity bubble_edits { *user_id\n*bubble_id }
  entity guest_sessions { *id }
  entity page_annotations { *user_id\n*page_id }
}
package "M06 Từ điển" {
  entity dict_entries { *id }
  entity dict_examples { *id\n--\nentry_id }
  entity hanzi { *ch }
  entity hsk_words { *id }
  entity xianxia_entries { *id }
  entity xianxia_rules { *id }
  entity lookup_events { *id\n--\nuser_id\nentry_id\nbubble_id }
}
package "M07/M08 Sổ tay & Ôn tập" {
  entity vocab_entries { *id\n--\nuser_id\nentry_id }
  entity vocab_contexts { *id\n--\nvocab_entry_id\nbubble_id\npage_id\nsnippet_file_id }
  entity cards { *id\n--\nuser_id\nvocab_entry_id }
  entity review_logs { *id\n--\ncard_id\nuser_id }
  entity fsrs_parameters { *user_id }
  entity saved_sentences { *id\n--\nuser_id\nbubble_id\npage_id }
  entity vocab_ai_notes { *vocab_entry_id }
}
package "M09/M10/M11" {
  entity quizzes { *id\n--\nuser_id }
  entity quiz_questions { *id\n--\nquiz_id\nvocab_entry_id\nrelated_entry_id\nexample_id }
  entity dismissed_suggestions { *user_id\n*term }
  entity tts_cache { *id\n--\nfile_id }
  entity external_call_logs { *id }
}
package "M05 ngữ pháp / M16" {
  entity grammar_analyses { *id\n--\nsentence_hash }
  entity grammar_requests { *id\n--\nuser_id\nanalysis_id }
  entity minigame_sessions { *id\n--\nuser_id }
}
package "M16 Gamification" {
  entity xp_events { *id\n--\nuser_id }
  entity seasons { *id }
  entity season_results { *season_id\n*user_id }
  entity achievements { *id }
  entity user_achievements { *user_id\n*achievement_id }
}
package "M17 VIP & Phần thưởng" {
  entity wallets { *user_id\n--\nequipped_frame_id }
  entity wallet_ledger { *id\n--\nuser_id\nactor_id }
  entity vip_unlocks { *user_id\n*series_id }
  entity avatar_frames { *id }
  entity user_frames { *user_id\n*frame_id }
  entity reward_items { *id\n--\nframe_id }
  entity reward_redemptions { *id\n--\nuser_id\nitem_id }
}
package "M12/M13/M14/M15" {
  entity daily_activities { *user_id\n*activity_date }
  entity system_settings { *key }
  entity content_removals { *id\n--\nfile_id\nremoved_by }
  entity error_reports { *id\n--\nreporter_id\npage_id\nbubble_id }
  entity notifications { *id\n--\nuser_id }
  entity reminder_logs { *user_id\n*reminder_date }
  entity scheduled_jobs { *name }
  entity job_runs { *id\n--\njob_name }
}

users ||--o{ refresh_tokens
users ||--o{ password_reset_tokens
users ||--|| user_settings
users ||--o{ admin_audit_logs
users ||--o{ series
series ||--o{ chapters
chapters ||--o{ pages
pages }o--|| translations
translations ||--o{ bubbles
users ||--o{ bubble_edits
bubbles ||--o{ bubble_edits
users ||--o{ reading_progress
users ||--o{ page_reads
users ||--o{ library_items
series ||--o{ library_items
users ||--o{ series_ratings
series ||--o{ series_ratings
users ||--o{ page_annotations
pages ||--o{ page_annotations
dict_entries ||--o{ dict_examples
users ||--o{ vocab_entries
vocab_entries ||--o{ vocab_contexts
vocab_entries ||--o{ cards
vocab_entries ||--o| vocab_ai_notes
users ||--o{ saved_sentences
cards ||--o{ review_logs
users ||--|| fsrs_parameters
users ||--o{ quizzes
quizzes ||--o{ quiz_questions
dict_examples ||--o{ quiz_questions
users ||--o{ dismissed_suggestions
grammar_analyses ||--o{ grammar_requests
users ||--o{ grammar_requests
users ||--o{ minigame_sessions
users ||--o{ xp_events
seasons ||--o{ season_results
users ||--o{ season_results
achievements ||--o{ user_achievements
users ||--o{ user_achievements
users ||--o| wallets
avatar_frames |o--o{ wallets
users ||--o{ wallet_ledger
users ||--o{ vip_unlocks
series ||--o{ vip_unlocks
avatar_frames ||--o{ user_frames
users ||--o{ user_frames
avatar_frames |o--o{ reward_items
reward_items ||--o{ reward_redemptions
users ||--o{ reward_redemptions
users ||--o{ daily_activities
users ||--o{ error_reports
users ||--o{ notifications
scheduled_jobs ||--o{ job_runs
@enduml
```

## 4. Đặc tả bảng

### 4.1 M01 Xác thực & Tài khoản — GĐ1

**`users`**: tài khoản (F01.01–F01.09, F13.01–F13.03)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| email | VARCHAR(254) | NN | UQ trên `lower(email)` |
| password_hash | TEXT | NN | Argon2id; hash bcrypt cũ được băm lại khi người dùng đăng nhập |
| display_name | VARCHAR(100) | NN | |
| avatar_file_id | BIGINT | FK stored_files SET NULL | Ảnh đại diện tải lên (F01.10); loại trừ với `avatar_preset` |
| avatar_preset | VARCHAR(32) | | Mã ảnh đại diện có sẵn (F01.10, GĐ6): `original`, `sakura_flower`, `bach_thien`, `tieu_vu_tru`, `mac_van`, `lac_ly`; danh sách mã nằm trong mã nguồn, không có bảng riêng; đặt thì `avatar_file_id` bị bỏ |
| role | VARCHAR(16) | NN, CHECK `user`/`admin`, mặc định `user` | |
| status | VARCHAR(16) | NN, CHECK `active`/`locked`, mặc định `active` | |
| locked_reason | VARCHAR(500) | | Lý do khóa (US-QT-03) |
| locked_at | TIMESTAMPTZ | | |
| password_changed_at | TIMESTAMPTZ | | Dùng để vô hiệu token cũ |
| last_login_at | TIMESTAMPTZ | | |
| created_at, updated_at | TIMESTAMPTZ | NN | `created_at` là ngày tham gia |

IX: `(role)`, `(status)`, trigram trên `display_name` và `email` để tìm người dùng (F13.01).

**`refresh_tokens`**: phiên đăng nhập theo thiết bị, xoay vòng (F01.03–F01.05)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| user_id | BIGINT | FK users CASCADE, NN, IX |
| token_hash | CHAR(64) | NN, UQ (SHA-256) |
| family_id | UUID | NN, IX (cùng một chuỗi xoay vòng) |
| replaced_by_id | BIGINT | FK refresh_tokens SET NULL |
| user_agent | VARCHAR(255) | |
| ip | VARCHAR(64) | |
| expires_at | TIMESTAMPTZ | NN |
| revoked_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | NN |

Ghi nhớ đăng nhập (F01.11): **không có cột riêng**. Đăng nhập với `remember_me = true` đặt `expires_at` sau 30 ngày; `false` đặt sau `REFRESH_TOKEN_SHORT_HOURS` (mặc định 24 giờ). Khi làm mới, chế độ được suy ra bằng cách so `expires_at - created_at` của phiên cũ với hạn ngắn, rồi phiên mới kế thừa.

**`password_reset_tokens`**: liên kết đặt lại mật khẩu, dùng một lần, hết hạn sau 30 phút (F01.06)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| user_id | BIGINT | FK users CASCADE, NN, IX |
| token_hash | CHAR(64) | NN, UQ |
| expires_at | TIMESTAMPTZ | NN |
| used_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | NN |

### 4.2 M02 Cài đặt cá nhân — GĐ1

**`user_settings`**: quan hệ 1–1 với `users` (F02.01–F02.04, F11.03, F14.03, F06.03)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| user_id | BIGINT | PK, FK users CASCADE | |
| hsk_level | SMALLINT | CHECK 1–9 | NULL nghĩa là "Chưa chọn" |
| default_mode | VARCHAR(8) | NN, CHECK `read`/`learn`, mặc định `read` | |
| tts_voice | VARCHAR(64) | | NULL thì dùng giọng mặc định |
| tts_rate | NUMERIC(3,2) | NN, CHECK 0.50–1.50, mặc định 1.00 | |
| show_xianxia | BOOLEAN | NN, mặc định true | Hiện từ điển tu tiên |
| reminder_enabled | BOOLEAN | NN, mặc định false | F14.03 |
| reminder_time | TIME | | Giờ địa phương |
| timezone | VARCHAR(64) | NN, mặc định `Asia/Ho_Chi_Minh` | Tính "hôm nay" và chuỗi ngày học |
| bubble_font_scale | SMALLINT | NN, mặc định 100, CHECK BETWEEN 80 AND 160 | Cỡ chữ lớp dịch trên trang, đơn vị phần trăm, bước 10 (F02.04, US-NH-74); thêm ở GĐ5 bằng migration mới |
| dismissed_tours | VARCHAR(16)[] | NN, mặc định rỗng | Các tour đã xem hoặc chọn không nhắc lại: khóa tour của F02.05 (migration 0016) |
| show_on_leaderboard | BOOLEAN | NN, mặc định true | Hiện tên, ảnh, huy hiệu, khung trên bảng xếp hạng; tắt thì người khác thấy "Học viên ẩn danh" (F16.08, US-NH-89); **thêm ở GĐ6.5, migration 0012** |
| updated_at | TIMESTAMPTZ | NN | |

Ghi chú: hai cột `learning_goal` và `weekly_page_goal` (CHECK 1–1000) đã tạo ở GĐ1 theo mục 6.2; `weekly_page_goal` là mục tiêu tuần của F12.04 và F16.05 (NULL thì F16.05 dùng mặc định 20 trang).

### 4.3 M13 Quản trị (phần người dùng) — GĐ1

**`admin_audit_logs`**: nhật ký thao tác quản trị (F13.06)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| admin_id | BIGINT | FK users SET NULL, IX |
| action | VARCHAR(48) | NN (vd. `user.role_changed`, `user.locked`, `series.deleted`) |
| target_type | VARCHAR(32) | NN |
| target_id | BIGINT | |
| details | JSONB | NN, mặc định `{}` (giá trị trước/sau; không chứa mật khẩu hay token) |
| created_at | TIMESTAMPTZ | NN, IX |

> Ghi chú (24/10/2026, F13.07, US-QT-14): thao tác của Quản trị viên sửa/xóa dữ liệu học tập của người dùng khác dùng lại bảng này, không thêm bảng mới. `action` thuộc nhóm `user_data.*` (vd. `user_data.vocab_deleted`, `user_data.card_reset`, `user_data.settings_updated`); `target_type`/`target_id` trỏ tới đối tượng bị tác động; `details` lưu `user_id` của người dùng đích và tên các trường bị đổi, không chép nội dung ghi chú, ngữ cảnh, mật khẩu hay token.

### 4.4 M06 Từ điển & Tra cứu — GĐ2 (đã tạo: migration 0003, 0004)

Nguồn dữ liệu (nạp bằng `server/scripts/load_dictionaries.py`):

| Nguồn | Vào bảng | Giấy phép |
|---|---|---|
| Thiên Chửu (chép từ `ptud_db`, chủ yếu chữ đơn) | `dict_entries` (`source='thienchuu'`), ví dụ trong giải nghĩa → `dict_examples` (`gloss`) | theo dữ liệu gốc của dự án |
| **CVDICT** — Trung–Việt ~119.000 mục, dựa trên CC-CEDICT (bản sao `thaoshibe/chugiai-zh-en-vi`, gốc `ph0ngp/CVDICT`) | `dict_entries` (`source='cvdict'`) | **CC BY-SA 4.0** — phải ghi nguồn |
| **complete-hsk-vocabulary** (`drkameleon`) — nhãn `new-1…new-7` = HSK 3.0 (7 = nhóm 7–9) | `hsk_words` | MIT |
| **Tatoeba** — câu đời thường Trung + bản dịch Việt (trực tiếp hoặc nối qua câu tiếng Anh) | `dict_examples` (`tatoeba`, `source_ref='tatoeba:<id>'`) | **CC BY 2.0 FR** — phải ghi nguồn |
| Hán tự (`ptud_db.hanzi`) + âm Hán Việt từ PhienAm | `hanzi` | theo dữ liệu gốc |
| VietPhrase / Names / PhienAm / LuatNhan (`ptud_db`) | `xianxia_entries`, `xianxia_rules` | theo dữ liệu gốc |

**`dict_entries`**: (F06.01, F06.02)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| simplified | VARCHAR(64) | NN, IX | |
| traditional | VARCHAR(64) | IX | |
| pinyin | VARCHAR(160) | NN | Có dấu thanh |
| pinyin_numeric | VARCHAR(160) | NN | `xue2 xi2` |
| pinyin_search | VARCHAR(128) | NN, IX `varchar_pattern_ops` | `xuexi` — bỏ dấu, số thanh, khoảng trắng; tìm theo tiền tố |
| pinyin_source | VARCHAR(16) | NN, CHECK `dict`/`pypinyin` | |
| han_viet | VARCHAR(160) | | Từ ghép thiếu thì ghép từ `hanzi.han_viet` khi tra |
| meanings_vi | JSONB | NN, mặc định `[]` | `[{src, gloss}]`, mỗi nghĩa một phần tử |
| meanings_en | JSONB | NN, mặc định `[]` | |
| search_vi | TEXT | NN, GIN trigram | Nghĩa Việt gộp, chữ thường — tìm theo nghĩa |
| part_of_speech | VARCHAR(64) | | Mã gốc (vd `v,vn`); thiếu thì lấy `hsk_words.pos` khi tra |
| freq_rank | INTEGER | | |
| source | VARCHAR(16) | NN | `thienchuu` · `cvdict` |

UQ `(simplified, pinyin_numeric, source)`. Khi tra, các mục cùng chữ + cùng cách đọc (khác nguồn) được gộp thành một "cách đọc".

**`dict_examples`**: id PK · entry_id FK dict_entries CASCADE IX · zh TEXT NN · pinyin TEXT · vi TEXT (NULL = chưa có bản dịch Việt; Giai đoạn 5 dùng LLM bù) · source VARCHAR(16) CHECK `curated`/`gloss`/`tatoeba`/`llm` · source_ref VARCHAR(32) · difficulty_level SMALLINT (cấp HSK cao nhất của các từ trong câu, dùng lọc độ khó khi ra đề F09.01; tính bằng script nạp, chạy lại không nhân bản dữ liệu; thêm ở GĐ5, 25/10/2026) · created_at. Mỗi từ tối đa 3 câu Tatoeba, ưu tiên câu có bản dịch Việt, câu dễ (cấp HSK cao nhất trong câu thấp), câu ngắn.

**`hanzi`**: phân rã chữ Hán (F06.05). Khóa chính là `ch VARCHAR(2)`. Các cột: pinyin, pinyin_source, han_viet, radical VARCHAR(2), stroke_count SMALLINT, decomposition VARCHAR(64), components TEXT[], etymology JSONB, definition_en TEXT, stroke_data JSONB.

**`xianxia_entries`**: từ điển tu tiên (F06.03, pipeline F04.11): id PK · kind VARCHAR(8) CHECK `phrase`/`name`/`char` · key VARCHAR(64) NN · pinyin · pinyin_numeric · meanings TEXT[] NN. IX `(kind, key)`. F06.03 chỉ hiện mục chuyên ngành khi là tên riêng hoặc nghĩa khác nghĩa thông thường; người học tắt được bằng `user_settings.show_xianxia`.

**`xianxia_rules`**: luật nhân, giữ nguyên dạng gốc: seq INTEGER PK · rule TEXT NN (`mẫu=thay thế`).

**`hsk_words`** (**mới**): danh sách HSK 3.0 (F06.07, F06.08)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| word | VARCHAR(32) | NN, UQ |
| level | SMALLINT | NN, CHECK 1–9 (7 = nhóm 7–9 của HSK 3.0) |
| pinyin | VARCHAR(128) | |
| pos | VARCHAR(64) | Từ loại (mã), vd `v,vn` |
| list_version | VARCHAR(16) | NN, mặc định `3.0` |
| imported_at | TIMESTAMPTZ | NN |

Cấp của một chữ đơn lẻ cũng tra trong bảng này (dòng có `word` dài 1 ký tự). F06.08 lấy cấp cao nhất của các chữ cấu thành khi không có nguyên từ. Từ có nhiều cách đọc trong danh sách gốc được gộp, lấy cấp thấp nhất.

**`lookup_events`**: lịch sử tra cứu, dùng cho gợi ý (F10.01) và thống kê

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| user_id | BIGINT | FK users CASCADE, NN |
| term | VARCHAR(32) | NN |
| entry_id | BIGINT | FK dict_entries SET NULL |
| bubble_id | BIGINT | FK bubbles SET NULL (khóa ngoại thêm ở GĐ3) |
| action | VARCHAR(12) | NN, CHECK `hover`/`lookup`/`decompose`/`tts` |
| created_at | TIMESTAMPTZ | NN |

IX `(user_id, term)`, `(user_id, created_at)`.

### 4.5 Lưu trữ file — GĐ3

**`stored_files`**

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| kind | VARCHAR(16) | NN, CHECK `original`/`inpainted`/`rendered`/`snippet`/`cover`/`audio`/`avatar` | |
| storage_key | TEXT | NN, UQ | Đường dẫn tương đối, tên file ngẫu nhiên |
| sha256 | CHAR(64) | NN, IX | Chống trùng |
| mime_type | VARCHAR(64) | NN | |
| size_bytes | INTEGER | NN | |
| width, height | INTEGER | | |
| owner_id | BIGINT | FK users SET NULL | Người tải lên |
| expires_at | TIMESTAMPTZ | IX (chỉ dòng khác NULL) | Ảnh tải nhanh giữ 7 ngày |
| removed_at | TIMESTAMPTZ | | Bị gỡ khi kiểm duyệt (F13.04) |
| created_at | TIMESTAMPTZ | NN | |

### 4.6 M03 Thư viện truyện — GĐ3

**`series`**: (F03.02, F03.04, F03.05, F03.09–F03.11)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| owner_id | BIGINT | FK users CASCADE | NULL nghĩa là thư viện chung do admin đăng |
| visibility | VARCHAR(8) | NN, CHECK `public`/`private` | CHECK: `public` thì `owner_id` NULL; `private` thì `owner_id` khác NULL |
| title_vi | VARCHAR(255) | NN, trigram | |
| title_zh | VARCHAR(255) | trigram | |
| author | VARCHAR(255) | | |
| description | TEXT | | |
| cover_file_id | BIGINT | FK stored_files SET NULL | |
| status | VARCHAR(12) | NN, CHECK `ongoing`/`completed` | |
| est_hsk_level | SMALLINT | CHECK 1–9 | |
| created_by | BIGINT | FK users SET NULL | |
| genres | VARCHAR(32)[] | NN, mặc định mảng rỗng | Thể loại hiển thị trên thẻ truyện (mục 6.2); **tạo ở GĐ3, migration 0005** |
| is_vip | BOOLEAN | NN, mặc định false | Truyện VIP (F17.05, F17.09): người không VIP chỉ đọc chương `is_trial`. CHECK `NOT is_vip OR visibility = 'public'` (truyện riêng tư không có VIP). IX `(is_vip) WHERE is_vip`. **Thêm ở GĐ6.5, migration 0013** |
| created_at, updated_at | TIMESTAMPTZ | NN | |

**`chapters`**: id PK · series_id FK series CASCADE NN · number NUMERIC(6,1) NN · title VARCHAR(255) · is_trial BOOLEAN NN mặc định false (**mới**, cho phép Khách đọc thử, F03.03) · created_at, updated_at. UQ `(series_id, number)`.

**`pages`**: (F03.07, F03.08, F04.02)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| chapter_id | BIGINT | FK chapters CASCADE | NULL nghĩa là ảnh tải nhanh (F03.08) |
| owner_id | BIGINT | FK users CASCADE | Bắt buộc khi là ảnh tải nhanh |
| page_no | SMALLINT | NN | UQ `(chapter_id, page_no)` |
| original_file_id | BIGINT | FK stored_files SET NULL | |
| translation_id | BIGINT | FK translations SET NULL, IX | |
| width, height | INTEGER | | |
| created_at | TIMESTAMPTZ | NN | |

CHECK `chapter_id IS NOT NULL OR owner_id IS NOT NULL`.

**`reading_progress`**: PK `(user_id, chapter_id)` · last_page_no SMALLINT NN · mode VARCHAR(8) CHECK `read`/`learn` · completed BOOLEAN NN · updated_at. IX `(user_id, updated_at)` để lấy truyện đang đọc dở (F03.12).

**`page_reads`** (**mới**): PK `(user_id, page_id)` · first_read_at TIMESTAMPTZ NN. Ghi các trang đã đọc, phục vụ thống kê số trang đã đọc (F12.01, F12.02).

**`library_items`** (tạo ở GĐ3, migration 0005; F03.13, US-NH-61): Thư viện cá nhân và yêu thích.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| user_id | BIGINT | PK (thành phần), FK users CASCADE | |
| series_id | BIGINT | PK (thành phần), FK series CASCADE | |
| is_favorite | BOOLEAN | NN, mặc định false | Tab "Yêu thích" |
| added_at | TIMESTAMPTZ | NN | |

**`series_ratings`** (**mới**, tạo ở GĐ3; F03.14, US-NH-62): lượt chấm sao truyện, mỗi người một lượt cho mỗi truyện, sửa được. Điểm trung bình và số lượt chấm được tính khi truy vấn (`AVG(stars)`, `COUNT(*)`), không lưu sẵn.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| user_id | BIGINT | PK (thành phần), FK users CASCADE | |
| series_id | BIGINT | PK (thành phần), FK series CASCADE, IX | IX để tính trung bình theo truyện |
| stars | SMALLINT | NN, CHECK `stars BETWEEN 1 AND 5` | |
| created_at | TIMESTAMPTZ | NN | |
| updated_at | TIMESTAMPTZ | NN | Cập nhật khi người dùng chấm lại |

### 4.7 M04 Xử lý ảnh — GĐ3

**`translations`**: kết quả xử lý một **ảnh**, đồng thời là **hàng đợi job**. Worker lấy việc bằng `FOR UPDATE SKIP LOCKED`. Ảnh trùng (sha256 hoặc pHash) dùng lại bản ghi này (F04.07, F04.13, F04.14). Pipeline chạy hai giai đoạn (F04.01, 30/10/2026): giai đoạn chữ ghi `bubbles` ngay khi xong (status vẫn `running`), giai đoạn ảnh chỉ cập nhật `style` của bong bóng đã có cùng `inpainted_file_id`, `rendered_file_id` rồi đặt `done`. Cờ "đã có chữ" (`text_ready` trong API) **không lưu thành cột**: suy ra từ việc bản dịch đã có bong bóng, nên không cần migration.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| source_file_id | BIGINT | FK stored_files SET NULL | |
| sha256 | CHAR(64) | NN, IX | |
| phash | BIGINT | IX | |
| status | VARCHAR(12) | NN, CHECK `queued`/`running`/`done`/`failed` | IX `(status, queued_at)` |
| pipeline_version | VARCHAR(32) | NN | |
| attempts | SMALLINT | NN, mặc định 0 | |
| worker_id | VARCHAR(64) | | Worker đang giữ job |
| error_step | VARCHAR(32) | | `detect`/`ocr`/`segment`/`translate`/`inpaint`/`render` |
| error_message | VARCHAR(1000) | | Thông điệp đọc được, không có stack trace |
| inpainted_file_id, rendered_file_id | BIGINT | FK stored_files SET NULL | |
| stats | JSONB | NN, mặc định `{}` | Thời gian chạy từng bước |
| processing_ms | INTEGER | | |
| queued_at | TIMESTAMPTZ | NN | |
| started_at, finished_at | TIMESTAMPTZ | | |

**`bubbles`**: (F04.08–F04.10, F04.15)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| translation_id | BIGINT | FK translations CASCADE, NN |
| idx | SMALLINT | NN, thứ tự đọc; UQ `(translation_id, idx)` |
| class_name | VARCHAR(16) | NN, CHECK `speech_bubble`/`sound_effect`/`calligraphy`/`floating_text` |
| x, y, w, h | INTEGER | NN (pixel theo ảnh gốc) |
| polygon | JSONB | |
| confidence | REAL | |
| text_zh | TEXT | NN |
| pinyin | TEXT | |
| text_vi | TEXT | |
| translate_method | VARCHAR(32) | |
| lines | JSONB | NN `[]`: các dòng OCR kèm tọa độ, chiều dọc/ngang |
| tokens | JSONB | NN `[]`: `[{w, start, end, pinyin, entry_id}]` |
| style | JSONB | |

### 4.8 M05 Đọc & Hover-Dịch — GĐ3

**`bubble_edits`**: bản sửa dịch riêng của từng người: PK `(user_id, bubble_id)` · text_vi TEXT NN · created_at, updated_at (F05.05, F05.06).

**`guest_sessions`** (**mới**): đếm lượt tra của Khách theo phiên ẩn danh (F05.04): id UUID PK · lookup_count SMALLINT NN mặc định 0 · created_at · expires_at NN IX.

**`page_annotations`** (tạo ở GĐ3, migration 0005; F05.07, F05.08, US-NH-63, US-NH-64): dấu trang và ghi chú trên trang, lưu theo người dùng ở máy chủ (thay cho localStorage): PK `(user_id, page_id)` · is_bookmarked BOOLEAN NN mặc định false · highlights JSONB NN mặc định `[]` (bong bóng được tô màu và màu) · strokes JSONB NN mặc định `[]` (nét vẽ: màu, danh sách điểm) · updated_at TIMESTAMPTZ NN. FK `user_id` → users CASCADE, `page_id` → pages CASCADE. IX `(user_id, updated_at)` cho danh sách trang đã lưu (lọc `is_bookmarked`).

**`grammar_analyses`** (tạo ở GĐ6; F05.09, US-NH-78): kết quả phân tích ngữ pháp câu thoại, **dùng chung mọi người** vì không chứa dữ liệu cá nhân, cache theo nội dung câu.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| sentence_hash | CHAR(64) | NN, UQ | SHA-256 của câu đã chuẩn hóa (Unicode NFC, bỏ khoảng trắng thừa) |
| sentence_zh | TEXT | NN | Câu chữ Hán đã chuẩn hóa |
| content | JSONB | NN | Cây cú pháp (nhãn, đoạn chữ, nút con) và danh sách 1–3 điểm ngữ pháp (tên cấu trúc, giải thích, ví dụ) đã qua kiểm tra của máy chủ; không lưu kết quả rỗng |
| model | VARCHAR(64) | | Tên mô hình đã sinh (vd. giá trị `LLM_MODEL`) |
| created_at | TIMESTAMPTZ | NN | |

**`grammar_requests`** (tạo ở GĐ6; F05.09): ghi mỗi lượt Người học **phải gọi LLM** (cache chưa có), dùng để đếm hạn mức mỗi ngày. Chọn bảng riêng thay vì thêm `user_id` vào `external_call_logs` vì nhật ký gọi dịch vụ ngoài cố ý không chứa dữ liệu cá nhân (mục 4.12), và cũng không đặt `user_id` vào `grammar_analyses` vì bảng này dùng chung.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | |
| analysis_id | BIGINT | FK grammar_analyses SET NULL | Có khi lượt gọi sinh được kết quả hợp lệ; NULL khi kết quả bị loại. Lỗi kỹ thuật của LLM (tắt, quá thời gian, dịch vụ lỗi) không tính lượt theo F05.09 |
| requested_at | TIMESTAMPTZ | NN | IX `(user_id, requested_at)` để đếm theo ngày của người dùng |

Hạn mức: khóa `grammar_daily_limit` trong `system_settings` (mục 4.16). Lượt dùng kết quả có sẵn không ghi vào bảng này nên không tốn hạn mức.

### 4.9 M15 Tác vụ nền — GĐ3

**`scheduled_jobs`**: name VARCHAR(48) PK · interval_seconds INTEGER NN · enabled BOOLEAN NN · last_started_at · last_finished_at · last_status VARCHAR(12) CHECK `ok`/`failed` · locked_until TIMESTAMPTZ · locked_by VARCHAR(64). Hai cột cuối là khóa chống chạy chồng (F15.03).

**`job_runs`**: id PK · job_name FK scheduled_jobs CASCADE IX · started_at NN · finished_at · status VARCHAR(12) CHECK `running`/`ok`/`failed` · summary JSONB (vd. số file đã dọn) · error_message.

### 4.10 M07 Sổ tay cá nhân — GĐ4

**`vocab_entries`**: đổi tên từ `user_vocab` (F07.01–F07.07, F07.09)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | UQ `(user_id, term)` |
| term | VARCHAR(32) | NN | |
| entry_id | BIGINT | FK dict_entries SET NULL | |
| pinyin | VARCHAR(128) | | Lưu bản sao, không phụ thuộc từ điển |
| meaning_vi | TEXT | | Lưu bản sao, sửa được |
| hsk_level | SMALLINT | CHECK 1–9 | NULL nghĩa là "Ngoài HSK" |
| hsk_source | VARCHAR(12) | NN, CHECK `list`/`derived`/`none` | `derived` = suy từ chữ cấu thành |
| status | VARCHAR(12) | NN, CHECK `learning`/`known`/`ignored` | IX `(user_id, status)` |
| source | VARCHAR(12) | NN, CHECK `highlight`/`lookup`/`suggestion`/`manual`/`quiz` | |
| note | VARCHAR(1000) | | Tối đa 1000 ký tự |
| is_starred | BOOLEAN | NN, DEFAULT false | Đánh dấu sao từ (F07.09, US-NH-66); thêm ở GĐ4 theo mục 6.2 |
| created_at, updated_at | TIMESTAMPTZ | NN | |

IX `(user_id, hsk_level)`.

Ghi chú truy vấn, không thêm bảng hay cột mới:
- **Bộ thẻ theo truyện** (F08.10, US-NH-67): từ thuộc truyện nào được suy ra qua `vocab_contexts` → `pages` → `chapters` → `series`. Bộ "Từ đánh dấu sao" lọc theo `vocab_entries.is_starred`. Số từ đã ôn của một bộ là số mục từ có ít nhất một thẻ (`cards`) đã có `review_logs`. Ngữ cảnh có `page_id` NULL (trang đã xóa) không đóng góp vào bộ truyện nào.
- **Âm Hán Việt** (F07.10, US-NH-68): không lưu ở sổ tay; đọc từ `dict_entries.han_viet` qua `vocab_entries.entry_id`, thiếu thì ghép từ `hanzi.han_viet` của từng chữ trong `term` (M06, F06.01).

**`vocab_contexts`**: id PK · vocab_entry_id FK vocab_entries CASCADE NN IX · bubble_id FK bubbles SET NULL · page_id FK pages SET NULL · sentence_zh TEXT NN · sentence_vi TEXT · snippet_file_id FK stored_files SET NULL (ảnh cắt là **bản sao độc lập**, không hết hạn) · source_label VARCHAR(255) · created_at. UQ `(vocab_entry_id, bubble_id)`: lưu lại cùng một bong bóng không tạo ngữ cảnh trùng.

**`saved_sentences`** (**mới**, tạo ở GĐ5; F07.11, US-NH-70): câu thoại Người học lưu từ trang truyện. Lưu **bản sao văn bản** để câu vẫn còn khi trang hoặc bong bóng bị xóa.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | |
| bubble_id | BIGINT | FK bubbles SET NULL | NULL khi bong bóng đã bị xóa |
| page_id | BIGINT | FK pages SET NULL | Dùng cho "Mở trang gốc"; NULL thì ẩn nút |
| sentence_zh | TEXT | NN | Câu tiếng Trung |
| sentence_vi | TEXT | | Bản dịch tại thời điểm lưu (bản sửa cá nhân nếu có) |
| source_label | VARCHAR(255) | | "Truyện · Chương · Trang" |
| note | TEXT | | Tối đa 1000 ký tự (kiểm ở tầng ứng dụng) |
| created_at, updated_at | TIMESTAMPTZ | NN | |

UQ `(user_id, bubble_id)`: một bong bóng chỉ lưu một lần mỗi người. IX `(user_id, created_at)`: danh sách mới nhất trước, phân trang. Quản trị viên xem và xóa qua F13.07.

Bảng **không lưu pinyin**: khi trả danh sách, pinyin được dựng từ `bubbles.tokens` của bong bóng gốc (bong bóng đã xóa thì không có pinyin). Khi hiển thị, bản dịch ưu tiên bản sửa cá nhân (F05.05) nếu có, nếu không dùng `sentence_vi`.

### 4.11 M08 Ôn tập FSRS — GĐ4

**`cards`**: đổi tên từ `flashcards`, chuyển từ SM-2 sang FSRS (F08.01–F08.05, F08.09)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | |
| vocab_entry_id | BIGINT | FK vocab_entries CASCADE, NN | UQ `(vocab_entry_id, card_type)` |
| card_type | VARCHAR(12) | NN, CHECK `recognition`/`recall`/`listening` | |
| state | VARCHAR(12) | NN, CHECK `learning`/`review`/`relearning` | Đúng 3 trạng thái của FSRS |
| step | SMALLINT | | Bước học (FSRS learning step) |
| stability | DOUBLE PRECISION | | S |
| difficulty | DOUBLE PRECISION | | D |
| due_at | TIMESTAMPTZ | NN | |
| last_review_at | TIMESTAMPTZ | | |
| reps, lapses | INTEGER | NN, mặc định 0 | |
| is_suspended | BOOLEAN | NN, mặc định false | F08.05 |
| created_at, updated_at | TIMESTAMPTZ | NN | |

IX `(user_id, due_at) WHERE NOT is_suspended`. Bỏ các cột SM-2 (`ease_factor`, `interval_days`).

**`review_logs`**: (F08.02, F08.06, F08.08)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| card_id | BIGINT | FK cards CASCADE, NN, IX |
| user_id | BIGINT | FK users CASCADE, NN, IX `(user_id, reviewed_at)` |
| rating | SMALLINT | NN, CHECK 1–4 (Quên/Khó/Được/Dễ) |
| state_before | VARCHAR(12) | NN |
| stability_before, stability_after | DOUBLE PRECISION | |
| difficulty_before, difficulty_after | DOUBLE PRECISION | |
| due_after | TIMESTAMPTZ | NN |
| duration_ms | INTEGER | |
| presentation_id | UUID | NN, UQ: chống bấm đúp gửi trùng |
| reviewed_at | TIMESTAMPTZ | NN |

**`fsrs_parameters`**: tham số FSRS riêng từng người (F08.08): user_id PK FK users CASCADE · weights DOUBLE PRECISION[] NN · desired_retention NUMERIC(3,2) NN mặc định 0.90 · review_count INTEGER NN (số lượt ôn lúc tối ưu) · optimized_at TIMESTAMPTZ NN.

**`vocab_ai_notes`** (**mới**, tạo ở GĐ5; F08.11, US-NH-75): bộ đệm "Thẻ mở rộng AI" cho mỗi mục từ, để không gọi LLM lại.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| vocab_entry_id | BIGINT | PK, FK vocab_entries CASCADE | Một mục từ có tối đa một thẻ mở rộng; xóa mục từ thì xóa theo |
| content | JSONB | NN | 2 câu ví dụ (zh, vi), mẹo chiết tự, 2–3 cụm từ; cấu trúc lồng, không lọc theo từng trường |
| model | VARCHAR(64) | | Tên mô hình LLM đã dùng; NULL với nội dung dự phòng |
| source | VARCHAR(12) | NN, CHECK `llm`/`fallback` | `fallback` = ví dụ từ điển và chiết tự từ dữ liệu M06 |
| generated_at | TIMESTAMPTZ | NN | |
| regenerate_count | SMALLINT | NN, mặc định 0 | Số lần "Tạo lại", giới hạn theo cấu hình |

Hạn mức gọi LLM mỗi người mỗi ngày: đếm các dòng `source = 'llm'` có `generated_at` trong ngày (múi giờ người học) qua `vocab_entries.user_id`; không thêm bảng riêng, vì `external_call_logs` không lưu người dùng (không chứa dữ liệu cá nhân). Tạo lại cùng một mục từ ghi đè `generated_at` nên chỉ đếm một lần; `regenerate_count` giới hạn số lần tạo lại. Lời gọi vẫn ghi vào `external_call_logs` với `operation = 'ai_note'`. Nội dung gửi LLM chỉ gồm từ, pinyin, nghĩa, cấp HSK và trình độ, không có dữ liệu cá nhân.

### 4.12 M11 Phát âm & dịch vụ ngoài — GĐ4

**`tts_cache`**: id PK · text_sha256 CHAR(64) NN · voice VARCHAR(64) NN · rate NUMERIC(3,2) NN · file_id FK stored_files CASCADE NN · created_at. UQ `(text_sha256, voice, rate)` (F11.05).

**`external_call_logs`**: nhật ký gọi dịch vụ ngoài, **không** chứa dữ liệu cá nhân (F08.11, F09.06–F09.08, F11.06)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| service | VARCHAR(8) | NN, CHECK `llm`/`tts` |
| provider | VARCHAR(32) | NN |
| operation | VARCHAR(32) | NN (vd. `generate_quiz`, `synthesize`) |
| status | VARCHAR(12) | NN, CHECK `ok`/`timeout`/`invalid`/`error` |
| latency_ms | INTEGER | |
| error_code | VARCHAR(64) | |
| created_at | TIMESTAMPTZ | NN, IX `(service, created_at)` |

### 4.13 M09 Kiểm tra cá nhân hóa — GĐ5

**`quizzes`**: mỗi bài kiểm tra có một lượt làm (F09.01–F09.05)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| user_id | BIGINT | FK users CASCADE, NN, IX `(user_id, created_at)` |
| source | VARCHAR(12) | NN, CHECK `llm`/`fallback`/`mixed` |
| status | VARCHAR(12) | NN, CHECK `in_progress`/`submitted` |
| question_count | SMALLINT | NN |
| score | SMALLINT | Điểm chính, chỉ đếm câu về từ đã lưu (`target_kind = 'saved'`) |
| related_score | SMALLINT | Điểm riêng "Đoán từ mới" của câu từ mở rộng (F09.09); không vào `score` |
| related_count | SMALLINT | NN, DEFAULT 0: số câu từ mở rộng trong bài |
| fallback_reason | VARCHAR(24) | CHECK `llm_disabled`/`timeout`/`invalid_schema`/`network`/`daily_limit`; nguyên nhân dùng đề dự phòng, chỉ lưu nội bộ, không trả cho Người học (F09.08) |
| note | TEXT | Ghi chú hiển thị, vd. "Đề tạo tự động từ từ điển" |
| wrong_cards_rescheduled_at | TIMESTAMPTZ | Đánh dấu đã áp dụng "ôn sớm" (F09.04), tránh làm hai lần |
| created_at | TIMESTAMPTZ | NN |
| submitted_at | TIMESTAMPTZ | |

**`quiz_questions`**: đáp án đúng **chỉ trả cho trình duyệt sau khi nộp bài**

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| quiz_id | BIGINT | FK quizzes CASCADE, NN; UQ `(quiz_id, position)` |
| position | SMALLINT | NN |
| question_type | VARCHAR(16) | NN, CHECK `multiple_choice`/`fill_blank` |
| prompt | TEXT | NN |
| options | JSONB | Các lựa chọn (câu trắc nghiệm) |
| correct_answer | TEXT | NN |
| accepted_answers | JSONB | NN `[]`: các cách viết tương đương (US-NH-47) |
| explanation | TEXT | |
| vocab_entry_id | BIGINT | FK vocab_entries SET NULL (câu về từ đã lưu) |
| target_kind | VARCHAR(8) | NN, CHECK `saved`/`related`: từ đã lưu hay từ mở rộng (F09.09) |
| term | VARCHAR(32) | NN: từ được hỏi (dùng cho từ mở rộng chưa có mục từ) |
| related_entry_id | BIGINT | FK vocab_entries SET NULL: từ đã lưu làm cầu nối cho gợi ý của từ mở rộng |
| example_id | BIGINT | FK dict_examples SET NULL: câu ví dụ dùng cho câu hỏi |
| hint | TEXT | Gợi ý nối với từ đã biết hoặc âm Hán Việt (câu từ mở rộng) |
| origin | VARCHAR(12) | NN, CHECK `llm`/`fallback` |
| user_answer | TEXT | |
| is_correct | BOOLEAN | |
| mistake_review | JSONB | Nội dung "Vì sao sai?" (F09.10, GĐ6): giải thích, điểm khác với đáp án đúng, câu luyện 4 lựa chọn, `origin` `llm`/`fallback`. NULL khi chưa ai mở. Lưu để mở lại không gọi lại LLM |
| mistake_review_at | TIMESTAMPTZ | Thời điểm tạo `mistake_review`; dùng đếm hạn mức |

Hạn mức giải thích lỗi sai mỗi ngày (F09.10, riêng, không chung với đề LLM): đếm các `quiz_questions` có `mistake_review ->> 'origin' = 'llm'` và `mistake_review_at` trong ngày, nối `quizzes.user_id` của người dùng; khóa `mistake_review_daily_limit` trong `system_settings`. Không cần bảng riêng. Câu luyện không lưu đáp án chọn và không ghi `review_logs`.

Hạn mức số đề LLM mỗi ngày: đếm `quizzes` có `source <> 'fallback'` của người dùng trong ngày; đề dự phòng không tốn phí nên không tính. Hết hạn mức thì vẫn tạo đề dự phòng với `fallback_reason = 'daily_limit'`. Không cần bảng riêng.

### 4.14 M10 Gợi ý từ — GĐ5

Không có bảng thống kê từ theo chương: danh sách gợi ý (F10.01) và ứng viên từ mở rộng (F09.09) được tính khi gọi từ `bubbles.tokens` của các trang trong chương (bảng `chapter_vocab` trước đây bị bỏ, cập nhật 25/10/2026).

**`dismissed_suggestions`**: PK `(user_id, term)` · dismissed_at NN (F10.03). Việc bỏ qua áp dụng cho mọi chương nên không có `chapter_id`. Danh sách gợi ý tính khi người dùng yêu cầu, không lưu sẵn (theo SRS).

### 4.15 M12 Thống kê — GĐ6

**`daily_activities`**: PK `(user_id, activity_date DATE)` theo múi giờ người học · reviews_count INTEGER NN · pages_read INTEGER NN · words_saved INTEGER NN · quizzes_done INTEGER NN · study_seconds INTEGER NN · updated_at. Dùng để tính chuỗi ngày học (F12.02) và biểu đồ (F12.01). Các use case tăng bộ đếm trong cùng giao dịch với hành động.

F12.04 (trang chủ "Hôm nay nên học gì", GĐ6) **không thêm bảng**: danh sách việc được tính khi gọi từ `cards` (thẻ đến hạn, độ nhớ R), `reading_progress`, `page_reads` và `user_settings.weekly_page_goal` (mục tiêu tuần), `vocab_entries`, `bubbles.tokens` (từ gợi ý). Ở GĐ6 chức năng không gọi LLM (câu nhắc theo mẫu). Nếu về sau bật tùy chọn Gemini viết lại câu nhắc có cache theo ngày thì sẽ cần cột hoặc bảng cache riêng; khi đó phải đề xuất và xin duyệt thêm.

### 4.16 M13 Quản trị (phần còn lại) — GĐ6

**`system_settings`**: key VARCHAR(48) PK · value JSONB NN · updated_by FK users SET NULL · updated_at. Các khóa ban đầu: `llm_enabled`, `tts_enabled`, `quiz_daily_llm_limit` (F13.05). Các khóa bổ sung ngày 25/10/2026, không cần bảng mới: `ai_note_daily_limit` (F08.11), `maintenance_mode`, `auto_moderation_enabled`, `ocr_on_upload_enabled`, `admin_notifications_enabled` (F13.05, mở rộng); `legal_terms`, `legal_privacy` (F13.08; value là JSON gồm `content`, `version`, `effective_date`); `sample_page_id` (F04.16, trang mẫu do quản trị chọn). Hạn mức Thẻ mở rộng AI ở GĐ5 đọc từ `Settings`, chuyển sang khóa `ai_note_daily_limit` ở GĐ6. Khóa bổ sung 25/10/2026, không cần bảng mới: `grammar_daily_limit` (F05.09), `mistake_review_daily_limit` (F09.10).

Danh sách khóa cấu hình hiện hành của F13.05 (11 khóa, kiểm kiểu và khoảng trong `admin/domain/system_settings.py`): `llm_enabled`, `tts_enabled` (BOOL); `quiz_daily_llm_limit`, `ai_note_daily_limit`, `grammar_daily_limit`, `mistake_review_daily_limit` (số nguyên 0 đến 1000); `maintenance_mode`, `auto_moderation_enabled`, `ocr_on_upload_enabled`, `admin_notifications_enabled` (BOOL); `sample_page_id` (số nguyên dương hoặc null). **Khóa chưa có dòng trong bảng dùng giá trị mặc định lấy từ cấu hình máy chủ** (`Settings`/`.env`; riêng hạn mức ngữ pháp mặc định 30 và giải thích lỗi sai mặc định 20 là hằng số có tên ở domain; bảo trì tắt, kiểm duyệt tự động bật, OCR khi tải bật, thông báo quản trị bật, không có trang mẫu); chỉ khi quản trị viên lưu mới có dòng. Bộ đệm trong tiến trình vài giây, bị xóa ngay khi lưu. `ocr_on_upload_enabled` đã lưu được nhưng **chưa có tác dụng** (chờ duyệt: cần trạng thái bản dịch mới và migration). Khóa `legal_terms`, `legal_privacy` của F13.08 không thuộc 11 khóa này (GĐ6.6). **Bổ sung GĐ6.5 (F17.04, không cần bảng hay migration):** 4 khóa hạn mức VIP `vip_quiz_daily_llm_limit` (mặc định 10), `vip_ai_note_daily_limit` (40), `vip_grammar_daily_limit` (60), `vip_mistake_review_daily_limit` (40), số nguyên 0 đến 1000; tổng 15 khóa. Mặc định đặt trong `Settings`/`.env`. Cách đếm lượt đã dùng không đổi (mục 4.8, 4.11, 4.13).

**`content_removals`**: id PK · file_id FK stored_files SET NULL · page_id FK pages SET NULL · reason VARCHAR(500) NN · removed_by FK users SET NULL · created_at (F13.04). Gỡ ảnh còn đặt `stored_files.removed_at` cho ảnh gốc, ảnh đã xóa chữ, ảnh đã dịch và ảnh ngữ cảnh (`snippet`) cắt từ ảnh đó; từ và thẻ không bị xóa. **Cờ kiểm duyệt tự động không có bảng**: tính khi liệt kê từ `stored_files` (chiều rộng, chiều cao, `sha256`) và trạng thái bản dịch `failed`, theo ngưỡng cạnh ngắn dưới 200 px, cạnh dài trên 12000 px.

### 4.17 M14 Phản hồi & Thông báo — GĐ6

**`error_reports`**: (F14.01, F14.02)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| id | BIGINT | PK |
| reporter_id | BIGINT | FK users CASCADE, NN, IX |
| page_id | BIGINT | FK pages SET NULL |
| bubble_id | BIGINT | FK bubbles SET NULL |
| report_type | VARCHAR(16) | NN, CHECK `ocr`/`translation`/`other` |
| description | VARCHAR(1000) | NN |
| status | VARCHAR(12) | NN, CHECK `new`/`resolved`/`rejected`, IX |
| resolution_note | VARCHAR(1000) | |
| handled_by | BIGINT | FK users SET NULL |
| handled_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | NN |

**`notifications`**: id PK · user_id FK users CASCADE NN · kind VARCHAR(24) NN (hiện có `reminder`, `report_resolved`, `report_rejected`, `content_removed`; GĐ6.5 thêm `season_reward`, `achievement_unlocked`, `streak_milestone`, `vip_granted`, `vip_expiring`, `wallet_adjusted`, không cần migration vì cột không có CHECK) · title VARCHAR(200) NN · body TEXT · channel VARCHAR(8) CHECK `in_app`/`email` · status VARCHAR(8) CHECK `pending`/`sent`/`failed` · **data JSONB NN mặc định `{}`** · read_at · created_at · sent_at. IX `(user_id, read_at)`, `(user_id, created_at)`.

`data` (F14.05, F14.06) là đích điều hướng và số liệu đi kèm để chuông thông báo mở đúng màn hình khi bấm: thông báo báo lỗi có `report_id`, `page_id`, `status`; thông báo nhắc ôn có `due_cards`. Hộp thông báo (F14.06) chỉ đọc các dòng `channel = in_app` của chính người dùng, tính số chưa đọc bằng `read_at IS NULL` nhờ chỉ mục `(user_id, read_at)`; không thêm bảng nào khác.

**`reminder_logs`**: PK `(user_id, reminder_date DATE)` · sent_at NN. Chống gửi nhắc hai lần trong một ngày (F14.04).

### 4.18 M16 Gamification — GĐ6.5

Đặc tả bảng XP, mùa thi đua, huy hiệu bổ sung ngày 30/10/2026 (F16.02–F16.12, đã triển khai 31/10/2026); bảng của mini-game đã duyệt 25/10/2026. Cả sáu bảng của M16 (gồm `minigame_sessions`) tạo trong **migration 0012** (`0012_gd65_gamification`), kèm cột `user_settings.show_on_leaderboard` và dữ liệu khởi tạo 7 dòng của `achievements`.

Cân nhắc khi thiết kế (vì sao **không** có bảng nhiệm vụ, mục tiêu tuần, bảng xếp hạng):
- Nhiệm vụ ngày (F16.04) là 3 hằng số trong domain; tiến độ đọc thẳng từ `daily_activities` (đã có, cập nhật cùng giao dịch với hành động). Việc "đã thưởng nhiệm vụ X ngày D" chính là sự tồn tại của dòng `xp_events (source='quest', source_ref='read_pages:2026-10-30')`, nên bảng `quest_definitions`/`user_quest_progress` là thừa.
- Mục tiêu tuần (F16.05) lấy mục tiêu từ `user_settings.weekly_page_goal`, tiến độ từ tổng `daily_activities.pages_read`, đã thưởng là dòng `xp_events (source='weekly_goal')`.
- Bảng xếp hạng (F16.07) tính khi gọi bằng `SUM` trên `xp_events` hoặc `daily_activities` theo khoảng thời gian; chỉ kết quả **đã chốt** của mùa mới lưu (`season_results`), vì đó là căn cứ trao thưởng không được đổi.

**`xp_events`** (F16.02, sổ cái XP chỉ thêm; không UPDATE, không DELETE trừ khi xóa tài khoản)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | |
| source | VARCHAR(20) | NN, CHECK `page_read`/`review`/`word_saved`/`quiz`/`minigame`/`quest`/`weekly_goal`/`streak_milestone` | |
| source_ref | VARCHAR(64) | NN | Mã trang, mã lượt ôn, từ, mã bài, mã ván; `read_pages:<ngày>`; ngày đầu tuần; `<mốc>:<ngày bắt đầu chuỗi>` |
| amount | SMALLINT | NN, CHECK `amount BETWEEN 0 AND 1000` | XP thực nhận sau khi áp trần (có thể 0) |
| capped | BOOLEAN | NN, mặc định false | Bị cắt vì trần ngày |
| activity_date | DATE | NN | Ngày theo múi giờ Người học: tính trần ngày và nhiệm vụ |
| created_at | TIMESTAMPTZ | NN | Thời điểm máy chủ ghi nhận: quyết định sự kiện thuộc mùa nào |

UQ `(user_id, source, source_ref)`: **chống cộng trùng** (idempotent), gửi lại cùng sự kiện thì `INSERT … ON CONFLICT DO NOTHING`. IX `(created_at, user_id)` để tính bảng xếp hạng tuần/tháng/mùa; IX `(user_id, activity_date)` cho trần ngày, XP hôm nay và nhiệm vụ. Mọi truy vấn cá nhân lọc `user_id`.

**`seasons`** (F16.09, F16.10)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| number | INTEGER | NN, UQ, CHECK `number >= 1` | "Kỳ N", tăng dần |
| starts_at | TIMESTAMPTZ | NN, UQ | Thứ Hai 00:00 giờ Việt Nam (lưu UTC: Chủ Nhật 17:00 UTC); UQ chống hai yêu cầu cùng tạo một mùa |
| ends_at | TIMESTAMPTZ | NN, CHECK `ends_at > starts_at` | Mốc loại trừ: Thứ Hai kế tiếp 00:00 giờ Việt Nam; sự kiện có `created_at < ends_at` thuộc mùa |
| status | VARCHAR(12) | NN, CHECK `active`/`finalizing`/`finalized`, mặc định `active` | IX `(status, ends_at)` cho tác vụ chốt |
| finalized_at | TIMESTAMPTZ | | |
| created_at | TIMESTAMPTZ | NN | |

**`season_results`** (F16.10; chỉ top 50 đủ điều kiện)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| season_id | BIGINT | PK (thành phần), FK seasons CASCADE | |
| user_id | BIGINT | PK (thành phần), FK users CASCADE, IX | Lịch sử mùa của tôi (F16.09) |
| rank | SMALLINT | NN, CHECK `rank BETWEEN 1 AND 50` | UQ `(season_id, rank)` |
| xp | INTEGER | NN, CHECK `xp >= 0` | XP trong mùa lúc chốt |
| tier | VARCHAR(8) | NN, CHECK `top3`/`top10`/`top50` | |
| reward_granted_at | TIMESTAMPTZ | | NULL = chưa trao xong; tác vụ chạy lại chỉ xử lý dòng NULL |
| created_at | TIMESTAMPTZ | NN | |

PK `(season_id, user_id)` bảo đảm mỗi người một kết quả mỗi mùa; kết hợp khóa `season:<mã mùa>` ở `wallet_ledger` để không trao thưởng hai lần.

**`achievements`** (F16.11; danh mục huy hiệu, dữ liệu khởi tạo trong migration)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| code | VARCHAR(32) | NN, UQ | `sakura_member`, `top_scholar`, `manhua_elite`, `seed_sower`, `hsk3_master`, `night_owl`, `apprentice_translator` |
| name | VARCHAR(64) | NN | Tên tiếng Việt khớp `data/achievements.ts` |
| description | VARCHAR(255) | NN | |
| metric | VARCHAR(24) | NN, CHECK `study_days`/`pages_read`/`words_saved`/`hsk3_mastered`/`night_pages`/`bubble_lookups`/`season_top3` | Chỉ số dùng để mở khóa |
| thresholds | INTEGER[] | NN, CHECK `cardinality(thresholds) BETWEEN 1 AND 3` | Ngưỡng cấp I/II/III tăng dần (kiểm thứ tự ở tầng ứng dụng) |
| coin_rewards | INTEGER[] | NN | Xu thưởng từng cấp, cùng số phần tử với `thresholds` |
| style_key | VARCHAR(32) | NN | Biểu tượng và màu viết sẵn ở giao diện |
| sort_order | SMALLINT | NN, mặc định 0 | |
| is_active | BOOLEAN | NN, mặc định true | |
| created_at, updated_at | TIMESTAMPTZ | NN | |

**`user_achievements`** (F16.11, F16.12)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| user_id | BIGINT | PK (thành phần), FK users CASCADE | |
| achievement_id | BIGINT | PK (thành phần), FK achievements RESTRICT | Không xóa định nghĩa đã có người đạt (chỉ tắt `is_active`) |
| tier | SMALLINT | NN, CHECK `tier BETWEEN 1 AND 3` | Cấp cao nhất đã đạt; không giảm |
| source | VARCHAR(8) | NN, CHECK `rule`/`season` | Mở khóa theo luật hay do thưởng mùa |
| is_equipped | BOOLEAN | NN, mặc định false | UQ một phần `(user_id) WHERE is_equipped`: mỗi người tối đa một huy hiệu đang đeo |
| unlocked_at | TIMESTAMPTZ | NN | Lần đầu đạt cấp I |
| tier_reached_at | TIMESTAMPTZ | NN | Lần lên cấp gần nhất |

Chỉ số của huy hiệu tính khi đánh giá, không lưu: `study_days` đếm dòng `daily_activities` có `reviews_count + pages_read > 0`; `pages_read` đếm `page_reads`; `words_saved` đếm `vocab_entries`; `hsk3_mastered` đếm `vocab_entries` có `hsk_level = 3` và (`status = 'known'` hoặc có `cards.state = 'review'` với `stability >= 21`); `night_pages` đếm `page_reads` có giờ địa phương của `first_read_at` (theo `user_settings.timezone`) trong 23:00–03:59; `bubble_lookups` đếm `DISTINCT bubble_id` của `lookup_events` hành động `hover`/`lookup`. Xu của mỗi cấp ghi vào `wallet_ledger` với khóa `achievement:<mã>:<cấp>`.

**`minigame_sessions`** (F16.01, US-NH-81): mỗi ván mini-game. Bộ thủ yếu được tính khi gọi từ `review_logs` (rating 1–2) nối `cards`, `vocab_entries` và `hanzi.radical`/`components`, nên không lưu bảng thống kê riêng.

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | |
| game_type | VARCHAR(24) | NN, CHECK `falling_radical` | Loại mini-game; thêm giá trị khi có game mới |
| target_radical | VARCHAR(8) | NN | Bộ thủ hoặc thành phần mục tiêu |
| score | SMALLINT | NN | Điểm do máy chủ tính lại |
| correct | SMALLINT | NN | Số lần chọn đúng |
| wrong | SMALLINT | NN | Số lần chọn sai |
| duration_ms | INTEGER | NN | Thời gian chơi thực tế, máy chủ giới hạn hợp lý |
| played_at | TIMESTAMPTZ | NN | IX `(user_id, played_at)` |

**`minigame_rounds`** (F16.01, migration `0014_gd65_minigame_rounds`; bổ sung 31/10/2026): lượt do máy chủ phát, chống tự dựng bộ chữ và nộp lại. id UUID PK · user_id FK users CASCADE, NN · radical VARCHAR NN · chars VARCHAR(8)[] NN (bộ chữ đã phát) · issued_at TIMESTAMPTZ NN · submitted_at TIMESTAMPTZ (NULL = chưa nộp). IX `(user_id, issued_at)`. Dòng cũ hơn 7 ngày do tác vụ `purge_minigame_rounds` dọn. Bảng này là thứ 57 của hệ thống. Migration `0015_gd65_pinyin_blade` bổ sung cho game gõ pinyin: `minigame_rounds` thêm `mode` (`hsk`/`weak_radical`), `hsk_band` (1–7), `items` JSONB (bộ mục kèm đáp án), `radical` được NULL, bỏ cột `chars`; `minigame_sessions` thêm `game_type = 'pinyin_blade'`, `hsk_band`, `max_combo`, `typos`, `target_radical` được NULL.

XP của ván chơi ghi vào `xp_events` (`source = 'minigame'`, `source_ref` = `minigame_sessions.id`) trong cùng giao dịch lưu ván (F16.01 bước 6, F16.02). Ván chơi không cộng xu.

### 4.19 M17 VIP & Phần thưởng — GĐ6.5

Đặc tả bổ sung ngày 30/10/2026 (F17.01–F17.10, đã triển khai 31/10/2026). Bảy bảng tạo trong **migration 0013** (`0013_gd65_vip_rewards`), kèm cột `series.is_vip` và dữ liệu khởi tạo 5 khung (`avatar_frames`) và 5 món đổi thưởng (`reward_items`). **Không có bảng thanh toán, thẻ hay giao dịch tiền** (người dùng chốt 30/10/2026). Đã cân nhắc tách `coin_ledger` và `vip_grants` thành hai bảng như gợi ý ở mục 6.3, nhưng gộp thành một sổ `wallet_ledger` có cột loại (`currency`) vì ba loại (xu, vé, ngày VIP) có cùng vòng đời, cùng khóa chống trùng và thường được trao cùng nhau trong một gói thưởng.

**`wallets`** (F17.01–F17.03, F17.08; quan hệ 1–1 với `users`, tạo khi người dùng nhận phần thưởng đầu tiên)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| user_id | BIGINT | PK, FK users CASCADE | |
| coin_balance | INTEGER | NN, mặc định 0, CHECK `coin_balance >= 0` | Xu Sakura; không bao giờ âm |
| ticket_balance | SMALLINT | NN, mặc định 0, CHECK `ticket_balance BETWEEN 0 AND 99` | Vé đọc truyện VIP |
| vip_until | TIMESTAMPTZ | | NULL = chưa từng VIP; đang VIP khi `vip_until > now` (tính khi hỏi, không có job đổi trạng thái). IX `(vip_until) WHERE vip_until IS NOT NULL` cho tác vụ nhắc |
| vip_reminded_for | TIMESTAMPTZ | | Giá trị `vip_until` đã được nhắc sắp hết hạn (F17.03); khác `vip_until` thì nhắc lại |
| equipped_frame_id | BIGINT | FK avatar_frames SET NULL | Khung đang đeo; khi hiển thị chỉ dùng nếu còn hiệu lực |
| created_at, updated_at | TIMESTAMPTZ | NN | |

Mọi thay đổi số dư khóa dòng ví bằng `SELECT … FOR UPDATE` trong cùng giao dịch với dòng sổ (Unit of Work).

**`wallet_ledger`** (F17.01; sổ chỉ thêm)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | |
| currency | VARCHAR(8) | NN, CHECK `coin`/`ticket`/`vip_days` | |
| amount | INTEGER | NN, CHECK `amount <> 0` | Dương là nhận, âm là tiêu/thu |
| balance_after | INTEGER | | Số dư sau (xu, vé); NULL với `vip_days` |
| vip_until_after | TIMESTAMPTZ | | Hạn VIP sau (chỉ `vip_days`) |
| reason | VARCHAR(20) | NN, CHECK `season_reward`/`quest_bonus`/`streak_milestone`/`achievement`/`welcome`/`redemption`/`vip_unlock`/`admin_adjust` | |
| idempotency_key | VARCHAR(80) | NN | `season:<id>`, `quests_all:<ngày>`, `<mốc>:<ngày>`, `achievement:<mã>:<cấp>`, `welcome`, mã yêu cầu UUID, `admin:<request_id>` |
| note | VARCHAR(500) | | Lý do của Quản trị viên |
| actor_id | BIGINT | FK users SET NULL | Quản trị viên thực hiện (F17.10); NULL với phần thưởng tự động |
| created_at | TIMESTAMPTZ | NN | |

UQ `(user_id, currency, idempotency_key)`: một gói thưởng có thể có nhiều loại nhưng mỗi loại chỉ ghi một lần. IX `(user_id, created_at)` cho lịch sử ví (phân trang).

**`vip_unlocks`** (F17.06): PK `(user_id, series_id)` · user_id FK users CASCADE · series_id FK series CASCADE, IX · source VARCHAR(8) NN CHECK `ticket`/`admin` · unlocked_at TIMESTAMPTZ NN. Mở khóa vĩnh viễn, không phụ thuộc `wallets.vip_until`.

**`avatar_frames`** (F17.08; danh mục khung, dữ liệu khởi tạo)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| code | VARCHAR(32) | NN, UQ | `sakura_gold`, `spring_petal`, `vip_sakura`, `bamboo_leaf`, `ink_cloud` |
| name | VARCHAR(64) | NN | "Hoa Anh Đào Vàng", "Cánh Hoa Mùa Xuân", "Khung VIP Hoa Anh Đào", "Lá Trúc Xanh", "Mây Mực" |
| description | VARCHAR(255) | | Cách kiếm |
| style_key | VARCHAR(32) | NN | Kiểu hiển thị viết sẵn ở giao diện, không phải tệp ảnh |
| acquire_kind | VARCHAR(8) | NN, CHECK `season`/`shop`/`vip` | `season` = thưởng mùa/mục tiêu tuần (không bán); `vip` = dùng khi đang VIP, không cần sở hữu |
| is_active | BOOLEAN | NN, mặc định true | |
| created_at | TIMESTAMPTZ | NN | |

**`user_frames`** (F17.01, F17.08): PK `(user_id, frame_id)` · user_id FK users CASCADE · frame_id FK avatar_frames RESTRICT · source VARCHAR(12) NN CHECK `season`/`weekly_goal`/`redemption`/`admin` · acquired_at TIMESTAMPTZ NN · expires_at TIMESTAMPTZ (NULL = vĩnh viễn; khung từ mục tiêu tuần có hạn 7 ngày, nhận lại thì gia hạn tới mốc muộn hơn; đã vĩnh viễn thì không đổi thành có hạn).

**`reward_items`** (F17.07, F17.09; danh mục cửa hàng do Quản trị viên cấu hình)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| code | VARCHAR(32) | NN, UQ | `vip_1d`, `vip_7d`, `vip_ticket`, `frame_bamboo`, `frame_ink` |
| name | VARCHAR(100) | NN | |
| description | VARCHAR(255) | | |
| kind | VARCHAR(12) | NN, CHECK `vip_days`/`vip_ticket`/`avatar_frame` | |
| price_coins | INTEGER | NN, CHECK `price_coins BETWEEN 1 AND 100000` | Mặc định 120 / 700 / 300 / 800 / 800 |
| vip_days | SMALLINT | CHECK `vip_days BETWEEN 1 AND 365` | Có khi `kind = 'vip_days'` |
| ticket_count | SMALLINT | CHECK `ticket_count BETWEEN 1 AND 10` | Có khi `kind = 'vip_ticket'` |
| frame_id | BIGINT | FK avatar_frames RESTRICT | Có khi `kind = 'avatar_frame'`; chỉ khung `acquire_kind = 'shop'` (kiểm ở ứng dụng) |
| per_user_limit | SMALLINT | CHECK `per_user_limit >= 1` | NULL = không giới hạn |
| is_active | BOOLEAN | NN, mặc định true | Ngừng bán thay cho xóa |
| sort_order | SMALLINT | NN, mặc định 0 | |
| updated_by | BIGINT | FK users SET NULL | |
| created_at, updated_at | TIMESTAMPTZ | NN | |

CHECK nhất quán theo loại: `(kind = 'vip_days') = (vip_days IS NOT NULL)`, `(kind = 'vip_ticket') = (ticket_count IS NOT NULL)`, `(kind = 'avatar_frame') = (frame_id IS NOT NULL)`.

**`reward_redemptions`** (F17.07)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| id | BIGINT | PK | |
| user_id | BIGINT | FK users CASCADE, NN | |
| item_id | BIGINT | FK reward_items RESTRICT, NN | Không xóa món đã có lượt đổi |
| price_coins | INTEGER | NN, CHECK `price_coins > 0` | Giá tại thời điểm đổi |
| request_id | UUID | NN | Chống bấm đúp; cũng là `idempotency_key` của dòng sổ trừ xu |
| created_at | TIMESTAMPTZ | NN | |

UQ `(user_id, request_id)`. IX `(user_id, item_id)` để đếm giới hạn mỗi người; IX `(user_id, created_at)`.

Quyền đọc truyện VIP (F17.05) không cần bảng mới: suy ra từ `series.is_vip`, `chapters.is_trial`, `users.role`, `wallets.vip_until` và `vip_unlocks`. Hạn mức AI theo VIP (F17.04) dùng 4 khóa mới trong `system_settings` (mục 4.16), không thêm bảng. Thao tác quản trị (F17.09, F17.10) ghi `admin_audit_logs` với `action` `series.vip_changed`, `reward_item.created`, `reward_item.updated`, `rewards.vip_granted`, `rewards.vip_revoked`, `rewards.wallet_adjusted`.

## 5. Thay đổi so với thiết kế cũ (`ptud_db`)

| Bản cũ | Bản mới | Lý do |
|---|---|---|
| `user_vocab` | `vocab_entries` + thêm `pinyin`, `meaning_vi`, `hsk_level`, `hsk_source` | Đặt tên theo quy ước; lưu bản sao để sổ tay không phụ thuộc từ điển; HSK theo F06.08 |
| `flashcards` (SM-2) | `cards` (FSRS) | Thuật toán đã chốt là FSRS |
| `review_logs` (SM-2) | thêm S/D trước và sau, `presentation_id` | FSRS và chống gửi trùng |
| `users.is_active` | `status` + `locked_reason`, `locked_at` | US-QT-03 cần lưu lý do khóa |
| `user_settings` | thêm `tts_rate`, `show_xianxia`, nhắc ôn, `timezone`; bỏ `daily_new_cards`, `daily_review_cap`, `show_pinyin` | Theo M02/M11/M14; ba cột bỏ đi không có trong user story |
| `dict_entries.hsk_level` | bảng `hsk_words` | Nguồn HSK riêng, nạp lại được |
| `translations` | thêm cột hàng đợi (`attempts`, `worker_id`, `error_step`, `queued_at`, `started_at`) | Worker riêng, `SKIP LOCKED` |
| `vocab_suggestions` | bỏ; thay bằng `dismissed_suggestions` | SRS: gợi ý tính khi yêu cầu |
| — | thêm `password_reset_tokens`, `admin_audit_logs`, `hsk_words`, `page_reads`, `guest_sessions`, `scheduled_jobs`, `job_runs`, `fsrs_parameters`, `external_call_logs`, `quizzes`, `quiz_questions`, `dismissed_suggestions`, `daily_activities`, `system_settings`, `content_removals`, `error_reports`, `notifications`, `reminder_logs` | Các chức năng mới trong SRS |

## 6. Đối chiếu với giao diện React (`frontend/frontend-YingHua`)

Giao diện hiện dùng toàn dữ liệu giả (mock), chưa gọi API nào. Đối chiếu từng màn hình với thiết kế ở trên:

### 6.1 Đã có trong thiết kế lõi, không cần thêm bảng

| Giao diện | Bảng / cách lấy |
|---|---|
| Catalog: tìm kiếm, lọc theo HSK, số chương | `series` (`title_vi`, `title_zh`, `est_hsk_level`), đếm `chapters` |
| Tiến độ truyện (trang x/y, %), "Đọc tiếp" | `reading_progress` + đếm `pages` |
| Số từ đã lưu theo truyện; bộ thẻ Flashcard theo truyện (F08.10) | `vocab_contexts` → `pages` → `chapters` → `series` |
| Ảnh đã tải lên để dịch | `pages` có `chapter_id` NULL, `translations.status` |
| Flashcard: trạng thái "Đã thuộc / Đang học / Cần ôn lại" | `vocab_entries.status` (`known` = Đã thuộc) và `cards.due_at <= now` (= Cần ôn lại) |
| Flashcard: 4 nút đánh giá, phím 1–4 | `cards` + `review_logs` (FSRS tính khoảng cách thật, thay cho các mốc cố định 10 phút / 1 / 3 / 7 ngày) |
| Câu ví dụ trên thẻ | `vocab_contexts.sentence_zh/vi`, `dict_examples` |
| Hồ sơ: chuỗi ngày học, số từ, số trang, số giờ học | `daily_activities`, `vocab_entries`, `page_reads`, tổng `study_seconds` |
| Đọc truyện: bong bóng, hover, phát âm, đọc cả trang | `bubbles` (tọa độ pixel đổi sang %), `tts_cache` |
| Admin: người dùng, khiếu nại, cài đặt hệ thống | `users`, `error_reports`, `system_settings` |
| Đổi email, đổi mật khẩu | `users` (đổi email có kiểm tra mật khẩu hiện tại) |

### 6.2 Đề xuất thêm: nhỏ, chỉ phục vụ giao diện (cần duyệt)

| Thêm | Phục vụ |
|---|---|
| `users.avatar_file_id` (FK stored_files), `users.chinese_name VARCHAR(32)`, `users.show_email BOOLEAN`, `users.show_join_date BOOLEAN` | Hồ sơ, chỉnh sửa hồ sơ, quyền riêng tư |
| `user_settings.learning_goal` CHECK `study`/`entertainment`/`both`, `user_settings.weekly_page_goal SMALLINT` | Form đăng ký, mục tiêu tuần |
| `series.genres VARCHAR(32)[]` | Thể loại trên thẻ truyện |
| Bảng `library_items`: PK `(user_id, series_id)`, `is_favorite BOOLEAN`, `added_at` | "Lưu vào Thư viện", tab Yêu thích |
| `vocab_entries.is_starred BOOLEAN` | Đánh dấu sao từ, bộ thẻ "Từ đánh dấu sao" (đã đưa vào SRS: F07.09, F08.10; US-NH-66, US-NH-67) |
| Bảng `page_annotations`: PK `(user_id, page_id)`, `highlights JSONB`, `strokes JSONB`, `is_bookmarked BOOLEAN`, `updated_at` | Bút ghi chú, tô màu bong bóng, lưu trang. Hiện các dữ liệu này nằm trong localStorage. |

### 6.3 Có trên giao diện nhưng KHÔNG có trong SRS (cần quyết định phạm vi)

| Tính năng | Nếu làm thì cần |
|---|---|
| XP, nhiệm vụ hằng ngày (+20/+15/+30 XP) | Đã đưa vào SRS ngày 30/10/2026: F16.02, F16.04 (US-NH-84, US-NH-85); bảng `xp_events`, **không** có `daily_quests` (tiến độ tính từ `daily_activities`, mục 4.18) |
| Bảng xếp hạng theo tuần / tháng / mùa | Đã đưa vào SRS ngày 30/10/2026: F16.07–F16.10 (US-NH-88 … US-NH-90, US-HG-05); tính từ `xp_events` + `daily_activities`; bảng `seasons`, `season_results` |
| Huy hiệu / thành tích (7 loại) | Đã đưa vào SRS ngày 30/10/2026: F16.11, F16.12 (US-NH-91, US-NH-92); bảng `achievements`, `user_achievements` |
| VIP, xu, phần thưởng | Đã đưa vào SRS ngày 30/10/2026: M17, F17.01–F17.10 (US-NH-93 … US-NH-99, US-QT-17, US-QT-18, US-HG-06). **Không phải nghiệp vụ thanh toán**: người dùng chốt không dùng tiền thật, nên không có `subscriptions`; thay bằng `wallets`, `wallet_ledger`, `vip_unlocks`, `avatar_frames`, `user_frames`, `reward_items`, `reward_redemptions` (mục 4.19) |
| Chấm sao truyện | `series_ratings` (đã đưa vào SRS: F03.14, US-NH-62; xem mục 4.6) |
| Tác giả / cộng đồng gửi bài chờ duyệt | Quy trình kiểm duyệt nội dung cộng đồng (lớn) |
| Mục ngữ pháp trên trang | Đã đưa vào SRS ngày 25/10/2026: F05.09 (US-NH-78), LLM sinh theo lược đồ cố định; bảng `grammar_analyses`, `grammar_requests` (mục 4.8) |
| Đăng nhập Google / WeChat / Apple | OAuth với bên thứ ba |

**Quyết định (23/10/2026):** thêm toàn bộ mục 6.2, tạo theo giai đoạn như sau:
- GĐ1: các cột mới của `users`, cùng `learning_goal` và `weekly_page_goal`.
- GĐ3: `series.genres`, `library_items`, `page_annotations` (cùng `series_ratings`, mục 4.6), tạo trong **migration 0005**.
- GĐ4: `vocab_entries.is_starred`.

## 8. Tính năng giao diện ngoài SRS (chốt lại 23/10/2026: **làm hết, không bỏ**)

Mọi tính năng đang có trên giao diện React đều được hiện thực, theo module và giai đoạn. Không xóa phần giao diện nào; phần nào chưa đến giai đoạn thì tạm giữ dữ liệu giả cho đến khi được nối.

| Tính năng giao diện | Module mở rộng | Giai đoạn |
|---|---|---|
| Từ vựng trong ngày (Catalog), ô tìm kiếm trên Navbar | M06 (thêm chức năng) | GĐ2 |
| Đánh giá (chấm sao) truyện | M03, **đã đưa vào SRS: F03.14 (US-NH-62)** | GĐ3 |
| Thư viện cá nhân và yêu thích | M03, **đã đưa vào SRS: F03.13 (US-NH-61)** | GĐ3 |
| Lưu (đánh dấu) trang | M05, **đã đưa vào SRS: F05.07 (US-NH-63)** | GĐ3 |
| Ghi chú vẽ và tô màu bong bóng trên trang | M05, **đã đưa vào SRS: F05.08 (US-NH-64)** | GĐ3 |
| Mục ngữ pháp trên trang (grammar spotlight, khối "Cấu trúc trọng điểm") | M05, **đã đưa vào SRS: F05.09 (US-NH-78)**; bảng `grammar_analyses`, `grammar_requests` | GĐ6 (trước đây dự kiến GĐ3–5) |
| Giải thích lỗi sai và câu luyện thêm trong kết quả kiểm tra | M09, **đã đưa vào SRS: F09.10 (US-NH-79)**; cột `quiz_questions.mistake_review`, `mistake_review_at` | GĐ6 |
| Trang chủ "Hôm nay nên học gì" | M12, **đã đưa vào SRS: F12.04 (US-NH-80)**; không cần bảng mới | GĐ6 |
| Chọn nguồn đọc trong trình đọc (bộ chọn truyện riêng tư / ảnh tải lên / chương, cột trái liệt kê trang, URL khớp trang đang xem) | M05, **đã đưa vào SRS: F05.10 (US-NH-83, 30/10/2026)**; **không thêm bảng hay cột**, chỉ đọc dữ liệu hiện có (`series`, `chapters`, `pages`, `reading_progress`, ảnh tải nhanh) qua API sẵn có | GĐ6 |
| Mini-game luyện bộ thủ yếu | **M16**, **đã đưa vào SRS: F16.01 (US-NH-81)**; bảng `minigame_sessions` | GĐ6.5 |
| Trợ lý học tập dạng trò chuyện có công cụ; chấm phát âm bằng biểu đồ thanh điệu | Hướng phát triển, chỉ ghi mô tả và user story (`docs/modules-functions.md` mục 7, US-HP-01, US-HP-02); không có mã F, không có bảng | Sau GĐ6.6 |
| XP, nhiệm vụ ngày, bảng xếp hạng tuần/tháng/mùa, huy hiệu & thành tựu, mục tiêu tuần | **M16 Gamification**, **đã đưa vào SRS: F16.02–F16.12 (US-NH-84 … US-NH-92, US-HG-05; 30/10/2026)**; bảng `xp_events`, `seasons`, `season_results`, `achievements`, `user_achievements`, cột `user_settings.show_on_leaderboard` (migration 0012). Mục tiêu theo tháng không có trên giao diện hiện tại nên không đặc tả | GĐ6.5 |
| VIP, xu Sakura, phần thưởng mùa, khung avatar, truyện VIP, cửa hàng đổi thưởng | **M17 VIP & Phần thưởng**, **đã đưa vào SRS: F17.01–F17.10 (US-NH-93 … US-NH-99, US-QT-17, US-QT-18, US-HG-06; 30/10/2026)**; không thanh toán tiền thật; bảng `wallets`, `wallet_ledger`, `vip_unlocks`, `avatar_frames`, `user_frames`, `reward_items`, `reward_redemptions`, cột `series.is_vip` (migration 0013) | GĐ6.5 |
| Tác giả / cộng đồng gửi truyện, bản dịch, học liệu; hàng chờ duyệt; duyệt tác giả | **M18 Nội dung cộng đồng** | GĐ6.6 |
| Đăng nhập Google / WeChat / Apple | **M19 Đăng nhập liên kết (OAuth)** | GĐ6.6 |
| Đổi email (có xác thực) | M01 (thêm chức năng) | GĐ6.6 |
| Avatar tải lên | M01 + `stored_files` (kind `avatar`, `users.avatar_file_id`), **đã đưa vào SRS: F01.10 (US-NH-65)**; chọn ảnh có sẵn: xem dòng bên dưới | GĐ3 |
| Đánh dấu sao từ trong sổ tay (`vocab_entries.is_starred`) | M07, **đã đưa vào SRS: F07.09 (US-NH-66)** | GĐ4 |
| Bộ thẻ Flashcard theo truyện và bộ "Từ đánh dấu sao" | M08 (đọc dữ liệu M07, M03), **đã đưa vào SRS: F08.10 (US-NH-67)** | GĐ4 |
| Âm Hán Việt trên mục từ và mặt sau thẻ | M07 (đọc dữ liệu M06), **đã đưa vào SRS: F07.10 (US-NH-68)** | GĐ4 |
| Danh sách "Câu thoại đã lưu" ở Hồ sơ (lưu, nghe lại, mở trang gốc, ghi chú, bỏ lưu) | M07, **đã đưa vào SRS: F07.11 (US-NH-70)**; bảng `saved_sentences` | GĐ5 |
| Nút "Lưu tất cả từ của trang" | M07, **đã đưa vào SRS: F07.12 (US-NH-71)**; không cần bảng mới | GĐ5 |
| Gợi ý truyện theo trình độ ở Hồ sơ | M10, **đã đưa vào SRS: F10.04 (US-NH-72)**; không cần bảng mới | GĐ5 |
| Độ phủ từ vựng của chương ("đã nắm X/Y từ HSK n") | M10, **đã đưa vào SRS: F10.05 (US-NH-73)**; tính khi gọi từ `bubbles.tokens` | GĐ5 |
| Cỡ chữ bong bóng dịch (80–160%) | M02, **đã đưa vào SRS: F02.04 (US-NH-74)**; cột `user_settings.bubble_font_scale` | GĐ5 |
| Flashcard AI (thẻ mở rộng: ví dụ mới, mẹo chiết tự, cụm từ; LLM Google Gemini, chọn 25/10/2026) | M08, **đã đưa vào SRS: F08.11 (US-NH-75)**; bảng `vocab_ai_notes`. Hạn mức theo VIP: F17.04 (khóa `vip_ai_note_daily_limit`); "3 ngày mở khóa VIP & Flashcard AI" là quà chào mừng của F17.03 | GĐ5 (VIP: GĐ6.5) |
| Ghi nhớ đăng nhập | M01, **đã đưa vào SRS: F01.11 (US-NH-76)**; không cần bảng mới (đổi thời hạn mã làm mới và nơi lưu ở trình duyệt) | GĐ6 |
| Chọn ảnh đại diện có sẵn | M01, **mở rộng F01.10 (US-NH-65 TC6)**; thêm cột `users.avatar_preset VARCHAR(32)` (mã ảnh mặc định, loại trừ với `avatar_file_id`) | GĐ6 |
| Trang Điều khoản dịch vụ và Chính sách bảo mật do quản trị soạn | M13, **đã đưa vào SRS: F13.08 (US-QT-15)**; lưu ở `system_settings` (khóa `legal_terms`, `legal_privacy`) | GĐ6.6 |
| Cài đặt hệ thống mở rộng: chế độ bảo trì, kiểm duyệt ảnh tự động, OCR khi tải, thông báo quản trị | M13, **mở rộng F13.05 (US-QT-13 TC5–TC10)**; khóa mới trong `system_settings` | GĐ6 |
| Xuất báo cáo vi phạm (CSV) | M13, **đã đưa vào SRS: F13.09 (US-QT-16)**; đọc `error_reports`, `content_removals` | GĐ6.6 |
| Duyệt nhanh tự động hàng chờ duyệt nội dung cộng đồng | M18 (không có mã F ở SRS hiện tại; viết khi làm M18): sắp xếp hàng chờ theo kiểm tra sơ bộ bằng luật (tỉ lệ OCR thành công, ảnh trùng, kích thước); quản trị viên vẫn là người quyết định | GĐ6.6 |
| Thử với trang mẫu trước khi tải ảnh | M04, **đã đưa vào SRS: F04.16 (US-NH-77)**; dùng trang đã xử lý sẵn, khóa `sample_page_id` trong `system_settings`; không cần bảng mới | GĐ6 |
| Xáo trộn thẻ / từ | Thao tác thuần giao diện (đổi thứ tự hiển thị phía trình duyệt), không cần dữ liệu máy chủ, không có mã F | Không áp dụng |
| Tải ảnh đại diện (đã có API F01.10, giao diện chưa nối) | M01, giữ F01.10 | GĐ5 (nối giao diện) |
| Xóa ảnh tải nhanh (đã có API, giao diện chưa nối) | M03, F03.09 | GĐ5 (nối giao diện) |
| Sửa và xóa truyện, chương (đã có API, giao diện chưa nối) | M03, F03.09 | GĐ5 (nối giao diện) |
| Màn hình cài đặt người học: trình độ HSK, chế độ đọc, giọng đọc (đã có API, giao diện chưa nối) | M02, F02.01–F02.03 | GĐ5 (nối giao diện) |
| Màn hình giám sát xử lý ảnh của quản trị (đã có API, giao diện chưa nối) | M04, F04.05 | GĐ5 (nối giao diện) |
| Màn hình tác vụ nền của quản trị (đã có API, giao diện chưa nối) | M15, F15.03 | GĐ5 (nối giao diện) |

Với mỗi mục trên: **viết bổ sung user story + chức năng (F) + đặc tả bảng và trình duyệt trước khi làm**, giống 104 chức năng gốc. Cập nhật 30/10/2026 (GĐ6.5, chờ duyệt): M16 (F16.02–F16.12) và M17 (F17.01–F17.10) đưa tổng lên 151 chức năng và 144 user story, thêm 12 bảng (tổng 57 bảng) và hai cột `user_settings.show_on_leaderboard`, `series.is_vip`; migration dự kiến 0012 (M16 và `minigame_sessions`) và 0013 (M17). Cập nhật 30/10/2026: F05.10 (chọn nguồn đọc trong trình đọc, US-NH-83) đưa tổng lên 130 chức năng và 124 user story, không thêm bảng hay cột. Cập nhật 25/10/2026 (đợt AI): bốn mục F05.09, F09.10, F12.04 (GĐ6) và F16.01 (GĐ6.5) đưa tổng lên 128 chức năng và 122 user story, thêm ba bảng `grammar_analyses`, `grammar_requests`, `minigame_sessions` (tổng 44 bảng) và hai cột `quiz_questions.mistake_review`, `mistake_review_at`. Cập nhật 25/10/2026 (đợt trước): F09.09 (câu hỏi từ mở rộng, US-NH-69) đưa tổng lên 114; sau đó mười mục F07.11, F07.12, F08.11, F10.04, F10.05, F02.04 (GĐ5) và F01.11, F04.16, F13.08, F13.09 (GĐ6 đến 6.6) đưa tổng lên 124 chức năng và 118 user story, cùng hai bảng `saved_sentences`, `vocab_ai_notes` và cột `user_settings.bubble_font_scale` (GĐ5), cột `users.avatar_preset` (GĐ6). Cập nhật 24/10/2026: năm mục đã ghi "đã đưa vào SRS" làm tổng chức năng thành 109; bổ sung cùng ngày ba mục của GĐ4 (F07.09, F07.10, F08.10) đưa tổng lên 112 (xem `docs/modules-functions.md`).

## 9. Chép dữ liệu từ `ptud_db`

- **Giai đoạn 2**: viết script `server/scripts/copy_dictionaries.py` chép 4 bảng từ điển theo lô, chạy lại không nhân bản dữ liệu. `ptud_db` giữ nguyên.
- **Không chép**: người dùng thử, truyện thử, thẻ thử trong `ptud_db`. Đó chỉ là dữ liệu kiểm thử của bản cũ, và cấu trúc thẻ đã đổi từ SM-2 sang FSRS.
