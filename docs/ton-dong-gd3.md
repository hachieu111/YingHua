# Việc còn mở của Giai đoạn 3 (ghi 24/10/2026, làm sau)

GĐ3 (M03, M04, M05, M15) đã xong và chạy được (xem `docs/ke-hoach-trien-khai.md`). Các điểm dưới đây chưa làm hoặc chưa kiểm, xếp theo mức ưu tiên đề xuất. Khi làm xong một mục thì gạch bỏ hoặc xóa dòng.

## A. Nên làm sớm (ảnh hưởng đúng/sai hoặc chất lượng)
| # | Việc | Ghi chú |
|---|---|---|
| A1 | Các luật `LuatNhan.txt` cùng loại với 4 luật đã sửa | Các luật `在…` khác (dòng 113–118, 120–122, 37, 70, 71) ăn chữ `在` của `现在`; `对/跟/向…说` khớp nhầm `说明`, `说服`; `比…强/快` + `得多`; `比` khớp `比如`, `比较`, `对比`; `把…当` khớp `当然`, `当时`, `相当`; `不在`, `还在` chưa được chặn; `说话?` nuốt `话` của từ sau; nhóm `([^，。！？]+?)` có thể kéo rất xa. Làm bằng `yinghua-vision` kèm đối chiếu trước/sau trên 203 câu mẫu. |
| A2 | Tách từ jieba | `一阶术炼师` bị tách `一阶术 / 炼师`. Có thể thêm từ điển người dùng cho jieba (cần duyệt). |
| A3 | Chống xử lý ảnh trùng theo pHash (F04.14) | Hiện chỉ dùng lại bản dịch theo `sha256`. Cột `phash` mới chỉ được ghi. Hai ảnh giống nhau tải gần như cùng lúc vẫn bị xử lý riêng (chưa chống đua lúc nhận việc). |
| A4 | Hạn mức tra từ của Khách (F05.04) | Khách bỏ header `X-Guest-Session` thì lấy phiên mới và đặt lại hạn mức; chưa giới hạn theo IP. "Tra lại cùng một từ không tính thêm lượt" chưa làm (cột chỉ có bộ đếm). |
| A5 | Lọc HSK nhóm 7–9 | `GET /series?hsk=` chỉ khớp đúng một cấp; giao diện dùng chip từng cấp 1–9. |

## B. Giao diện và trải nghiệm
| # | Việc | Ghi chú |
|---|---|---|
| B1 | Xóa trang đã tải lên và "Bỏ khỏi Thư viện" ngay trên thẻ | Hàm API đã có, chưa có nút trên thẻ (bỏ khỏi Thư viện làm được trong modal chi tiết truyện). |
| B2 | Thẻ truyện ở Catalog hiện sao trung bình thay cho "N từ vựng" | Chưa có số từ theo truyện; làm khi có M07 (GĐ4). `GET /reading-progress/continue` cũng chưa trả HSK. |
| B3 | Khung bong bóng hiện luôn thay vì chỉ khi rê chuột | Chưa xác nhận đây có phải thiết kế mong muốn. |
| B4 | `ComicReader.tsx` dài khoảng 1.000 dòng | Quy tắc clean-code là ≤ ~300 dòng; nên tách panel tra từ và công cụ ghi chú ra file riêng. |
| B5 | Thẻ "Cấu trúc trọng điểm" (ngữ pháp) và "Chuỗi học 7 ngày" còn dữ liệu giả; mục tiêu tuần "75%" ghi "(số liệu minh họa)" | Ngữ pháp thuộc GĐ3–5 (M05 mở rộng); chuỗi học, mục tiêu tuần thuộc M12 (GĐ6). |
| B6 | Ảnh tải nhanh bị dọn thì trang trả 404 | SRS đã sửa cho khớp ("Không tìm thấy ảnh"); kiểm tra giao diện hiện thông báo này cho đúng. |

