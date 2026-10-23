# Quy tắc kiểm soát thay đổi — HỎI TRƯỚC KHI SỬA (bắt buộc, ưu tiên cao nhất)

Quy tắc này đứng trên mọi rule khác. Nếu có mâu thuẫn, làm theo file này.

## 1. Khi nào phải hỏi
Phải hỏi người dùng và **chờ trả lời đồng ý rõ ràng** ("ok", "đồng ý", "làm đi"...) trước khi:
- Tạo, sửa, đổi tên, xóa **bất kỳ file nào trong repo**: code, cấu hình, migration, tài liệu, rules, agents, skills.
- Cài, gỡ hoặc nâng phiên bản thư viện; thêm dịch vụ ngoài.
- Thay đổi **công nghệ, kiến trúc, cấu trúc thư mục, schema CSDL, hợp đồng API** (kể cả khi thay đổi đó có vẻ hiển nhiên).
- Chạy lệnh có tác dụng phụ: migration, xóa dữ liệu, `git commit`/`push`/`reset`, gọi dịch vụ trả phí (LLM).

Không cần hỏi: đọc file, tìm kiếm, chạy test/lint chỉ đọc, ghi file tạm trong thư mục scratchpad.

## 2. Phạm vi của một lần đồng ý
- Yêu cầu của người dùng **nêu cụ thể** việc cần sửa (vd. "sửa US-NH-31 và F06.08") = đã đồng ý **đúng phạm vi đó**, không cần hỏi lại.
- Đồng ý chỉ áp dụng cho phạm vi đã nêu. Phát hiện thêm việc cần sửa ngoài phạm vi → **dừng, báo lại, hỏi tiếp**; không "tiện tay" sửa.
- Đồng ý ở lần trước không áp dụng cho việc mới.

## 3. Mẫu đề xuất trước khi sửa
```
Đề xuất thay đổi
- Mục tiêu: <vì sao cần sửa, gắn mã US/F nếu có>
- File ảnh hưởng: <tạo/sửa/xóa từng file>
- Cách làm: <2–5 gạch đầu dòng>
- Ảnh hưởng: <API/DB/kiến trúc/bảo mật có đổi không; có vi phạm rule nào không>
- Kiểm tra: <test/lint sẽ chạy>
Bạn đồng ý không?
```

## 4. Khi rule cản trở
Nếu yêu cầu của người dùng mâu thuẫn với một rule trong `.claude/rules/` (vd. dùng thư viện ngoài danh sách tech-stack, gọi SQL thô trong use case), **nêu rõ rule bị vi phạm và hậu quả**, đề xuất cách đúng, rồi để người dùng quyết định. Chỉ sửa rule khi người dùng đồng ý sửa rule.

## 5. Subagent
- Subagent không hỏi được người dùng. Claude chính phải xin đồng ý **trước khi giao việc có sửa file**, và brief phải ghi rõ phạm vi đã được duyệt.
- Subagent chỉ làm trong phạm vi brief; gặp việc ngoài phạm vi thì dừng và báo lại, không tự làm.

## 6. Không bao giờ
- Không dùng Bash (`sed`, `echo >`, `rm`, script) để lách việc hỏi khi sửa file.
- Không tự ý sửa `.claude/settings*.json`, `.claude/rules/`, `CLAUDE.md` để nới quy tắc.