## C. Chưa kiểm
- Vẽ ghi chú và tô màu bong bóng trên **màn hình cảm ứng**; tô màu bong bóng, tải ảnh về, chấm sao truyện công khai mới thử qua API, chưa bấm trên giao diện.
- Ca "file của người khác trả 404" qua `GET /files/{id}` (cần tài khoản thứ hai có dữ liệu).
- Worker thật: Ctrl+C trên Windows, kịch bản model nạp lỗi, `run_due_jobs` lâu dài; test e2e `tests/integration/test_worker_e2e.py` chưa chạy lại sau khi đổi cách tạo config.
- Chưa có assert riêng cho khách gọi `GET /series?scope=public` (trường `progress` phải `null`).
- `tests/api/test_dictionary.py::test_word_of_the_day_returns_404_when_no_hsk_data` có nhánh `skip` phụ thuộc dữ liệu CSDL test.

## D. Hạ tầng, môi trường, git
| # | Việc | Ghi chú |
|---|---|---|
| D1 | `server/requirements-worker.txt` chưa dựng thử trên máy sạch | `paddleocr 2.7.0.3` khai báo cần opencv ≤ 4.6.0.66 nhưng bản đã kiểm thử là 4.8.1.78 nên phải cài 2 bước; môi trường có cả `opencv-contrib-python` và `opencv-python-headless`. |
| D2 | Reload của uvicorn trên Windows không ổn định | Reloader thấy thay đổi nhưng tiến trình cũ không tắt (kể cả với polling); tạm thời chạy không `--reload` và khởi động lại sau mỗi đợt sửa (ghi trong `server/README.md`). Cần điều tra vì sao lifespan/shutdown bị treo; các server cũ để lại tiến trình con mồ côi giữ cổng 8000. Worker chưa có supervisor tự chạy lại. |
| D3 | Trước khi commit | Thư mục `frontend/` chưa được git theo dõi (git hiện `Frontend/` ở trạng thái `??`). Các file `.pyc` trong `module xử lí ảnh/**/__pycache__/` đang được theo dõi và bị sửa, cần gỡ khỏi index. 9 file khác của module ảnh (`main.py`, `pipeline.py`, `text_renderer.py`, `typesetter.py`, `label_tool.py`, `scripts/*`) hiện bị đổi, phần lớn do kết thúc dòng, riêng `main.py` thêm khoảng 785 dòng; cần xác nhận nguồn gốc. |
| D4 | `ruff format` đã chạy trên cả `server/` | Agent chưa đối chiếu `git diff` xem file cũ nào bị format lại. |
| D5 | Dọn file mồ côi | Job `cleanup_orphan_files` đã có; chưa kiểm khi tiến trình chết giữa lúc ghi file và commit. |

---

# Việc còn mở của Giai đoạn 4 (ghi 24/10/2026, làm sau)

GĐ4 (M07 Sổ tay, M08 Ôn tập FSRS, M11 Phát âm, cùng F13.07 quản trị dữ liệu người dùng) đã chạy được. Các điểm dưới đây chưa làm hoặc chưa kiểm.

| # | Việc | Ghi chú |
|---|---|---|
| G1 | Tốc độ đọc trong cài đặt cá nhân (F11.03) | Cột `tts_rate` có trong CSDL nhưng API `GET/PATCH /settings` (M02) chưa mở trường này; giao diện đang gửi `rate` theo từng lần gọi `/tts`. Mở trường là đổi hợp đồng M02. |
| G2 | ~~Danh sách giọng và nghe thử giọng (F02.03)~~ | **Đã xử lý ở GĐ5** (danh sách giọng lấy từ Edge TTS, F11.03/M11). |
| G3 | TTS: tạm ngắt gọi dịch vụ khi lỗi liên tục, dọn cache âm thanh cũ | Mục [Đề xuất] của F11.06; chưa có job dọn `tts_cache`. Công tắc bật/tắt TTS của quản trị (F13.05) thuộc GĐ6, hiện là `TTS_ENABLED` trong `.env`. |
| G4 | Trạng thái "Đã lưu" của từ trong trình đọc chỉ nhớ trong phiên | Tải lại trang thì mất; bấm lại sẽ nhận 409 rồi hiện "Đã lưu". Có thể thêm endpoint trả các từ đã lưu theo trang. |
| G5 | Số từ đã lưu theo truyện trên thẻ truyện | Trùng mục B2 của GĐ3 (tránh vòng phụ thuộc library ↔ vocab, cần port riêng). |
| G6 | Admin `GET /admin/users/{id}/reading-progress` chỉ gồm truyện đang đọc dở | Chưa gồm truyện đã đọc xong (cần phương thức repository mới). Router `overview` của F13.07 đặt ở module `review` để tránh vòng phụ thuộc (ghi trong docstring). |
| G7 | File giao diện dài | `ReviewRoom.tsx` khoảng 576 dòng, `ComicReader.tsx` khoảng 1.000 dòng (clean-code ≤ ~300). `VOCABULARY_LIST`, `FLASHCARD_DECKS` trong `data/mockData.ts` không còn dùng nhưng chưa xóa. Thanh tiến độ trong `ProfilePage` vẫn là dữ liệu giả (M12, GĐ6). |
| G8 | Chưa kiểm bằng mắt hiệu ứng lật thẻ 3D | Trình duyệt nhúng không vẽ được biến đổi 3D trong ảnh chụp; đã kiểm bằng DOM (thẻ xoay 180°, hai mặt ẩn mặt lưng). Cần xem trên trình duyệt thật. |
| G9 | Ghi chú khi kiểm thử bằng dòng lệnh | Trên Git Bash/Windows, `curl -d` với chữ Hán bị hỏng mã hóa (server nhận chữ sai, Edge TTS trả lỗi). Gửi bằng Python UTF-8 hoặc `curl --data-binary @file.json`. |
| G10 | F07.08 Xuất CSV/Anki, F08.08 Tối ưu tham số FSRS | Thuộc GĐ6 theo kế hoạch. |
| G11 | ~~Xóa ảnh đại diện~~ | **Đã xử lý ở GĐ5** (F01.10, gỡ ảnh về ảnh mặc định). |

---

# Việc còn mở của Giai đoạn 5 (ghi 25/10/2026, làm sau)

GĐ5 (M09 Kiểm tra, M10 Gợi ý, F07.11, F07.12, F08.11, F02.04, danh sách giọng, xóa ảnh đại diện) đã xong (xem `docs/ke-hoach-trien-khai.md`). Các điểm dưới đây chưa làm hoặc chưa kiểm. Hai mục GĐ4 đã được xử lý ở GĐ5: danh sách giọng để nghe thử (G2) và xóa ảnh đại diện (G11).

| # | Việc | Ghi chú |
|---|---|---|
| H1 | Dữ liệu giả còn trên giao diện Hồ sơ | Khối "Mục tiêu tuần", huy hiệu và tab "Flashcard theo truyện" vẫn là dữ liệu giả; thuộc M12/M16 (GĐ6). |
| H2 | Quản trị M10 và đề dự phòng | Chưa có API quản trị cho M10; chưa hiển thị cho Quản trị viên lý do dùng đề dự phòng (nguyên nhân mới chỉ lưu nội bộ). |
| H3 | Chưa thử bằng trình duyệt các luồng bấm | Phím 1–4 khi làm bài; lưu tạm đáp án khi tải lại trang; nhảy trang từ gợi ý; hoàn tác "Bỏ qua"; nút "Lưu câu"; cỡ chữ A−/A+. |
| H4 | Kho câu ví dụ ở cấp HSK 5+ | Số câu ví dụ có bản dịch ít, đề dự phòng ở cấp cao dễ phải dùng câu thoại đã lưu hoặc câu hỏi theo định nghĩa. |
| H5 | `dict_entries.freq_rank` còn trống | Nguồn "cùng cấp HSK, phổ biến" của từ mở rộng (F09.09) hiện chỉ bốc ngẫu nhiên; cần nạp tần suất từ. |
| H6 | Cảnh báo kích thước bundle Vite | Gói build lớn hơn 500 kB; có thể tách mã (code splitting) sau. |
