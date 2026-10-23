# Tài liệu User Story — YingHua (映画)

YingHua là ứng dụng web hỗ trợ học tiếng Trung qua truyện tranh và hình ảnh, theo quy trình: Đọc → Nhận diện → Tra cứu → Tìm hiểu → Lưu từ → Ôn tập → Nghe. Tài liệu này mô tả yêu cầu nghiệp vụ của hệ thống dưới dạng user story kèm tiêu chí chấp nhận, làm cơ sở cho thiết kế, lập trình và kiểm thử. Tài liệu chỉ mô tả hành vi quan sát được, không đề cập chi tiết cài đặt.

## 1. Quy ước

**Cú pháp.** Mỗi story gồm: mã và tên ngắn; câu mô tả "Là … tôi muốn … để …"; độ ưu tiên và nguồn; danh sách tiêu chí chấp nhận theo mẫu Cho trước / khi / thì. Mỗi story có 3–6 tiêu chí, gồm cả trường hợp lỗi và trường hợp biên.

**Story hệ thống (system story).** Với actor phụ (Pipeline xử lý ảnh, Dịch vụ TTS, Dịch vụ LLM, Bộ hẹn giờ), story viết dạng "Là <hệ thống/dịch vụ>, tôi cần …, để …".

**Mã story.** `US-<nhóm>-<số thứ tự>`:

| Mã | Actor |
|---|---|
| KH | Khách (chưa đăng nhập) |
| NH | Người học |
| QT | Quản trị viên |
| XL | Pipeline xử lý ảnh |
| TTS | Dịch vụ Text-to-Speech bên ngoài |
| LLM | Dịch vụ LLM bên ngoài |
| HG | Bộ hẹn giờ hệ thống |

Các story NH được chia thành nhóm chức năng A–L, đặt tiêu đề nhóm bằng `####`.

**Độ ưu tiên.** Must (bắt buộc cho bản phát hành đầu), Should (nên có), Could (có thể bổ sung nếu còn thời gian).

**Nguồn.**
- `[TM]`: có trong thuyết minh đề tài.
- `[Luồng 2]`: bổ sung ở luồng Sổ tay, tự xác định HSK và flashcard.
- `[Luồng 3]`: bổ sung ở luồng Kiểm tra cá nhân hóa bằng LLM.
- `[Đề xuất]`: chức năng do nhóm đề xuất thêm, chưa nằm trong thuyết minh.

**Các con số đề xuất** (không có trong thuyết minh, dùng làm giá trị mặc định, có thể điều chỉnh): ảnh tải lên tối đa 10 MB, định dạng jpg/png/webp; Hover hiển thị trong dưới 1 giây; Khách tra thử tối đa 5 lượt mỗi phiên; liên kết đặt lại mật khẩu hết hạn sau 30 phút; tốc độ đọc TTS từ 0,5x đến 1,5x; một bài kiểm tra gồm 10 câu. Các con số khác (mật khẩu tối thiểu 8 ký tự, sổ tay tối thiểu 10 từ để làm kiểm tra, chờ LLM 20 giây, giữ ảnh tải nhanh 7 ngày, chu kỳ dọn dẹp 60 phút, 4 mức đánh giá Quên/Khó/Được/Dễ) lấy theo yêu cầu đã chốt.

**Thuật ngữ.** Người học, Quản trị viên, Hover & Dịch, Sổ tay cá nhân, Flashcard, Spaced Repetition (lịch ôn do thuật toán FSRS tính), Text-to-Speech.

## 2. Bảng tổng hợp actor

| Actor | Loại | Số story | Mã |
|---|---|---|---|
| Khách | Chính | 6 | US-KH-01 … 06 |
| Người học | Chính | 60 | US-NH-01 … 60 |
| Quản trị viên | Chính (kế thừa Người học) | 13 (riêng) | US-QT-01 … 13 |
| Pipeline xử lý ảnh | Phụ (hệ thống) | 9 | US-XL-01 … 09 |
| Dịch vụ TTS bên ngoài | Phụ (hệ thống) | 3 | US-TTS-01 … 03 |
| Dịch vụ LLM bên ngoài | Phụ (hệ thống) | 3 | US-LLM-01 … 03 |
| Bộ hẹn giờ hệ thống | Phụ (hệ thống) | 4 | US-HG-01 … 04 |
| **Tổng** | | **98** | |

---

## 3. Khách (chưa đăng nhập)

### US-KH-01 — Xem trang giới thiệu
**Là** Khách, **tôi muốn** xem trang giới thiệu YingHua, **để** hiểu ứng dụng giúp học tiếng Trung qua truyện tranh như thế nào trước khi đăng ký.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi chưa đăng nhập, **khi** mở địa chỉ trang chủ, **thì** thấy phần giới thiệu các chức năng chính (nhận diện chữ, Hover & Dịch, Sổ tay cá nhân, Flashcard, Text-to-Speech) mà không bị yêu cầu đăng nhập.
2. **Cho trước** đang ở trang giới thiệu, **khi** bấm "Đăng ký" hoặc "Đăng nhập", **thì** được chuyển đến đúng biểu mẫu tương ứng.
3. **Cho trước** tôi đã đăng nhập, **khi** mở trang chủ, **thì** được đưa thẳng tới trang làm việc của Người học thay vì trang giới thiệu.
4. **Cho trước** trang giới thiệu đang mở trên điện thoại, **khi** xem, **thì** nội dung hiển thị đầy đủ, không bị tràn ngang màn hình.

### US-KH-02 — Đăng ký tài khoản
**Là** Khách, **tôi muốn** đăng ký tài khoản bằng email và mật khẩu, **để** lưu từ và theo dõi việc học của mình.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** email chưa được dùng và mật khẩu có từ 8 ký tự trở lên, **khi** gửi biểu mẫu đăng ký, **thì** tài khoản được tạo với vai trò Người học và tôi được đưa tới bước tiếp theo (đăng nhập hoặc vào thẳng ứng dụng).
2. **Cho trước** email đã tồn tại, **khi** đăng ký, **thì** hiện thông báo "Email đã được sử dụng" và không tạo tài khoản mới.
3. **Cho trước** mật khẩu ngắn hơn 8 ký tự, **khi** đăng ký, **thì** hiện thông báo "Mật khẩu tối thiểu 8 ký tự" và không tạo tài khoản.
4. **Cho trước** email sai định dạng (ví dụ thiếu ký tự `@`) hoặc để trống, **khi** đăng ký, **thì** biểu mẫu báo lỗi ngay tại trường đó.
5. **Cho trước** mật khẩu đã đăng ký, **khi** quản trị viên hay bất kỳ ai xem dữ liệu tài khoản, **thì** mật khẩu không bao giờ hiển thị dưới dạng văn bản gốc.

### US-KH-03 — Đăng nhập
**Là** Khách, **tôi muốn** đăng nhập bằng email và mật khẩu, **để** sử dụng đầy đủ chức năng học tập.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** thông tin đúng và tài khoản đang hoạt động, **khi** đăng nhập, **thì** vào được trang làm việc và phiên đăng nhập được thiết lập.
2. **Cho trước** mật khẩu sai hoặc email không tồn tại, **khi** đăng nhập, **thì** hiện cùng một thông báo chung "Email hoặc mật khẩu không đúng", không tiết lộ email có tồn tại hay không.
3. **Cho trước** tài khoản đã bị Quản trị viên khóa, **khi** đăng nhập với thông tin đúng, **thì** không vào được và hiện thông báo "Tài khoản đã bị khóa, vui lòng liên hệ quản trị viên".
4. **Cho trước** để trống email hoặc mật khẩu, **khi** gửi biểu mẫu, **thì** báo lỗi thiếu thông tin và không gửi yêu cầu đăng nhập.
5. **Cho trước** mất kết nối mạng, **khi** đăng nhập, **thì** hiện thông báo "Không thể kết nối, vui lòng thử lại" và dữ liệu đã nhập được giữ nguyên trong biểu mẫu.

### US-KH-04 — Đọc thử một chương công khai
**Là** Khách, **tôi muốn** đọc thử một chương truyện công khai, **để** trải nghiệm ứng dụng trước khi đăng ký.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi chưa đăng nhập, **khi** mở chương được đánh dấu cho đọc thử, **thì** xem được các trang ở dạng ảnh gốc và ảnh đã dịch.
2. **Cho trước** tôi đang đọc thử, **khi** cố mở chương khác không thuộc diện đọc thử, **thì** hiện lời nhắc đăng ký/đăng nhập.
3. **Cho trước** tôi chưa đăng nhập, **khi** cố mở truyện riêng tư của một Người học, **thì** hệ thống từ chối và thông báo không có quyền truy cập.
4. **Cho trước** hiện chưa có chương nào được bật đọc thử, **khi** vào mục đọc thử, **thì** hiện thông báo "Chưa có chương đọc thử" thay vì trang trống.

### US-KH-05 — Tra từ giới hạn khi đọc thử
**Là** Khách, **tôi muốn** tra từ bằng Hover & Dịch khi đọc thử, **để** cảm nhận giá trị của ứng dụng; đồng thời hiểu việc lưu từ cần có tài khoản.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi đang đọc thử, **khi** rê chuột vào một từ, **thì** thấy pinyin và nghĩa tiếng Việt của từ.
2. **Cho trước** đã dùng hết 5 lượt tra trong phiên, **khi** tra tiếp, **thì** hiện lời nhắc đăng ký để tiếp tục, không hiển thị kết quả tra.
3. **Cho trước** tôi là Khách, **khi** bấm "Lưu", **thì** không có từ nào được lưu và hiện lời nhắc đăng ký.
4. **Cho trước** Khách tra từ ở chế độ chi tiết (ví dụ, phân rã chữ Hán), **khi** mở, **thì** chỉ thấy phần thông tin cơ bản và có lời mời đăng ký để xem đầy đủ.

### US-KH-06 — Quên mật khẩu qua email
**Là** Khách, **tôi muốn** đặt lại mật khẩu qua email, **để** lấy lại quyền truy cập khi quên mật khẩu.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** nhập email đã đăng ký, **khi** bấm "Quên mật khẩu", **thì** nhận được email chứa liên kết đặt lại có hiệu lực 30 phút.
2. **Cho trước** nhập email chưa đăng ký, **khi** gửi yêu cầu, **thì** vẫn hiện thông báo chung "Nếu email tồn tại, chúng tôi đã gửi hướng dẫn" và không gửi email.
3. **Cho trước** liên kết đã quá 30 phút hoặc đã dùng một lần, **khi** mở, **thì** hiện thông báo liên kết không còn hiệu lực và cho phép yêu cầu lại.
4. **Cho trước** đặt mật khẩu mới có dưới 8 ký tự, **khi** gửi, **thì** bị từ chối với thông báo tối thiểu 8 ký tự.
5. **Cho trước** đặt lại thành công, **khi** hoàn tất, **thì** mọi phiên đăng nhập cũ của tài khoản bị đăng xuất.

---

## 4. Người học

#### Nhóm A — Tài khoản và cài đặt cá nhân

### US-NH-01 — Duy trì phiên đăng nhập
**Là** Người học, **tôi muốn** phiên đăng nhập được tự làm mới khi còn hoạt động, **để** không bị đăng xuất giữa lúc đang đọc.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** phiên sắp hết hạn và tôi vẫn đang thao tác, **khi** hệ thống làm mới phiên, **thì** tôi tiếp tục dùng mà không phải đăng nhập lại và không mất nội dung đang xem.
2. **Cho trước** phiên làm mới đã hết hạn hoặc bị thu hồi, **khi** thao tác tiếp, **thì** tôi được đưa về trang đăng nhập kèm thông báo "Phiên đã hết hạn".
3. **Cho trước** tôi bị khóa tài khoản trong lúc đang dùng, **khi** phiên được làm mới, **thì** việc làm mới bị từ chối và tôi bị đăng xuất.
4. **Cho trước** mất mạng đúng lúc làm mới, **khi** có mạng trở lại, **thì** hệ thống thử làm mới lại thay vì đăng xuất ngay.

### US-NH-02 — Đăng xuất
**Là** Người học, **tôi muốn** đăng xuất khỏi thiết bị đang dùng, **để** bảo vệ tài khoản trên máy dùng chung.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** đang đăng nhập, **khi** bấm "Đăng xuất", **thì** được đưa về trang giới thiệu và không còn truy cập được các trang cá nhân.
2. **Cho trước** đã đăng xuất, **khi** dùng nút Quay lại của trình duyệt, **thì** không xem được dữ liệu cá nhân.
3. **Cho trước** tôi đăng nhập ở hai thiết bị, **khi** đăng xuất ở thiết bị A, **thì** thiết bị B vẫn đăng nhập bình thường.

### US-NH-03 — Đăng xuất mọi thiết bị
**Là** Người học, **tôi muốn** đăng xuất khỏi tất cả thiết bị, **để** thu hồi quyền truy cập khi nghi ngờ lộ tài khoản.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi đăng nhập trên nhiều thiết bị, **khi** bấm "Đăng xuất mọi thiết bị", **thì** tất cả phiên (kể cả phiên hiện tại) bị thu hồi và mọi thiết bị phải đăng nhập lại.
2. **Cho trước** thiết bị khác đang mở, **khi** nó gửi yêu cầu kế tiếp, **thì** nhận thông báo phiên không hợp lệ và chuyển về trang đăng nhập.
3. **Cho trước** thao tác thành công, **khi** hoàn tất, **thì** hiện thông báo xác nhận số thiết bị đã bị đăng xuất.
4. **Cho trước** mất mạng khi thực hiện, **khi** yêu cầu không gửi được, **thì** hiện lỗi và các phiên vẫn còn hiệu lực (không rơi vào trạng thái nửa chừng).

### US-NH-04 — Xem và sửa hồ sơ
**Là** Người học, **tôi muốn** xem và chỉnh sửa hồ sơ cá nhân, **để** thông tin tài khoản luôn đúng.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** đã đăng nhập, **khi** mở trang hồ sơ, **thì** thấy email, tên hiển thị và ngày tham gia của chính tôi.
2. **Cho trước** nhập tên hiển thị hợp lệ, **khi** lưu, **thì** tên mới hiển thị ngay trên giao diện và còn nguyên sau khi tải lại trang.
3. **Cho trước** để trống tên hiển thị, **khi** lưu, **thì** bị từ chối với thông báo trường bắt buộc.
4. **Cho trước** tôi cố sửa hồ sơ của người khác, **khi** thao tác, **thì** hệ thống từ chối với thông báo không có quyền.

### US-NH-05 — Đổi mật khẩu
**Là** Người học, **tôi muốn** đổi mật khẩu, **để** giữ an toàn cho tài khoản.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** nhập đúng mật khẩu hiện tại và mật khẩu mới từ 8 ký tự, **khi** xác nhận, **thì** đổi thành công và hiện thông báo.
2. **Cho trước** nhập sai mật khẩu hiện tại, **khi** xác nhận, **thì** bị từ chối với thông báo "Mật khẩu hiện tại không đúng" và mật khẩu không đổi.
3. **Cho trước** mật khẩu mới dưới 8 ký tự, **khi** xác nhận, **thì** bị từ chối với thông báo tối thiểu 8 ký tự.
4. **Cho trước** đổi mật khẩu thành công, **khi** các thiết bị khác gửi yêu cầu tiếp theo, **thì** các phiên đó bị đăng xuất, còn phiên hiện tại vẫn hoạt động.
5. **Cho trước** mật khẩu mới trùng mật khẩu cũ, **khi** xác nhận, **thì** bị từ chối với thông báo yêu cầu chọn mật khẩu khác.

### US-NH-06 — Khai báo trình độ HSK
**Là** Người học, **tôi muốn** khai báo trình độ HSK của mình (1–9), **để** gợi ý từ và đề kiểm tra phù hợp với tôi.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** mở trang cài đặt, **khi** chọn trình độ từ 1 đến 9 và lưu, **thì** giá trị được ghi nhận và hiển thị lại đúng ở lần mở sau.
2. **Cho trước** giá trị nằm ngoài khoảng 1–9, **khi** lưu, **thì** bị từ chối với thông báo giá trị không hợp lệ.
3. **Cho trước** tôi chưa khai báo trình độ, **khi** mở cài đặt, **thì** thấy trạng thái "Chưa chọn" và các gợi ý dùng mức mặc định chung.
4. **Cho trước** tôi đổi trình độ, **khi** xem gợi ý từ, **thì** danh sách gợi ý thay đổi phù hợp với trình độ mới.

### US-NH-07 — Chọn chế độ mặc định Đọc/Học
**Là** Người học, **tôi muốn** chọn chế độ mặc định là Đọc hoặc Học, **để** giao diện đọc truyện mở đúng cách tôi thường dùng.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi chọn chế độ Đọc làm mặc định, **khi** mở một chương, **thì** trang hiển thị ở chế độ Đọc (ưu tiên ảnh đã đắp bản dịch).
2. **Cho trước** tôi chọn chế độ Học làm mặc định, **khi** mở một chương, **thì** trang hiển thị ở chế độ Học (ưu tiên ảnh gốc kèm Hover & Dịch).
3. **Cho trước** đang đọc, **khi** tôi chuyển chế độ tạm thời bằng nút chuyển, **thì** thiết lập mặc định đã lưu không bị thay đổi.
4. **Cho trước** chưa thiết lập, **khi** mở chương lần đầu, **thì** chế độ Đọc được dùng làm mặc định (giả định).

### US-NH-08 — Chọn giọng đọc Text-to-Speech
**Là** Người học, **tôi muốn** chọn giọng đọc Text-to-Speech ưa thích, **để** nghe phát âm bằng giọng dễ nghe nhất với tôi.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** mở cài đặt, **khi** xem danh sách giọng, **thì** thấy các giọng tiếng Trung khả dụng và có nút nghe thử.
2. **Cho trước** tôi chọn một giọng và lưu, **khi** nghe phát âm bất kỳ từ nào, **thì** âm thanh được đọc bằng giọng đã chọn.
3. **Cho trước** giọng đã chọn không còn khả dụng, **khi** phát âm, **thì** hệ thống dùng giọng mặc định và hiện thông báo đã chuyển giọng.
4. **Cho trước** tôi chưa chọn giọng, **khi** nghe phát âm, **thì** dùng giọng mặc định của hệ thống.

#### Nhóm B — Thư viện truyện

### US-NH-09 — Duyệt và tìm truyện công khai
**Là** Người học, **tôi muốn** duyệt và tìm kiếm truyện công khai, **để** chọn truyện muốn đọc.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** thư viện có truyện công khai, **khi** mở trang thư viện, **thì** thấy danh sách truyện (tên, ảnh bìa, số chương) được chia trang.
2. **Cho trước** nhập từ khóa trùng một phần tên truyện, **khi** tìm kiếm, **thì** chỉ hiện các truyện có tên khớp từ khóa, không phân biệt hoa thường.
3. **Cho trước** từ khóa không khớp truyện nào, **khi** tìm kiếm, **thì** hiện thông báo "Không tìm thấy truyện phù hợp".
4. **Cho trước** truyện riêng tư của người khác, **khi** tôi duyệt hay tìm kiếm, **thì** truyện đó không xuất hiện trong kết quả.
5. **Cho trước** truyện riêng tư của chính tôi, **khi** mở thư viện, **thì** tôi thấy chúng ở mục "Truyện của tôi".

### US-NH-10 — Tạo truyện riêng tư
**Là** Người học, **tôi muốn** tạo truyện riêng tư của mình, **để** học từ chính những trang truyện tôi muốn đọc.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** nhập tên truyện hợp lệ, **khi** tạo, **thì** truyện được tạo ở chế độ riêng tư và chỉ tôi nhìn thấy.
2. **Cho trước** để trống tên truyện, **khi** tạo, **thì** bị từ chối với thông báo trường bắt buộc.
3. **Cho trước** tên truyện trùng với một truyện đã có của tôi, **khi** tạo, **thì** hệ thống cảnh báo trùng tên và yêu cầu xác nhận hoặc đổi tên.
4. **Cho trước** tôi là Người học (không phải Quản trị viên), **khi** tìm cách chuyển truyện sang công khai, **thì** hệ thống từ chối vì chỉ Quản trị viên được đăng truyện công khai.

### US-NH-11 — Thêm chương
**Là** Người học, **tôi muốn** thêm chương vào truyện của mình, **để** sắp xếp các trang theo từng phần.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi là chủ truyện, **khi** thêm chương với số thứ tự và tên hợp lệ, **thì** chương xuất hiện đúng vị trí trong danh sách chương.
2. **Cho trước** số thứ tự chương đã tồn tại trong truyện, **khi** thêm, **thì** bị từ chối với thông báo trùng số chương.
3. **Cho trước** truyện thuộc người khác, **khi** tôi cố thêm chương, **thì** hệ thống từ chối với thông báo không có quyền.
4. **Cho trước** thêm chương thành công, **khi** mở chương, **thì** chương hiển thị trạng thái "Chưa có trang".

### US-NH-12 — Tải ảnh trang lên chương
**Là** Người học, **tôi muốn** tải ảnh các trang truyện lên chương, **để** hệ thống xử lý và tôi có thể đọc, tra từ.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tệp jpg, png hoặc webp không quá 10 MB, **khi** tải lên chương của tôi, **thì** trang được tạo với trạng thái "Đang chờ" và hiện trong danh sách trang.
2. **Cho trước** tệp có định dạng khác hoặc lớn hơn 10 MB, **khi** tải lên, **thì** bị từ chối và thông báo rõ lý do (định dạng hoặc dung lượng).
3. **Cho trước** ảnh trùng nội dung với trang đã có trong cùng chương, **khi** tải lên, **thì** hệ thống phát hiện trùng, không tạo trang mới và thông báo "Ảnh đã tồn tại".
4. **Cho trước** chọn nhiều ảnh cùng lúc, **khi** có một ảnh lỗi, **thì** các ảnh hợp lệ vẫn được tải và ảnh lỗi được liệt kê riêng kèm lý do.
5. **Cho trước** mất kết nối giữa chừng, **khi** tải chưa xong, **thì** trang không được tạo ở trạng thái dở dang và tôi có thể tải lại.

### US-NH-13 — Tải nhanh một ảnh lẻ để đọc ngay
**Là** Người học, **tôi muốn** tải nhanh một ảnh lẻ mà không cần tạo truyện, **để** đọc và tra từ ngay trên ảnh đó.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** ảnh jpg/png/webp không quá 10 MB, **khi** tải nhanh, **thì** ảnh được xử lý và tôi mở được ngay trang đọc với Hover & Dịch khi xử lý xong.
2. **Cho trước** ảnh tải nhanh, **khi** xem thông tin, **thì** có ghi chú ảnh sẽ được tự động xóa sau 7 ngày.
3. **Cho trước** ảnh không đạt định dạng/dung lượng, **khi** tải lên, **thì** bị từ chối với thông báo cụ thể.
4. **Cho trước** ảnh tải nhanh của người khác, **khi** tôi truy cập, **thì** hệ thống từ chối vì không có quyền.
5. **Cho trước** ảnh tải nhanh đã bị xóa sau 7 ngày, **khi** mở lại, **thì** hiện thông báo "Ảnh đã hết hạn lưu".

### US-NH-14 — Sửa và xóa truyện, chương, trang của mình
**Là** Người học, **tôi muốn** sửa và xóa truyện, chương, trang do tôi tạo, **để** quản lý thư viện cá nhân gọn gàng.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi là chủ truyện, **khi** sửa tên truyện, tên chương hoặc thứ tự chương, **thì** thay đổi được lưu và hiển thị ngay.
2. **Cho trước** tôi xóa một truyện, **khi** xác nhận ở hộp thoại cảnh báo, **thì** truyện cùng chương, trang và ảnh liên quan bị xóa; nếu tôi hủy thì không có gì bị xóa.
3. **Cho trước** xóa một trang, **khi** hoàn tất, **thì** trang biến mất khỏi chương, nhưng từ đã lưu trong Sổ tay cá nhân vẫn giữ ngữ cảnh ảnh đã cắt trước đó.
4. **Cho trước** đối tượng đã bị xóa từ thiết bị khác, **khi** tôi thao tác trên bản cũ, **thì** hiện thông báo "Không còn tồn tại".

### US-NH-15 — Không được sửa truyện của người khác
**Là** Người học, **tôi muốn** dữ liệu truyện của mình được bảo vệ khỏi người khác, **để** không ai tự ý sửa hay xóa nội dung của tôi.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** truyện thuộc Người học khác, **khi** tôi cố sửa/xóa truyện, chương hoặc trang, **thì** hệ thống từ chối với thông báo "Bạn không có quyền thực hiện thao tác này" và dữ liệu không đổi.
2. **Cho trước** truyện công khai do Quản trị viên đăng, **khi** tôi là Người học, **thì** chỉ đọc được, không sửa/xóa được.
3. **Cho trước** truyện riêng tư của người khác, **khi** tôi cố mở bằng đường dẫn trực tiếp, **thì** bị từ chối như khi không tồn tại (không tiết lộ sự có mặt của truyện).
4. **Cho trước** nút sửa/xóa, **khi** tôi xem truyện không thuộc quyền, **thì** các nút này không hiển thị.

### US-NH-16 — Lưu và tiếp tục tiến độ đọc
**Là** Người học, **tôi muốn** hệ thống ghi nhớ trang tôi đang đọc, **để** tiếp tục đúng chỗ ở lần sau.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi đang đọc trang 5 chương 3, **khi** rời khỏi và quay lại truyện, **thì** có nút "Tiếp tục đọc" dẫn đúng tới trang 5 chương 3.
2. **Cho trước** tôi đọc trên thiết bị A, **khi** đăng nhập thiết bị B, **thì** tiến độ cũng được tiếp tục tại cùng vị trí.
3. **Cho trước** chưa đọc truyện nào, **khi** mở thư viện, **thì** không hiện nút "Tiếp tục đọc".
4. **Cho trước** trang tôi đang dừng đã bị xóa, **khi** bấm "Tiếp tục đọc", **thì** đưa tôi tới trang gần nhất còn tồn tại thay vì báo lỗi.

#### Nhóm C — Đọc và nhận diện văn bản

### US-NH-17 — Tự động nhận diện vùng chữ tiếng Trung
**Là** Người học, **tôi muốn** hệ thống tự nhận diện các vùng chữ tiếng Trung trên ảnh tôi tải lên, **để** không phải nhập tay nội dung.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi vừa tải một trang lên, **khi** hệ thống xử lý xong, **thì** các vùng chữ (bong bóng) được nhận diện và có thể rê chuột vào để tra.
2. **Cho trước** ảnh không có chữ tiếng Trung, **khi** xử lý xong, **thì** trang ở trạng thái "Xong" kèm thông báo "Không tìm thấy văn bản tiếng Trung".
3. **Cho trước** ảnh quá mờ khiến không nhận diện được, **khi** xử lý, **thì** trang chuyển sang trạng thái "Lỗi" kèm lý do và không hiện vùng chữ sai lệch.
4. **Cho trước** nhận diện xong, **khi** tôi tải lại trang, **thì** kết quả nhận diện không phải chạy lại và hiển thị ngay.

### US-NH-18 — Xem trạng thái xử lý
**Là** Người học, **tôi muốn** thấy trạng thái xử lý của từng trang (đang chờ, đang xử lý, xong, lỗi), **để** biết khi nào có thể đọc.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi vừa tải ảnh lên, **khi** xem danh sách trang, **thì** mỗi trang hiện đúng một trong bốn trạng thái: Đang chờ, Đang xử lý, Xong, Lỗi.
2. **Cho trước** một trang đang xử lý, **khi** hoàn tất, **thì** trạng thái tự cập nhật sang "Xong" mà không cần tải lại trang.
3. **Cho trước** một trang ở trạng thái "Lỗi", **khi** tôi xem chi tiết, **thì** thấy lý do lỗi bằng tiếng Việt dễ hiểu và nút "Dịch lại".
4. **Cho trước** trang chưa "Xong", **khi** tôi mở nó, **thì** hiện thông báo đang xử lý và không hiển thị Hover & Dịch.

### US-NH-19 — Xem trang ở ba dạng hiển thị
**Là** Người học, **tôi muốn** xem trang ở ba dạng: ảnh gốc, ảnh đã xóa chữ, ảnh đã đắp bản dịch tiếng Việt, **để** đọc hiểu và đối chiếu với bản gốc.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** trang ở trạng thái "Xong", **khi** chọn từng dạng xem, **thì** hiển thị lần lượt ảnh gốc, ảnh đã xóa chữ và ảnh đã đắp bản dịch tiếng Việt.
2. **Cho trước** chuyển giữa các dạng, **khi** đổi, **thì** vị trí cuộn và mức phóng to được giữ nguyên.
3. **Cho trước** trang chưa xử lý xong, **khi** chọn dạng đã xóa chữ hoặc đã dịch, **thì** các lựa chọn này bị vô hiệu hóa kèm chú thích lý do; ảnh gốc vẫn xem được.
4. **Cho trước** đường truyền chậm, **khi** ảnh đang tải, **thì** hiện chỉ báo đang tải và không hiện ảnh vỡ.

### US-NH-20 — Tải ảnh về máy
**Là** Người học, **tôi muốn** tải ảnh (gốc, đã xóa chữ hoặc đã dịch) về máy, **để** xem lại ngoại tuyến.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** trang ở trạng thái "Xong", **khi** bấm "Tải về" ở một dạng xem, **thì** tệp ảnh của đúng dạng đó được tải xuống.
2. **Cho trước** trang chưa có ảnh dịch, **khi** bấm tải ảnh dịch, **thì** hiện thông báo "Chưa có ảnh dịch".
3. **Cho trước** trang thuộc truyện riêng tư của người khác, **khi** tôi cố tải, **thì** bị từ chối vì không có quyền.
4. **Cho trước** mất mạng khi đang tải, **khi** tải không hoàn tất, **thì** hiện thông báo lỗi và cho phép thử lại.

### US-NH-21 — Yêu cầu dịch lại khi lỗi
**Là** Người học, **tôi muốn** yêu cầu hệ thống xử lý lại trang bị lỗi, **để** có bản dịch mà không phải tải ảnh lên lần nữa.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** trang ở trạng thái "Lỗi" thuộc trang của tôi, **khi** bấm "Dịch lại", **thì** trạng thái chuyển sang "Đang chờ" và trang được đưa lại vào hàng đợi.
2. **Cho trước** trang đang "Đang chờ" hoặc "Đang xử lý", **khi** bấm "Dịch lại", **thì** yêu cầu bị từ chối với thông báo trang đang được xử lý (không tạo thêm công việc trùng).
3. **Cho trước** trang không thuộc quyền của tôi, **khi** yêu cầu dịch lại, **thì** bị từ chối vì không có quyền.
4. **Cho trước** xử lý lại vẫn lỗi, **khi** hoàn tất, **thì** trạng thái trở về "Lỗi" kèm lý do mới nhất.

#### Nhóm D — Hover & Dịch và chỉnh bản dịch

### US-NH-22 — Hover & Dịch bằng chuột
**Là** Người học, **tôi muốn** rê chuột vào từ hoặc câu trong bong bóng để thấy pinyin, nghĩa và bản dịch câu ngay trên ảnh, **để** hiểu nội dung mà không phải chuyển tab hay mất bố cục.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** trang ở trạng thái "Xong", **khi** rê chuột vào một từ trong bong bóng, **thì** trong dưới 1 giây hiện khung gồm pinyin, nghĩa tiếng Việt của từ và bản dịch cả câu.
2. **Cho trước** khung Hover đang hiện, **khi** quan sát bố cục, **thì** ảnh truyện không bị dịch chuyển hay thu phóng, và khung không bị cắt ở mép màn hình.
3. **Cho trước** từ không có trong từ điển, **khi** rê chuột vào, **thì** hiện pinyin (nếu có) và dòng "Chưa có nghĩa trong từ điển" thay vì khung trống.
4. **Cho trước** tôi rê chuột ra ngoài vùng từ, **khi** rời đi, **thì** khung Hover tự ẩn.
5. **Cho trước** mất kết nối mạng, **khi** rê chuột vào từ chưa được tải sẵn, **thì** hiện thông báo "Không tải được, thử lại".

### US-NH-23 — Hover & Dịch bằng cảm ứng
**Là** Người học, **tôi muốn** chạm vào từ trong bong bóng trên điện thoại để xem pinyin và nghĩa, **để** học được cả khi không có chuột.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi dùng màn hình cảm ứng, **khi** chạm vào một từ, **thì** hiện khung giống Hover (pinyin, nghĩa, bản dịch câu) trong dưới 1 giây.
2. **Cho trước** khung đang hiện, **khi** chạm ra ngoài khung, **thì** khung đóng lại.
3. **Cho trước** chạm vào từ khác khi khung đang mở, **khi** chạm, **thì** khung chuyển sang từ mới mà không chồng nhiều khung.
4. **Cho trước** thao tác cuộn hoặc phóng to bằng hai ngón, **khi** thực hiện, **thì** không bị nhận nhầm là chạm chọn từ.

### US-NH-24 — Sửa bản dịch của một bong bóng
**Là** Người học, **tôi muốn** sửa bản dịch của một bong bóng cho riêng mình, **để** bản dịch phù hợp hơn với cách hiểu của tôi.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** trang ở trạng thái "Xong", **khi** tôi nhập bản dịch mới cho một bong bóng và lưu, **thì** bản dịch mới hiển thị khi tôi xem và Hover, còn người học khác vẫn thấy bản dịch gốc.
2. **Cho trước** để trống nội dung sửa, **khi** lưu, **thì** bị từ chối với thông báo nội dung không được trống.
3. **Cho trước** tôi đã sửa bản dịch, **khi** mở lại trang ở lần sau hoặc trên thiết bị khác, **thì** bản sửa vẫn còn.
4. **Cho trước** truyện công khai, **khi** tôi sửa bản dịch, **thì** bản sửa không làm thay đổi dữ liệu dịch dùng chung của hệ thống.

### US-NH-25 — Hoàn tác bản sửa dịch
**Là** Người học, **tôi muốn** hoàn tác bản sửa dịch, **để** quay lại bản dịch tự động ban đầu.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** bong bóng có bản sửa của tôi, **khi** bấm "Hoàn tác", **thì** bản dịch hiển thị trở lại là bản tự động ban đầu.
2. **Cho trước** bong bóng chưa từng được sửa, **khi** xem, **thì** nút "Hoàn tác" không hiển thị hoặc bị vô hiệu hóa.
3. **Cho trước** hoàn tác thành công, **khi** tải lại trang, **thì** vẫn thấy bản dịch gốc, không phải bản sửa cũ.
4. **Cho trước** trang được dịch lại sau khi tôi đã sửa, **khi** xử lý lại xong, **thì** hệ thống hỏi hoặc ghi rõ bản sửa của tôi được giữ hay thay (giả định: giữ bản sửa và cho phép hoàn tác).

#### Nhóm E — Tra cứu đa chiều và phân rã chữ Hán

### US-NH-26 — Tra cứu chi tiết một từ
**Là** Người học, **tôi muốn** xem thông tin đa chiều của một từ gồm chữ Hán, Pinyin, Hán Việt, nghĩa tiếng Việt, từ loại, ví dụ và ngữ cảnh trong truyện, **để** hiểu sâu cách dùng từ.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** từ có trong từ điển, **khi** mở chi tiết từ, **thì** thấy đủ: chữ Hán, Pinyin, âm Hán Việt, nghĩa tiếng Việt, từ loại và ít nhất một ví dụ nếu dữ liệu có.
2. **Cho trước** tôi mở chi tiết từ một bong bóng, **khi** xem phần ngữ cảnh, **thì** thấy câu chứa từ đó trong bong bóng hiện tại.
3. **Cho trước** từ thiếu một số trường (ví dụ chưa có ví dụ), **khi** mở chi tiết, **thì** trường thiếu được ẩn hoặc ghi "Chưa có dữ liệu", không hiện giá trị rỗng/null.
4. **Cho trước** từ có nhiều nghĩa, **khi** xem, **thì** các nghĩa được liệt kê theo thứ tự có đánh số.

### US-NH-27 — Tìm kiếm từ
**Là** Người học, **tôi muốn** tìm từ bằng chữ Hán, Pinyin hoặc nghĩa tiếng Việt, **để** tra cứu nhanh mà không cần đọc truyện.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** nhập một chữ Hán có trong từ điển, **khi** tìm kiếm, **thì** các mục khớp được liệt kê, mục khớp chính xác nằm trên cùng.
2. **Cho trước** nhập Pinyin có hoặc không có dấu thanh, **khi** tìm kiếm, **thì** vẫn trả về các từ phù hợp.
3. **Cho trước** từ khóa không khớp mục nào, **khi** tìm kiếm, **thì** hiện "Không tìm thấy từ phù hợp".
4. **Cho trước** từ khóa để trống, **khi** bấm tìm, **thì** không thực hiện tìm và nhắc nhập từ khóa.

### US-NH-28 — Tra từ điển chuyên ngành truyện tu tiên
**Là** Người học, **tôi muốn** tra từ điển chuyên ngành truyện tu tiên, **để** hiểu các thuật ngữ đặc thù mà từ điển thông thường không giải thích.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** từ là thuật ngữ tu tiên có trong từ điển chuyên ngành (ví dụ tên cảnh giới), **khi** tra, **thì** kết quả ghi rõ nguồn là "từ điển tu tiên" bên cạnh nghĩa.
2. **Cho trước** từ có cả nghĩa thông thường và nghĩa tu tiên, **khi** tra, **thì** hiển thị cả hai nghĩa và phân biệt rõ.
3. **Cho trước** từ không phải thuật ngữ tu tiên, **khi** tra, **thì** không hiện mục từ điển chuyên ngành.
4. **Cho trước** tôi tắt hiển thị từ điển chuyên ngành trong cài đặt (giả định), **khi** tra, **thì** chỉ thấy nghĩa thông thường.

### US-NH-29 — Tách câu thành từ
**Là** Người học, **tôi muốn** hệ thống tách câu tiếng Trung thành các từ, **để** biết ranh giới từ và tra từng từ.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một câu tiếng Trung trong bong bóng hoặc do tôi nhập, **khi** yêu cầu tách từ, **thì** nhận được danh sách từ theo đúng thứ tự xuất hiện, mỗi từ kèm pinyin.
2. **Cho trước** câu chứa ký tự không phải chữ Hán (số, dấu câu, chữ Latin), **khi** tách, **thì** các ký tự đó được giữ nguyên nhưng không bị tra như từ.
3. **Cho trước** nhập chuỗi rỗng, **khi** tách, **thì** hiện nhắc nhập nội dung và không trả kết quả.
4. **Cho trước** tôi bấm vào một từ sau khi tách, **khi** chọn, **thì** mở chi tiết từ đó (US-NH-26).

### US-NH-30 — Phân rã chữ Hán
**Là** Người học, **tôi muốn** xem bộ thủ, thành phần cấu tạo và số nét của một chữ Hán, **để** ghi nhớ chữ dễ hơn.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một chữ Hán đơn có dữ liệu, **khi** mở phần phân rã, **thì** thấy bộ thủ, các thành phần cấu tạo và số nét.
2. **Cho trước** từ gồm nhiều chữ, **khi** mở phân rã, **thì** có thể xem lần lượt từng chữ cấu thành.
3. **Cho trước** chữ chưa có dữ liệu phân rã, **khi** mở, **thì** hiện "Chưa có dữ liệu phân rã" và các phần khác của chi tiết từ vẫn dùng bình thường.
4. **Cho trước** ký tự không phải chữ Hán, **khi** yêu cầu phân rã, **thì** hệ thống từ chối với thông báo ký tự không hợp lệ.

#### Nhóm F — Sổ tay cá nhân

### US-NH-31 — Lưu từ từ ngay khi đang đọc
**Là** Người học, **tôi muốn** bấm "Lưu" ngay khi đang đọc, **để** từ được đưa vào Sổ tay cá nhân kèm ngữ cảnh gốc, cấp độ HSK và flashcard mà không phải nhập tay.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM] [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi đang xem khung Hover của một từ, **khi** bấm "Lưu", **thì** từ xuất hiện trong Sổ tay cá nhân ở trạng thái "Đang học" cùng ảnh bong bóng được cắt làm ngữ cảnh.
2. **Cho trước** từ nằm trong danh sách HSK, **khi** lưu, **thì** hệ thống tự gán cấp độ HSK tương ứng.
   - Nếu từ **không có** trong danh sách HSK, hệ thống lấy **cấp cao nhất trong các chữ cấu thành** (cấp của một chữ là cấp của chữ đó khi đứng một mình như một từ trong danh sách HSK) và gắn nhãn "suy từ chữ cấu thành". Ví dụ: từ gồm một chữ cấp 2 và một chữ cấp 5 thì được gán cấp 5.
   - Nếu không chữ nào có cấp HSK (hoặc từ chỉ có một chữ và chữ đó không có trong danh sách) thì ghi "Ngoài HSK".
3. **Cho trước** lưu thành công, **khi** mở trang ôn tập, **thì** flashcard cho từ đó đã được tạo và sẽ đến hạn theo lịch ôn đầu tiên.
4. **Cho trước** không cắt được ảnh bong bóng (ví dụ lỗi tọa độ), **khi** lưu, **thì** từ vẫn được lưu kèm câu văn bản làm ngữ cảnh và hiện cảnh báo thiếu ảnh.
5. **Cho trước** mất kết nối khi bấm "Lưu", **khi** gửi không được, **thì** hiện thông báo "Chưa lưu được, thử lại" và không có bản ghi nửa chừng.
6. **Cho trước** tôi là Khách, **khi** bấm "Lưu", **thì** bị chuyển sang lời nhắc đăng ký (US-KH-05).

### US-NH-32 — Lưu từ không trùng lặp
**Là** Người học, **tôi muốn** việc lưu lại một từ đã có chỉ thêm ngữ cảnh mới, **để** Sổ tay cá nhân không bị trùng từ.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** từ X đã có trong sổ tay, **khi** tôi lưu lại X từ một bong bóng khác, **thì** sổ tay vẫn chỉ có một mục X và mục này có thêm một ngữ cảnh mới.
2. **Cho trước** lưu lại X từ đúng bong bóng đã lưu, **khi** bấm "Lưu", **thì** hiện thông báo "Từ này đã có với ngữ cảnh này" và không thêm ngữ cảnh trùng.
3. **Cho trước** lưu lại X, **khi** hoàn tất, **thì** flashcard cũ giữ nguyên lịch ôn, không tạo flashcard mới và không đặt lại tiến độ.
4. **Cho trước** hai lần bấm "Lưu" liên tiếp rất nhanh, **khi** xử lý, **thì** chỉ tạo đúng một mục từ.

### US-NH-33 — Đổi trạng thái học của từ
**Là** Người học, **tôi muốn** đổi trạng thái của từ giữa "Đang học", "Đã thuộc" và "Bỏ qua", **để** sổ tay phản ánh đúng mức độ nắm vững.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM] [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** từ ở trạng thái "Đang học", **khi** chuyển sang "Đã thuộc", **thì** nhãn đổi ngay và thẻ của từ đó không còn xuất hiện trong danh sách thẻ đến hạn.
2. **Cho trước** từ ở trạng thái "Bỏ qua", **khi** chuyển lại "Đang học", **thì** thẻ được đưa trở lại lịch ôn tập.
3. **Cho trước** chọn trạng thái ngoài ba giá trị trên, **khi** gửi, **thì** bị từ chối với thông báo trạng thái không hợp lệ.
4. **Cho trước** từ của người khác, **khi** tôi cố đổi trạng thái, **thì** bị từ chối vì không có quyền.

### US-NH-34 — Ghi chú cho từ
**Là** Người học, **tôi muốn** thêm ghi chú cho từ trong sổ tay, **để** lưu mẹo nhớ hay giải thích riêng.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** mở một từ trong sổ tay, **khi** nhập ghi chú và lưu, **thì** ghi chú hiển thị lại ở các lần mở sau và trong thẻ ôn tập của từ đó.
2. **Cho trước** xóa hết nội dung ghi chú rồi lưu, **khi** hoàn tất, **thì** từ không còn ghi chú.
3. **Cho trước** ghi chú vượt quá độ dài tối đa (đề xuất 1000 ký tự), **khi** lưu, **thì** bị từ chối với thông báo vượt giới hạn.
4. **Cho trước** ghi chú chứa ký tự đặc biệt hoặc mã HTML, **khi** hiển thị, **thì** được hiện như văn bản thuần, không bị thực thi.

### US-NH-35 — Xem và xóa ngữ cảnh của từ
**Là** Người học, **tôi muốn** xem và xóa từng ngữ cảnh (ảnh bong bóng) của một từ, **để** giữ lại những ngữ cảnh hữu ích.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** từ có nhiều ngữ cảnh, **khi** mở chi tiết, **thì** thấy danh sách ngữ cảnh, mỗi ngữ cảnh gồm ảnh bong bóng và nguồn (truyện, chương, trang).
2. **Cho trước** tôi xóa một ngữ cảnh khi từ còn từ hai ngữ cảnh trở lên, **khi** xác nhận, **thì** chỉ ngữ cảnh đó bị xóa, từ và flashcard vẫn giữ nguyên.
3. **Cho trước** từ chỉ còn một ngữ cảnh, **khi** tôi xóa ngữ cảnh đó, **thì** từ vẫn còn trong sổ tay (không có ngữ cảnh) hoặc hệ thống hỏi xác nhận xóa cả từ (giả định: từ vẫn còn).
4. **Cho trước** bấm vào một ngữ cảnh, **khi** mở, **thì** đưa tới đúng trang truyện nguồn nếu trang đó còn tồn tại; nếu đã bị xóa thì hiện thông báo "Trang nguồn không còn".

### US-NH-36 — Xóa từ khỏi sổ tay
**Là** Người học, **tôi muốn** xóa một từ khỏi sổ tay, **để** loại bỏ từ tôi không muốn học.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** từ có trong sổ tay, **khi** xóa và xác nhận ở hộp thoại, **thì** từ, các ngữ cảnh, ghi chú và flashcard của từ đó đều bị xóa.
2. **Cho trước** hộp thoại xác nhận, **khi** tôi chọn "Hủy", **thì** không có dữ liệu nào bị xóa.
3. **Cho trước** từ đã xóa, **khi** lưu lại từ đó sau này, **thì** được xem như từ mới với lịch ôn bắt đầu lại.
4. **Cho trước** từ của người khác, **khi** tôi cố xóa, **thì** bị từ chối vì không có quyền.

### US-NH-37 — Lọc sổ tay theo HSK và trạng thái
**Là** Người học, **tôi muốn** lọc sổ tay theo cấp độ HSK và trạng thái, **để** tập trung vào nhóm từ cần học.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** sổ tay có từ ở nhiều cấp, **khi** chọn bộ lọc HSK 3, **thì** chỉ hiển thị các từ HSK 3 và hiện số lượng kết quả.
2. **Cho trước** chọn đồng thời bộ lọc HSK và trạng thái, **khi** áp dụng, **thì** chỉ hiện các từ thỏa cả hai điều kiện.
3. **Cho trước** không có từ nào thỏa bộ lọc, **khi** áp dụng, **thì** hiện "Không có từ phù hợp" kèm nút xóa bộ lọc.
4. **Cho trước** sổ tay còn trống, **khi** mở, **thì** hiện hướng dẫn "Hãy lưu từ đầu tiên khi đọc truyện" thay vì bảng rỗng.

#### Nhóm G — Flashcard và Spaced Repetition

### US-NH-38 — Xem thẻ đến hạn mỗi ngày
**Là** Người học, **tôi muốn** mở trang ôn tập và thấy các thẻ đến hạn hôm nay, **để** ôn đúng lúc cần ôn.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM] [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** có thẻ đến hạn, **khi** mở trang ôn tập, **thì** hiện số thẻ đến hạn và bắt đầu phiên ôn với thẻ đầu tiên.
2. **Cho trước** thẻ chưa đến hạn, **khi** mở trang ôn tập, **thì** thẻ đó không xuất hiện trong phiên ôn.
3. **Cho trước** thẻ thuộc từ ở trạng thái "Đã thuộc" hoặc "Bỏ qua", **khi** lập danh sách, **thì** thẻ không được đưa vào.
4. **Cho trước** số thẻ đến hạn rất nhiều, **khi** mở trang, **thì** thẻ được nạp theo từng đợt, trang không bị treo.

### US-NH-39 — Lật thẻ và tự đánh giá mức nhớ
**Là** Người học, **tôi muốn** lật thẻ và tự đánh giá mức nhớ bằng bốn mức Quên / Khó / Được / Dễ, **để** hệ thống tính lại lịch ôn cho phù hợp với trí nhớ của tôi.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM] [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** thẻ đang hiện mặt trước, **khi** bấm "Lật", **thì** hiện mặt sau và xuất hiện đủ bốn nút Quên, Khó, Được, Dễ.
2. **Cho trước** tôi chưa lật thẻ, **khi** quan sát, **thì** các nút đánh giá bị ẩn hoặc vô hiệu hóa.
3. **Cho trước** tôi chọn một mức, **khi** xác nhận, **thì** thuật toán FSRS cập nhật độ ổn định S, độ khó D và ngày ôn tiếp theo của thẻ, rồi chuyển sang thẻ kế tiếp.
4. **Cho trước** so sánh cùng một thẻ, **khi** tôi chọn "Dễ" so với "Quên", **thì** khoảng cách đến ngày ôn tiếp theo của "Dễ" dài hơn.
5. **Cho trước** mất mạng khi gửi đánh giá, **khi** gửi thất bại, **thì** hiện lỗi, thẻ giữ nguyên để chấm lại và lịch ôn không bị cập nhật một nửa.
6. **Cho trước** một thẻ bị đánh giá hai lần do bấm đúp, **khi** xử lý, **thì** chỉ tính một lượt ôn.

### US-NH-40 — Ba loại thẻ ôn tập
**Là** Người học, **tôi muốn** ôn bằng ba loại thẻ: nhận diện (Hán→Việt), nhớ lại (Việt→Hán), nghe (nghe→Hán), **để** luyện cả đọc, nhớ và nghe.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM] [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** thẻ nhận diện, **khi** hiện mặt trước, **thì** hiện chữ Hán và mặt sau là nghĩa tiếng Việt.
2. **Cho trước** thẻ nhớ lại, **khi** hiện mặt trước, **thì** hiện nghĩa tiếng Việt và mặt sau là chữ Hán kèm pinyin.
3. **Cho trước** thẻ nghe, **khi** hiện mặt trước, **thì** phát âm thanh của từ (không hiện chữ Hán) và mặt sau hiện chữ Hán kèm nghĩa.
4. **Cho trước** dịch vụ Text-to-Speech lỗi khi gặp thẻ nghe, **khi** hiện thẻ, **thì** thông báo không phát được âm thanh và cho phép bỏ qua thẻ hoặc thử lại, không làm hỏng phiên ôn.
5. **Cho trước** mỗi từ đã lưu, **khi** tạo thẻ, **thì** có đủ ba loại thẻ cho từ đó (giả định).

### US-NH-41 — Thẻ hiển thị ảnh ngữ cảnh
**Là** Người học, **tôi muốn** thẻ ôn tập hiện kèm ảnh bong bóng nơi tôi gặp từ, **để** nhớ từ nhờ ngữ cảnh truyện.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** từ có ít nhất một ngữ cảnh, **khi** lật thẻ, **thì** mặt sau hiện ảnh ngữ cảnh.
2. **Cho trước** từ có nhiều ngữ cảnh, **khi** xem thẻ, **thì** hiện một ngữ cảnh và cho phép xem các ngữ cảnh còn lại.
3. **Cho trước** từ không có ngữ cảnh, **khi** lật thẻ, **thì** thẻ vẫn hiển thị bình thường, không có ảnh trống.
4. **Cho trước** ảnh ngữ cảnh không tải được, **khi** hiện thẻ, **thì** hiện ảnh thay thế/biểu tượng lỗi và thẻ vẫn dùng được.

### US-NH-42 — Tạm ngưng và đặt lại thẻ
**Là** Người học, **tôi muốn** tạm ngưng hoặc đặt lại một thẻ, **để** kiểm soát việc ôn từ khó hoặc từ tôi muốn học lại từ đầu.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** thẻ đang hoạt động, **khi** chọn "Tạm ngưng", **thì** thẻ không còn xuất hiện trong thẻ đến hạn cho đến khi tôi bật lại.
2. **Cho trước** thẻ đang tạm ngưng, **khi** chọn "Tiếp tục", **thì** thẻ trở lại lịch ôn với ngày đến hạn tính theo trạng thái hiện tại.
3. **Cho trước** chọn "Đặt lại" và xác nhận, **khi** hoàn tất, **thì** S, D và lịch ôn của thẻ về trạng thái ban đầu như thẻ mới; lịch sử ôn cũ vẫn được giữ.
4. **Cho trước** thẻ của người khác, **khi** tôi cố tạm ngưng hoặc đặt lại, **thì** bị từ chối vì không có quyền.

### US-NH-43 — Xem lịch sử ôn của thẻ
**Là** Người học, **tôi muốn** xem lịch sử các lần ôn của một thẻ, **để** biết tôi nhớ từ đó tốt hay kém theo thời gian.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** thẻ đã ôn nhiều lần, **khi** mở lịch sử, **thì** thấy danh sách các lượt theo thứ tự thời gian, mỗi lượt có ngày giờ và mức đánh giá (Quên/Khó/Được/Dễ).
2. **Cho trước** thẻ mới chưa ôn lần nào, **khi** mở lịch sử, **thì** hiện "Chưa có lượt ôn nào".
3. **Cho trước** lịch sử dài, **khi** mở, **thì** được chia trang hoặc tải dần.
4. **Cho trước** thẻ của người khác, **khi** tôi cố xem, **thì** bị từ chối vì không có quyền.

### US-NH-44 — Thông báo hoàn thành khi hết thẻ đến hạn
**Là** Người học, **tôi muốn** được báo khi đã ôn xong mọi thẻ đến hạn, **để** biết mình đã hoàn thành việc ôn hôm nay.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi đánh giá xong thẻ cuối cùng, **khi** không còn thẻ đến hạn, **thì** hiện màn hình "Bạn đã hoàn thành ôn tập hôm nay" kèm số thẻ đã ôn.
2. **Cho trước** tôi chưa có thẻ nào, **khi** mở trang ôn tập, **thì** hiện thông báo khác: "Chưa có thẻ, hãy lưu từ khi đọc truyện".
3. **Cho trước** màn hình hoàn thành, **khi** quan sát, **thì** hiện thời điểm hoặc số thẻ sẽ đến hạn kế tiếp (nếu có).
4. **Cho trước** có thẻ mới đến hạn sau khi tôi đã hoàn thành, **khi** tải lại trang ôn, **thì** các thẻ đó hiện ra để ôn tiếp.

#### Nhóm H — Kiểm tra cá nhân hóa

### US-NH-45 — Yêu cầu làm bài kiểm tra
**Là** Người học, **tôi muốn** yêu cầu một bài kiểm tra từ sổ tay của mình, **để** đánh giá mức nhớ từ vựng thực tế.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** sổ tay có từ 10 từ trở lên, **khi** bấm "Làm bài kiểm tra", **thì** hệ thống tạo một bài gồm 10 câu (đề xuất) và chuyển tôi vào màn làm bài.
2. **Cho trước** sổ tay có dưới 10 từ, **khi** yêu cầu, **thì** từ chối với thông báo "Cần tối thiểu 10 từ trong Sổ tay cá nhân" kèm số từ hiện có.
3. **Cho trước** hệ thống chọn từ, **khi** tạo bài, **thì** ưu tiên từ sắp quên hoặc đang học, kèm một phần từ đã nhớ lâu.
4. **Cho trước** từ ở trạng thái "Bỏ qua", **khi** chọn từ ra đề, **thì** các từ này không được dùng.
5. **Cho trước** đang chờ tạo bài, **khi** quá trình kéo dài, **thì** hiện chỉ báo đang tạo và tôi nhận được bài trong tối đa khoảng 20 giây (kể cả khi phải dùng đề dự phòng).

### US-NH-46 — Làm bài và nộp bài
**Là** Người học, **tôi muốn** làm bài trắc nghiệm/điền từ và nộp bài, **để** nhận kết quả.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** bài đã tạo, **khi** làm bài, **thì** tôi thấy từng câu (trắc nghiệm hoặc điền từ), chọn/nhập đáp án và đổi được đáp án trước khi nộp.
2. **Cho trước** còn câu chưa trả lời, **khi** bấm "Nộp bài", **thì** hệ thống cảnh báo số câu chưa làm và cho chọn nộp luôn hoặc quay lại làm tiếp.
3. **Cho trước** nộp bài, **khi** đã nộp, **thì** không thể nộp lần hai cho cùng một bài.
4. **Cho trước** mất mạng khi nộp, **khi** nộp thất bại, **thì** đáp án đã chọn không mất và tôi nộp lại được.
5. **Cho trước** bài thuộc người khác, **khi** tôi cố mở hoặc nộp, **thì** bị từ chối vì không có quyền.

### US-NH-47 — Chấm điểm và xem kết quả
**Là** Người học, **tôi muốn** xem điểm, đáp án đúng và giải thích sau khi nộp, **để** biết mình sai ở đâu.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi vừa nộp bài, **khi** hệ thống chấm xong, **thì** hiện điểm (số câu đúng trên tổng số câu) do máy chủ tính.
2. **Cho trước** xem chi tiết, **khi** mở từng câu, **thì** thấy đáp án của tôi, đáp án đúng và phần giải thích.
3. **Cho trước** đáp án đúng, **khi** bài còn chưa nộp, **thì** đáp án đúng không được gửi xuống giao diện của tôi (để không thể xem trước).
4. **Cho trước** câu điền từ có nhiều cách viết tương đương (ví dụ khác khoảng trắng hoặc hoa thường của pinyin), **khi** chấm, **thì** các cách viết tương đương được chấp nhận (giả định).

### US-NH-48 — Từ làm sai được đưa vào ôn sớm
**Là** Người học, **tôi muốn** các từ tôi làm sai được ôn lại sớm hơn, **để** củng cố đúng chỗ còn yếu.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi trả lời sai một câu, **khi** bài được chấm, **thì** thẻ của từ đó được xếp lịch ôn sớm hơn và xuất hiện trong thẻ đến hạn sớm nhất.
2. **Cho trước** tôi trả lời đúng, **khi** chấm, **thì** lịch ôn của từ đó không bị kéo sớm.
3. **Cho trước** từ sai đang tạm ngưng hoặc "Đã thuộc", **khi** chấm, **thì** từ này được chuyển sang "Đang học" và hiện thông báo đã đưa vào ôn lại (giả định).
4. **Cho trước** bài đã được chấm, **khi** tôi tải lại kết quả, **thì** lịch ôn không bị tính lại lần hai.

### US-NH-49 — Xem lịch sử bài kiểm tra
**Là** Người học, **tôi muốn** xem lại các bài kiểm tra đã làm, **để** theo dõi sự tiến bộ.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi đã làm bài, **khi** mở lịch sử, **thì** thấy danh sách bài theo thứ tự mới nhất trước, mỗi bài có ngày giờ và điểm.
2. **Cho trước** chọn một bài cũ, **khi** mở, **thì** xem lại được từng câu, đáp án và giải thích.
3. **Cho trước** chưa làm bài nào, **khi** mở lịch sử, **thì** hiện "Chưa có bài kiểm tra nào".
4. **Cho trước** bài của người khác, **khi** tôi cố xem, **thì** bị từ chối vì không có quyền.

### US-NH-50 — Đề dự phòng khi dịch vụ LLM lỗi
**Là** Người học, **tôi muốn** vẫn có bài kiểm tra khi dịch vụ sinh đề gặp sự cố, **để** việc học không bị gián đoạn.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** dịch vụ LLM lỗi hoặc quá thời gian chờ, **khi** tôi yêu cầu bài, **thì** hệ thống tự sinh đề dự phòng từ dữ liệu từ điển và vẫn trả bài cho tôi.
2. **Cho trước** bài được sinh bằng đề dự phòng, **khi** làm bài, **thì** có ghi chú "Đề tạo tự động từ từ điển" để tôi biết.
3. **Cho trước** đề dự phòng, **khi** chấm, **thì** quy tắc chấm và lịch ôn sớm áp dụng giống bài thường.
4. **Cho trước** Quản trị viên đã tắt dịch vụ LLM (US-QT-13), **khi** tôi yêu cầu bài, **thì** hệ thống dùng đề dự phòng ngay, không chờ dịch vụ ngoài.

#### Nhóm I — Gợi ý từ theo chương (cá nhân hóa)

### US-NH-51 — Xem gợi ý từ nên học trong chương
**Là** Người học, **tôi muốn** xem danh sách từ nên học trong chương đang đọc, **để** ưu tiên những từ phù hợp trình độ.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** chương đã xử lý xong, **khi** mở "Từ nên học", **thì** thấy danh sách từ sắp xếp theo mức phù hợp dựa trên tần suất trong chương, trình độ HSK của tôi và lịch sử tra.
2. **Cho trước** từ đã có trong sổ tay hoặc đã "Đã thuộc", **khi** lập gợi ý, **thì** từ đó không xuất hiện trong danh sách.
3. **Cho trước** tôi chưa khai báo trình độ HSK, **khi** xem gợi ý, **thì** hiện nhắc khai báo và dùng thứ tự theo tần suất.
4. **Cho trước** chương chưa xử lý xong hoặc không có từ phù hợp, **khi** mở, **thì** hiện thông báo tương ứng thay vì danh sách trống.

### US-NH-52 — Nhận hoặc bỏ qua gợi ý
**Là** Người học, **tôi muốn** nhận một gợi ý vào sổ tay hoặc bỏ qua nó, **để** danh sách gợi ý ngày càng sát nhu cầu.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một từ trong danh sách gợi ý, **khi** bấm "Nhận", **thì** từ được lưu vào sổ tay như thao tác lưu thông thường (US-NH-31) và biến mất khỏi danh sách gợi ý.
2. **Cho trước** một từ trong danh sách gợi ý, **khi** bấm "Bỏ qua", **thì** từ biến mất và không được gợi ý lại trong các lần sau.
3. **Cho trước** từ đã nhận đã có trong sổ tay, **khi** bấm "Nhận", **thì** áp dụng quy tắc không trùng (US-NH-32).
4. **Cho trước** tôi muốn xem lại từ đã bỏ qua, **khi** mở mục "Đã bỏ qua", **thì** có thể khôi phục từ đó vào danh sách gợi ý.

#### Nhóm J — Text-to-Speech

### US-NH-53 — Nghe phát âm từ và câu
**Là** Người học, **tôi muốn** nghe phát âm của từ và câu, **để** học cách đọc đúng.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** khung Hover hoặc chi tiết từ đang mở, **khi** bấm biểu tượng loa, **thì** âm thanh phát bằng giọng đã chọn trong cài đặt.
2. **Cho trước** từ hoặc câu đã từng được nghe, **khi** bấm loa lại, **thì** âm thanh phát lại nhanh hơn lần đầu nhờ dùng bản đã lưu (cache).
3. **Cho trước** dịch vụ TTS lỗi, **khi** bấm loa, **thì** hiện thông báo "Không phát được âm thanh, thử lại sau" và trang vẫn dùng bình thường.
4. **Cho trước** văn bản trống, **khi** bấm loa, **thì** nút bị vô hiệu hóa hoặc không phát gì.

### US-NH-54 — Nghe cả đoạn hội thoại
**Là** Người học, **tôi muốn** nghe cả một đoạn hội thoại trong trang, **để** luyện nghe theo mạch hội thoại.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** trang có nhiều bong bóng hội thoại, **khi** bấm "Nghe cả trang", **thì** các bong bóng được đọc lần lượt theo thứ tự đọc của truyện.
2. **Cho trước** đang phát, **khi** bấm "Dừng", **thì** âm thanh dừng ngay.
3. **Cho trước** đang phát, **khi** đến bong bóng nào, **thì** bong bóng đó được làm nổi bật trên ảnh.
4. **Cho trước** một bong bóng lỗi tổng hợp âm thanh, **khi** phát đến, **thì** bỏ qua bong bóng đó, báo lỗi và tiếp tục các bong bóng còn lại.

### US-NH-55 — Chỉnh tốc độ đọc
**Là** Người học, **tôi muốn** chỉnh tốc độ đọc, **để** nghe chậm khi mới học hoặc nhanh khi đã quen.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** bộ điều khiển tốc độ, **khi** chọn giá trị trong khoảng 0,5x–1,5x (đề xuất), **thì** các lần phát sau dùng đúng tốc độ đó.
2. **Cho trước** tôi chọn tốc độ, **khi** mở lại ứng dụng, **thì** tốc độ đã chọn được giữ lại.
3. **Cho trước** giá trị ngoài khoảng cho phép, **khi** thiết lập, **thì** bị từ chối hoặc tự đưa về giá trị biên.
4. **Cho trước** đang phát một đoạn, **khi** đổi tốc độ, **thì** áp dụng từ lần phát kế tiếp, không làm âm thanh hiện tại bị lỗi.

#### Nhóm K — Theo dõi tiến trình

### US-NH-56 — Xem thống kê học tập
**Là** Người học, **tôi muốn** xem thống kê số từ đã lưu, số thẻ đến hạn và tỉ lệ nhớ, **để** nắm được mức tiến bộ.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi có dữ liệu học, **khi** mở trang tiến trình, **thì** thấy tổng số từ đã lưu, số thẻ đến hạn hôm nay và tỉ lệ nhớ (tỉ lệ lượt ôn không chọn "Quên").
2. **Cho trước** tôi vừa lưu thêm một từ, **khi** mở lại trang, **thì** số từ tăng đúng một.
3. **Cho trước** tôi chưa có lượt ôn nào, **khi** mở trang, **thì** tỉ lệ nhớ hiện "Chưa có dữ liệu" thay vì 0% hoặc lỗi chia cho 0.
4. **Cho trước** thống kê, **khi** hiển thị, **thì** chỉ tính dữ liệu của chính tôi.

### US-NH-57 — Chuỗi ngày học và tiến độ đọc
**Là** Người học, **tôi muốn** thấy chuỗi ngày học liên tiếp và tiến độ đọc các truyện, **để** duy trì thói quen học.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi có ôn tập hoặc đọc trong ngày, **khi** mở trang tiến trình, **thì** chuỗi ngày học tăng đúng một cho ngày đó (mỗi ngày chỉ tính một lần).
2. **Cho trước** tôi bỏ lỡ một ngày, **khi** sang ngày kế, **thì** chuỗi quay về 0 hoặc 1 theo quy tắc đã công bố trên giao diện.
3. **Cho trước** nhiều truyện đang đọc, **khi** xem tiến độ đọc, **thì** mỗi truyện hiện số trang/chương đã đọc trên tổng.
4. **Cho trước** tôi mới đăng ký, **khi** mở trang, **thì** chuỗi ngày bằng 0 và tiến độ đọc trống kèm gợi ý bắt đầu.

#### Nhóm L — Chức năng mở rộng (đề xuất)

### US-NH-58 — Báo lỗi nhận diện hoặc bản dịch
**Là** Người học, **tôi muốn** báo lỗi nhận diện/dịch của một bong bóng cho Quản trị viên, **để** chất lượng dữ liệu được cải thiện.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi đang xem một bong bóng, **khi** chọn "Báo lỗi" và mô tả vấn đề, **thì** báo lỗi được ghi nhận với trạng thái "Mới" kèm vị trí trang/bong bóng.
2. **Cho trước** để trống mô tả, **khi** gửi, **thì** bị từ chối hoặc phải chọn ít nhất một loại lỗi.
3. **Cho trước** tôi đã báo lỗi cùng bong bóng và loại lỗi còn đang xử lý, **khi** báo lại, **thì** hệ thống nhắc báo lỗi đã tồn tại.
4. **Cho trước** Quản trị viên đã xử lý báo lỗi, **khi** tôi mở danh sách báo lỗi của mình, **thì** thấy trạng thái "Đã xử lý".

### US-NH-59 — Nhắc ôn tập hằng ngày
**Là** Người học, **tôi muốn** nhận nhắc ôn tập hằng ngày, **để** không quên ôn thẻ đến hạn.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi bật nhắc nhở và chọn giờ, **khi** tới giờ đó và có thẻ đến hạn, **thì** nhận một lời nhắc ghi rõ số thẻ cần ôn.
2. **Cho trước** không có thẻ đến hạn, **khi** tới giờ nhắc, **thì** không gửi lời nhắc.
3. **Cho trước** tôi tắt nhắc nhở, **khi** tới giờ, **thì** không nhận lời nhắc.
4. **Cho trước** tôi đã ôn xong trong ngày, **khi** tới giờ nhắc, **thì** không gửi lời nhắc.

### US-NH-60 — Xuất sổ tay ra CSV hoặc Anki
**Là** Người học, **tôi muốn** xuất Sổ tay cá nhân ra CSV hoặc định dạng Anki, **để** dùng dữ liệu ở công cụ khác hoặc sao lưu.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** sổ tay có từ, **khi** chọn xuất CSV, **thì** nhận tệp có một dòng cho mỗi từ gồm chữ Hán, pinyin, nghĩa, cấp độ HSK, trạng thái và ghi chú.
2. **Cho trước** chọn xuất Anki, **khi** hoàn tất, **thì** nhận tệp nhập được vào Anki với mặt trước/mặt sau đúng như thẻ nhận diện.
3. **Cho trước** sổ tay trống, **khi** bấm xuất, **thì** hiện thông báo "Sổ tay chưa có từ để xuất".
4. **Cho trước** đang áp dụng bộ lọc, **khi** xuất, **thì** chỉ xuất các từ thỏa bộ lọc (hoặc hỏi xuất toàn bộ).
5. **Cho trước** từ có tiếng Việt và chữ Hán, **khi** mở tệp CSV, **thì** ký tự hiển thị đúng, không bị lỗi mã hóa.

---

## 5. Quản trị viên

**Kế thừa.** Quản trị viên kế thừa toàn bộ hành vi của Người học (US-NH-01 … US-NH-60): có thể đăng nhập, đọc, tra cứu, lưu từ, ôn tập, làm kiểm tra như Người học và được áp dụng cùng tiêu chí chấp nhận, nên không viết lại ở đây. Các story dưới đây chỉ mô tả quyền bổ sung. Riêng quy tắc sở hữu (US-NH-15) được mở rộng: Quản trị viên được sửa/xóa bất kỳ truyện nào (US-QT-05).

### US-QT-01 — Xem và tìm người dùng
**Là** Quản trị viên, **tôi muốn** xem và tìm danh sách người dùng, **để** quản lý tài khoản trong hệ thống.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi là Quản trị viên, **khi** mở trang quản lý người dùng, **thì** thấy danh sách có chia trang, gồm email, vai trò, trạng thái (hoạt động/khóa) và ngày tham gia.
2. **Cho trước** nhập một phần email, **khi** tìm kiếm, **thì** chỉ hiện người dùng khớp; không khớp thì hiện "Không tìm thấy người dùng".
3. **Cho trước** tôi là Người học, **khi** truy cập trang này, **thì** bị từ chối với thông báo không có quyền.
4. **Cho trước** danh sách người dùng, **khi** hiển thị, **thì** không lộ mật khẩu hay dữ liệu học tập riêng (sổ tay, đáp án) của họ.

### US-QT-02 — Đổi vai trò người dùng
**Là** Quản trị viên, **tôi muốn** đổi vai trò của người dùng giữa Người học và Quản trị viên, **để** phân quyền quản trị.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một Người học, **khi** nâng lên Quản trị viên, **thì** từ lần đăng nhập/làm mới phiên tiếp theo người đó có quyền quản trị.
2. **Cho trước** tôi chọn đổi vai trò của chính mình từ Quản trị viên xuống Người học, **khi** xác nhận, **thì** bị từ chối với thông báo "Không thể tự hạ quyền chính mình".
3. **Cho trước** thao tác đổi vai trò thành công, **khi** hoàn tất, **thì** thay đổi được ghi nhận kèm người thực hiện và thời điểm.
4. **Cho trước** tôi là Người học, **khi** cố đổi vai trò, **thì** bị từ chối vì không có quyền.

### US-QT-03 — Khóa và mở khóa tài khoản
**Là** Quản trị viên, **tôi muốn** khóa hoặc mở khóa tài khoản, **để** ngăn người dùng vi phạm sử dụng hệ thống.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một tài khoản đang hoạt động, **khi** khóa, **thì** người đó không đăng nhập được (US-KH-03) và các phiên hiện có bị thu hồi.
2. **Cho trước** tài khoản đang bị khóa, **khi** mở khóa, **thì** người đó đăng nhập lại được và dữ liệu cũ còn nguyên.
3. **Cho trước** tôi chọn khóa chính tài khoản của mình, **khi** xác nhận, **thì** bị từ chối với thông báo "Không thể tự khóa chính mình".
4. **Cho trước** thao tác khóa/mở khóa, **khi** thực hiện, **thì** có hộp thoại xác nhận và được ghi nhận người thực hiện, thời điểm.

### US-QT-04 — Đăng truyện công khai
**Là** Quản trị viên, **tôi muốn** đăng truyện ở chế độ công khai, **để** mọi Người học và Khách (nếu chương cho đọc thử) có thể đọc.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi tạo truyện và chọn "Công khai", **khi** lưu, **thì** truyện xuất hiện trong thư viện chung của mọi Người học.
2. **Cho trước** truyện công khai chưa có chương nào, **khi** Người học duyệt thư viện, **thì** truyện chưa hiển thị trong thư viện chung cho đến khi có ít nhất 1 chương; Quản trị viên vẫn thấy truyện kèm nhãn "Chưa có chương".
3. **Cho trước** tôi chuyển truyện công khai về riêng tư, **khi** lưu, **thì** truyện biến mất khỏi thư viện chung của người khác, còn từ đã lưu của họ giữ ngữ cảnh ảnh đã cắt.
4. **Cho trước** tôi là Người học, **khi** cố đăng truyện công khai, **thì** bị từ chối vì không có quyền.

### US-QT-05 — Sửa và xóa bất kỳ truyện
**Là** Quản trị viên, **tôi muốn** sửa và xóa bất kỳ truyện nào trong hệ thống, **để** xử lý nội dung sai hoặc vi phạm.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** truyện của người khác (công khai hoặc riêng tư), **khi** tôi sửa tên/chương/trang, **thì** thay đổi được lưu và hiển thị với chủ truyện.
2. **Cho trước** tôi xóa một truyện, **khi** xác nhận, **thì** truyện cùng chương, trang, ảnh liên quan bị xóa và thao tác được ghi nhận.
3. **Cho trước** truyện bị xóa, **khi** Người học có từ lưu từ truyện đó, **thì** từ, ngữ cảnh ảnh đã cắt và flashcard của họ vẫn còn.
4. **Cho trước** hủy ở hộp thoại xác nhận, **khi** hủy, **thì** không có dữ liệu nào bị xóa.

### US-QT-06 — Giám sát xử lý ảnh
**Là** Quản trị viên, **tôi muốn** xem danh sách trang theo trạng thái xử lý, **để** theo dõi tình trạng hàng đợi và phát hiện sự cố.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi mở trang giám sát, **khi** lọc theo Đang chờ / Đang xử lý / Xong / Lỗi, **thì** chỉ hiện các trang thuộc trạng thái đã chọn kèm số lượng từng nhóm.
2. **Cho trước** một trang ở trạng thái "Lỗi", **khi** xem chi tiết, **thì** thấy lý do lỗi do pipeline ghi lại.
3. **Cho trước** không có trang nào ở trạng thái được lọc, **khi** lọc, **thì** hiện "Không có trang nào".
4. **Cho trước** tôi là Người học, **khi** truy cập trang giám sát, **thì** bị từ chối.

### US-QT-07 — Chạy lại trang lỗi
**Là** Quản trị viên, **tôi muốn** chạy lại việc xử lý các trang bị lỗi, **để** khôi phục chúng sau khi khắc phục sự cố.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một trang ở trạng thái "Lỗi", **khi** bấm "Chạy lại", **thì** trang chuyển sang "Đang chờ" và vào hàng đợi.
2. **Cho trước** chọn nhiều trang lỗi cùng lúc, **khi** chạy lại hàng loạt, **thì** mỗi trang được xếp hàng đúng một lần và kết quả từng trang được báo riêng.
3. **Cho trước** trang không ở trạng thái "Lỗi", **khi** bấm "Chạy lại", **thì** bị từ chối với thông báo trang đang không lỗi.
4. **Cho trước** chạy lại vẫn lỗi, **khi** hoàn tất, **thì** lý do lỗi mới được ghi đè lên lý do cũ.

### US-QT-08 — Xem thống kê toàn hệ thống
**Là** Quản trị viên, **tôi muốn** xem thống kê toàn hệ thống, **để** đánh giá mức sử dụng và chất lượng.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi mở trang thống kê, **khi** hiển thị, **thì** thấy tối thiểu: số người dùng, số truyện, số trang theo từng trạng thái xử lý và số từ đã lưu toàn hệ thống.
2. **Cho trước** hệ thống mới, chưa có dữ liệu, **khi** mở thống kê, **thì** các số hiện 0, không báo lỗi.
3. **Cho trước** thống kê, **khi** hiển thị, **thì** chỉ là số liệu tổng hợp, không lộ nội dung sổ tay hay đáp án của từng người học.
4. **Cho trước** tôi là Người học, **khi** mở trang này, **thì** bị từ chối.

### US-QT-09 — Nạp và cập nhật dữ liệu từ điển
**Là** Quản trị viên, **tôi muốn** nạp và cập nhật dữ liệu từ điển, **để** nội dung tra cứu luôn đầy đủ và chính xác.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tệp từ điển đúng định dạng, **khi** nạp, **thì** các mục mới được thêm và mục đã có được cập nhật; hệ thống báo số mục thêm mới, cập nhật và bỏ qua.
2. **Cho trước** tệp sai định dạng hoặc hỏng, **khi** nạp, **thì** bị từ chối với thông báo lỗi và dữ liệu hiện có không bị thay đổi.
3. **Cho trước** nạp lại cùng một tệp lần hai, **khi** hoàn tất, **thì** không sinh mục trùng (kết quả giống lần đầu).
4. **Cho trước** quá trình nạp bị gián đoạn giữa chừng, **khi** xảy ra, **thì** hệ thống không để từ điển ở trạng thái nửa chừng (hoàn tác toàn bộ lần nạp đó).
5. **Cho trước** tôi là Người học, **khi** cố nạp, **thì** bị từ chối.

### US-QT-10 — Nạp và cập nhật danh sách từ HSK
**Là** Quản trị viên, **tôi muốn** nạp và cập nhật danh sách từ theo cấp độ HSK, **để** hệ thống tự xác định đúng cấp HSK khi người học lưu từ.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM] [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tệp danh sách HSK hợp lệ, **khi** nạp, **thì** mỗi từ được gán cấp từ 1 đến 9 và hệ thống báo số từ theo từng cấp.
2. **Cho trước** tệp có cấp ngoài 1–9 hoặc thiếu cấp, **khi** nạp, **thì** những dòng sai bị liệt kê và bỏ qua; các dòng đúng vẫn được nạp, và giao diện báo số dòng đã nạp / bị bỏ qua.
3. **Cho trước** danh sách HSK đã được cập nhật, **khi** Người học lưu một từ mới, **thì** cấp HSK gán theo danh sách mới.
4. **Cho trước** cập nhật làm đổi cấp của từ đã có trong sổ tay, **khi** hoàn tất, **thì** cấp HSK của các từ đó được cập nhật tương ứng.

### US-QT-11 — Xử lý báo lỗi của Người học
**Là** Quản trị viên, **tôi muốn** xem và xử lý các báo lỗi nhận diện/dịch, **để** cải thiện chất lượng và phản hồi cho Người học.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** có báo lỗi mới, **khi** mở danh sách, **thì** thấy báo lỗi kèm trang, bong bóng, mô tả và người báo, lọc được theo trạng thái.
2. **Cho trước** một báo lỗi, **khi** tôi đổi trạng thái sang "Đã xử lý" hoặc "Từ chối" và ghi chú, **thì** Người học thấy trạng thái cập nhật (US-NH-58).
3. **Cho trước** báo lỗi liên quan đến trang xử lý sai, **khi** tôi bấm "Chạy lại", **thì** áp dụng quy tắc của US-QT-07.
4. **Cho trước** tôi là Người học, **khi** cố mở danh sách báo lỗi chung, **thì** bị từ chối.

### US-QT-12 — Kiểm duyệt ảnh tải lên
**Là** Quản trị viên, **tôi muốn** kiểm duyệt và gỡ ảnh tải lên vi phạm, **để** hệ thống không chứa nội dung không phù hợp.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** danh sách ảnh/trang mới tải lên, **khi** tôi xem, **thì** xem được ảnh và thông tin người tải.
2. **Cho trước** một ảnh vi phạm, **khi** tôi gỡ ảnh kèm lý do, **thì** ảnh không còn hiển thị với bất kỳ ai và chủ ảnh nhận thông báo có lý do.
3. **Cho trước** ảnh đã bị gỡ, **khi** Người học có từ lưu từ ảnh đó, **thì** từ và flashcard vẫn còn nhưng ngữ cảnh ảnh được ẩn.
4. **Cho trước** thao tác gỡ, **khi** thực hiện, **thì** được ghi nhận người thực hiện, thời điểm, lý do.

### US-QT-13 — Cấu hình dịch vụ LLM và TTS
**Là** Quản trị viên, **tôi muốn** bật/tắt dịch vụ LLM và TTS và giới hạn số đề mỗi ngày, **để** kiểm soát chi phí và độ ổn định.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** tôi tắt LLM, **khi** Người học yêu cầu bài kiểm tra, **thì** hệ thống dùng đề dự phòng (US-NH-50).
2. **Cho trước** tôi đặt giới hạn N đề mỗi ngày cho mỗi Người học, **khi** một người yêu cầu đề thứ N+1 trong ngày, **thì** bị từ chối với thông báo đã hết lượt hôm nay và thời điểm được tạo lại.
3. **Cho trước** tôi tắt TTS, **khi** Người học bấm nghe, **thì** hiện thông báo tính năng đang tạm tắt, các chức năng khác không bị ảnh hưởng.
4. **Cho trước** giá trị giới hạn không hợp lệ (âm hoặc không phải số), **khi** lưu, **thì** bị từ chối với thông báo cụ thể.

---

## 6. Pipeline xử lý ảnh (actor phụ, story hệ thống)

### US-XL-01 — Nhận việc từ hàng đợi và xử lý tuần tự
**Là** Pipeline xử lý ảnh, **tôi cần** nhận các yêu cầu xử lý từ hàng đợi và xử lý lần lượt, **để** tài nguyên không bị quá tải và mọi trang đều được xử lý theo thứ tự.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** nhiều trang ở trạng thái "Đang chờ", **khi** pipeline hoạt động, **thì** chỉ một trang ở trạng thái "Đang xử lý" tại một thời điểm và các trang được lấy theo thứ tự vào hàng đợi.
2. **Cho trước** hàng đợi trống, **khi** pipeline chờ, **thì** không tiêu tốn tài nguyên xử lý và sẵn sàng nhận việc mới ngay khi có.
3. **Cho trước** pipeline bị dừng đột ngột khi đang xử lý một trang, **khi** khởi động lại, **thì** trang đó không bị kẹt ở "Đang xử lý" mà được đưa lại vào hàng đợi hoặc đánh dấu "Lỗi" kèm lý do.
4. **Cho trước** một trang lỗi, **khi** pipeline gặp lỗi, **thì** các trang tiếp theo trong hàng đợi vẫn được xử lý bình thường.

### US-XL-02 — Phát hiện bong bóng chữ
**Là** Pipeline xử lý ảnh, **tôi cần** phát hiện các bong bóng chữ và phân loại thành bốn loại (hội thoại, hiệu ứng âm thanh, thư pháp, chữ nổi), **để** áp dụng cách xử lý phù hợp cho từng loại.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** ảnh trang có bong bóng, **khi** phát hiện, **thì** mỗi bong bóng nhận đúng một trong bốn loại và có vùng bao xác định trên ảnh.
2. **Cho trước** ảnh không có bong bóng nào, **khi** phát hiện, **thì** trả về danh sách rỗng và trang kết thúc ở "Xong" với ghi chú không có văn bản.
3. **Cho trước** hai bong bóng chồng lấn nhau, **khi** phát hiện, **thì** mỗi bong bóng vẫn có vùng riêng, không bị gộp nhầm thành một.
4. **Cho trước** ảnh bị hỏng hoặc không đọc được, **khi** phát hiện, **thì** trang chuyển "Lỗi" kèm lý do "Không đọc được ảnh".

### US-XL-03 — Nhận dạng ký tự (OCR)
**Là** Pipeline xử lý ảnh, **tôi cần** nhận dạng chữ tiếng Trung trong từng bong bóng, **để** có văn bản làm đầu vào cho tách từ và dịch.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một bong bóng chứa chữ tiếng Trung rõ nét, **khi** OCR, **thì** trả về chuỗi văn bản đúng thứ tự đọc của bong bóng.
2. **Cho trước** bong bóng có chữ xếp dọc, **khi** OCR, **thì** văn bản được đọc theo đúng chiều dọc từ trên xuống, từ phải sang trái (giả định theo truyện tranh Trung Quốc).
3. **Cho trước** OCR không nhận ra chữ nào trong một bong bóng, **khi** xong, **thì** bong bóng đó bị bỏ qua (không có văn bản), các bong bóng khác vẫn được xử lý.
4. **Cho trước** bong bóng chứa chữ không phải tiếng Trung (ví dụ chữ Latin), **khi** OCR, **thì** văn bản đó không được đưa vào bước dịch tiếng Trung.

### US-XL-04 — Tách từ và gắn mục từ điển
**Là** Pipeline xử lý ảnh, **tôi cần** tách văn bản thành từ và gắn mục từ điển cho từng từ, **để** chức năng Hover & Dịch hiển thị tức thì mà không phải tra lúc đọc.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** văn bản của một bong bóng, **khi** tách từ, **thì** mỗi từ có vị trí trong câu, pinyin và liên kết tới mục từ điển (nếu có).
2. **Cho trước** từ không có trong từ điển, **khi** gắn, **thì** từ vẫn được ghi nhận nhưng đánh dấu "Chưa có mục từ điển" để Hover hiển thị đúng thông báo.
3. **Cho trước** thuật ngữ tu tiên có trong từ điển chuyên ngành, **khi** tách và gắn, **thì** ưu tiên mục từ điển chuyên ngành nếu thuật ngữ đó khớp.
4. **Cho trước** kết quả tách từ đã tạo, **khi** Người học rê chuột, **thì** dữ liệu được dùng ngay để hiện trong dưới 1 giây.

### US-XL-05 — Dịch Trung→Việt ngoại tuyến
**Là** Pipeline xử lý ảnh, **tôi cần** dịch văn bản tiếng Trung sang tiếng Việt bằng bộ dữ liệu offline VietPhrase, Luật nhân, Names và Phiên âm, **để** có bản dịch mà không phụ thuộc dịch vụ ngoài.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** văn bản tiếng Trung đã OCR, **khi** dịch, **thì** thu được bản dịch tiếng Việt cho từng bong bóng, hoạt động được khi không có kết nối mạng ra ngoài.
2. **Cho trước** văn bản chứa tên riêng có trong Names, **khi** dịch, **thì** tên được dịch theo Names (ưu tiên hơn VietPhrase).
3. **Cho trước** từ không có trong bộ dữ liệu dịch, **khi** dịch, **thì** từ đó được chuyển bằng Phiên âm (Hán Việt) thay vì để trống hoặc giữ nguyên chữ Hán.
4. **Cho trước** bộ dữ liệu dịch thiếu hoặc không đọc được, **khi** dịch, **thì** trang chuyển "Lỗi" kèm lý do nêu rõ dữ liệu bị thiếu.

### US-XL-06 — Xóa chữ gốc và đắp chữ Việt
**Là** Pipeline xử lý ảnh, **tôi cần** xóa chữ gốc (inpaint) và đắp bản dịch tiếng Việt lên ảnh, **để** tạo ảnh đã xóa chữ và ảnh đã dịch cho Người học.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** các bong bóng đã dịch, **khi** hoàn tất, **thì** tạo ra hai ảnh bổ sung: ảnh đã xóa chữ (không còn chữ gốc) và ảnh đã đắp chữ Việt, ảnh gốc được giữ nguyên.
2. **Cho trước** bản dịch dài hơn vùng bong bóng, **khi** đắp chữ, **thì** chữ được tự xuống dòng và/hoặc thu nhỏ để nằm trọn trong bong bóng.
3. **Cho trước** văn bản có dấu tiếng Việt, **khi** đắp chữ, **thì** mọi dấu thanh, dấu mũ hiển thị đầy đủ, không bị lỗi ô vuông.
4. **Cho trước** lỗi ghi ảnh (hết dung lượng lưu trữ), **khi** lưu kết quả, **thì** trang chuyển "Lỗi" kèm lý do và không để lại ảnh nửa chừng.

### US-XL-07 — Cập nhật trạng thái và ghi lý do lỗi
**Là** Pipeline xử lý ảnh, **tôi cần** cập nhật trạng thái chờ → đang chạy → xong/lỗi cho từng trang và ghi lý do khi lỗi, **để** Người học và Quản trị viên theo dõi được tiến độ.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một trang vào hàng đợi, **khi** pipeline xử lý, **thì** trạng thái đi qua Đang chờ → Đang xử lý → Xong (hoặc Lỗi) theo đúng thứ tự, không nhảy bước.
2. **Cho trước** một bước xử lý thất bại, **khi** ghi lỗi, **thì** lý do lỗi được lưu kèm tên bước và thông điệp ngắn gọn.
3. **Cho trước** trang "Xong", **khi** kiểm tra, **thì** trang không còn lý do lỗi từ lần xử lý trước.
4. **Cho trước** trạng thái đổi, **khi** Người học đang xem danh sách trang, **thì** thay đổi hiện ra trong lần làm mới kế tiếp mà không cần thao tác khác.

### US-XL-08 — Chống xử lý lại ảnh trùng
**Là** Pipeline xử lý ảnh, **tôi cần** nhận biết ảnh trùng đã xử lý, **để** không tốn tài nguyên xử lý lại và tiết kiệm lưu trữ.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một ảnh có nội dung giống hệt ảnh đã xử lý xong, **khi** nhận yêu cầu, **thì** không chạy lại các bước nặng mà dùng lại kết quả đã có.
2. **Cho trước** ảnh trùng nhưng thuộc Người học khác, **khi** dùng lại kết quả, **thì** dữ liệu cá nhân (bản sửa dịch, sổ tay) của người đầu không bị chia sẻ.
3. **Cho trước** ảnh chỉ giống ở tên tệp nhưng khác nội dung, **khi** nhận, **thì** vẫn xử lý như ảnh mới.
4. **Cho trước** kết quả cũ đã hỏng hoặc bị xóa, **khi** phát hiện trùng, **thì** hệ thống xử lý lại từ đầu thay vì dùng kết quả hỏng.

### US-XL-09 — Cung cấp tọa độ bong bóng để cắt ảnh ngữ cảnh
**Là** Pipeline xử lý ảnh, **tôi cần** lưu và cung cấp tọa độ từng bong bóng, **để** hệ thống cắt đúng ảnh ngữ cảnh khi Người học lưu từ.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM] [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** trang đã xử lý, **khi** Người học lưu từ trong một bong bóng, **thì** ảnh cắt theo tọa độ chứa trọn bong bóng đó, không lẫn bong bóng khác.
2. **Cho trước** tọa độ nằm ngoài kích thước ảnh, **khi** cắt, **thì** bị chặn lại và hệ thống tiếp tục lưu từ không kèm ảnh (xem US-NH-31, tiêu chí 4).
3. **Cho trước** tọa độ, **khi** áp lên ảnh gốc và ảnh đã dịch, **thì** đều trỏ đúng cùng vị trí bong bóng vì hai ảnh cùng kích thước.
4. **Cho trước** trang được xử lý lại và tọa độ thay đổi, **khi** hoàn tất, **thì** ngữ cảnh ảnh đã cắt trước đó trong sổ tay không bị thay đổi.

---

## 7. Dịch vụ Text-to-Speech bên ngoài (actor phụ, story hệ thống)

### US-TTS-01 — Tổng hợp âm thanh từ văn bản
**Là** Dịch vụ Text-to-Speech (Microsoft Edge TTS), **tôi cần** nhận văn bản và giọng đọc rồi trả về âm thanh, **để** hệ thống phát được phát âm cho Người học.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** văn bản tiếng Trung hợp lệ và một giọng, **khi** hệ thống gọi dịch vụ, **thì** nhận được âm thanh đọc đúng văn bản bằng giọng đó và tốc độ yêu cầu.
2. **Cho trước** văn bản rỗng, **khi** gọi, **thì** hệ thống không gọi dịch vụ ngoài và báo thiếu nội dung.
3. **Cho trước** văn bản quá dài so với giới hạn, **khi** gọi, **thì** hệ thống chia nhỏ hoặc từ chối với thông báo giới hạn độ dài.
4. **Cho trước** giọng không tồn tại, **khi** gọi, **thì** hệ thống dùng giọng mặc định và ghi nhận cảnh báo.

### US-TTS-02 — Lưu cache âm thanh
**Là** Dịch vụ Text-to-Speech, **tôi cần** hệ thống lưu âm thanh đã tạo theo cặp (văn bản, giọng, tốc độ), **để** các lần nghe sau không phải gọi lại dịch vụ ngoài.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** một cặp (văn bản, giọng, tốc độ) đã có trong cache, **khi** được yêu cầu, **thì** hệ thống trả âm thanh đã lưu và không gọi dịch vụ ngoài.
2. **Cho trước** cùng văn bản nhưng khác giọng hoặc khác tốc độ, **khi** yêu cầu, **thì** tạo bản âm thanh mới, không dùng nhầm bản cũ.
3. **Cho trước** tệp trong cache bị hỏng hoặc mất, **khi** yêu cầu, **thì** hệ thống tạo lại âm thanh và thay thế bản hỏng.
4. **Cho trước** nhiều Người học yêu cầu cùng một văn bản cùng lúc, **khi** chưa có cache, **thì** chỉ gọi dịch vụ ngoài một lần cho cả nhóm yêu cầu đó.

### US-TTS-03 — Xử lý khi dịch vụ TTS lỗi
**Là** Dịch vụ Text-to-Speech, **tôi cần** hệ thống xử lý nhẹ nhàng khi tôi không phản hồi hoặc trả lỗi, **để** trang của Người học không bị hỏng.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** dịch vụ không phản hồi hoặc trả lỗi, **khi** Người học bấm nghe, **thì** hiện thông báo "Không phát được âm thanh, thử lại sau" và mọi chức năng khác (Hover, lưu từ, ôn tập) vẫn dùng bình thường.
2. **Cho trước** hệ thống không có kết nối ra ngoài, **khi** yêu cầu âm thanh chưa có trong cache, **thì** báo lỗi như trên; âm thanh đã có trong cache vẫn phát được.
3. **Cho trước** lỗi xảy ra, **khi** ghi nhận, **thì** nhật ký có lý do lỗi để Quản trị viên tra cứu.
4. **Cho trước** lần gọi lỗi, **khi** xảy ra, **thì** không lưu tệp âm thanh rỗng/hỏng vào cache.

---

## 8. Dịch vụ LLM bên ngoài (actor phụ, story hệ thống)

### US-LLM-01 — Sinh bộ đề kiểm tra
**Là** Dịch vụ LLM, **tôi cần** nhận danh sách từ (chỉ gồm từ và nghĩa) và trả về bộ đề kiểm tra, **để** hệ thống tạo bài cá nhân hóa cho Người học.

- **Độ ưu tiên:** Should   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** danh sách từ đã chọn, **khi** hệ thống gửi yêu cầu, **thì** nội dung gửi đi chỉ chứa từ và nghĩa, không chứa email, tên, mã người dùng hay thông tin cá nhân nào khác.
2. **Cho trước** yêu cầu hợp lệ, **khi** dịch vụ phản hồi, **thì** trả về bộ đề dạng JSON theo lược đồ cố định (loại câu, nội dung câu hỏi, các lựa chọn, đáp án đúng, giải thích).
3. **Cho trước** bộ đề được tạo, **khi** quan sát, **thì** mỗi từ đã chọn có ít nhất một câu hỏi và tổng số câu khớp số câu yêu cầu.
4. **Cho trước** nhật ký hệ thống, **khi** ghi yêu cầu gửi LLM, **thì** không ghi dữ liệu cá nhân của Người học.

### US-LLM-02 — Kiểm tra lược đồ và đối chiếu đáp án
**Là** Dịch vụ LLM, **tôi cần** hệ thống kiểm tra kết quả của tôi trước khi dùng, **để** đảm bảo đề có cấu trúc đúng và đáp án chính xác.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** JSON trả về, **khi** kiểm tra, **thì** hệ thống xác nhận đúng lược đồ (đủ trường, đúng kiểu, đáp án nằm trong các lựa chọn); sai lược đồ thì bị coi là không hợp lệ.
2. **Cho trước** đề hợp lệ về cấu trúc, **khi** đối chiếu đáp án với từ điển, **thì** câu có đáp án mâu thuẫn với nghĩa trong từ điển bị loại.
3. **Cho trước** đề không hợp lệ ở lần đầu, **khi** xử lý, **thì** hệ thống sinh lại tối đa 1 lần.
4. **Cho trước** đề vẫn không hợp lệ sau lần sinh lại, **khi** xử lý, **thì** chuyển sang đề dự phòng (US-LLM-03) và không sinh lại lần nữa.

### US-LLM-03 — Giới hạn thời gian chờ và dùng đề dự phòng
**Là** Dịch vụ LLM, **tôi cần** hệ thống giới hạn thời gian chờ tôi và có phương án thay thế, **để** Người học không phải chờ vô hạn.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [Luồng 3]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** dịch vụ không phản hồi trong 20 giây, **khi** hết thời gian, **thì** hệ thống hủy chờ và chuyển sang đề dự phòng sinh từ dữ liệu từ điển.
2. **Cho trước** dịch vụ trả lỗi (mất kết nối, lỗi phía dịch vụ, hết hạn mức), **khi** nhận lỗi, **thì** chuyển ngay sang đề dự phòng mà không báo lỗi kỹ thuật cho Người học.
3. **Cho trước** đề dự phòng, **khi** tạo, **thì** có số câu và loại câu giống yêu cầu ban đầu để Người học vẫn làm được bài đầy đủ.
4. **Cho trước** sự cố dịch vụ, **khi** ghi nhận, **thì** nhật ký ghi nguyên nhân (hết thời gian, lỗi cấu trúc, lỗi mạng) để Quản trị viên tra cứu.

---

## 9. Bộ hẹn giờ hệ thống (actor phụ, story hệ thống)

### US-HG-01 — Dọn ảnh tải nhanh hết hạn và phiên đăng nhập hết hạn
**Là** Bộ hẹn giờ hệ thống, **tôi cần** định kỳ mỗi 60 phút xóa ảnh tải nhanh quá 7 ngày và dọn phiên đăng nhập hết hạn, **để** giải phóng lưu trữ và giữ dữ liệu phiên gọn.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [TM]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** ảnh tải nhanh đã lưu quá 7 ngày, **khi** đến chu kỳ chạy 60 phút, **thì** ảnh và các sản phẩm xử lý của nó (ảnh xóa chữ, ảnh dịch) bị xóa.
2. **Cho trước** ảnh tải nhanh mới dưới 7 ngày, **khi** bộ hẹn giờ chạy, **thì** ảnh được giữ nguyên.
3. **Cho trước** ảnh thuộc chương của truyện (không phải tải nhanh), **khi** bộ hẹn giờ chạy, **thì** không bị xóa dù đã lâu.
4. **Cho trước** phiên đăng nhập đã hết hạn, **khi** bộ hẹn giờ chạy, **thì** bản ghi phiên bị xóa; phiên còn hạn không bị ảnh hưởng.
5. **Cho trước** một lần chạy gặp lỗi giữa chừng, **khi** xảy ra, **thì** lỗi được ghi nhật ký và lần chạy kế tiếp (sau 60 phút) vẫn thực hiện bình thường.
6. **Cho trước** từ trong sổ tay có ngữ cảnh cắt từ ảnh tải nhanh, **khi** ảnh gốc bị xóa, **thì** ảnh ngữ cảnh đã cắt của từ vẫn được giữ.

### US-HG-02 — Đưa thẻ đến hạn theo lịch FSRS
**Là** Bộ hẹn giờ hệ thống, **tôi cần** đảm bảo khi đến thời điểm ôn dự kiến thì thẻ trở thành "đến hạn", **để** Người học thấy đúng các thẻ cần ôn theo lịch FSRS.

- **Độ ưu tiên:** Must   ·   **Nguồn:** [Luồng 2]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** thẻ có thời điểm ôn tiếp theo là T, **khi** thời gian hiện tại đạt hoặc vượt T, **thì** thẻ xuất hiện trong danh sách thẻ đến hạn của Người học.
2. **Cho trước** thẻ có T ở tương lai, **khi** Người học mở trang ôn, **thì** thẻ không xuất hiện.
3. **Cho trước** thẻ bị tạm ngưng hoặc thuộc từ "Đã thuộc"/"Bỏ qua", **khi** đến T, **thì** thẻ không trở thành đến hạn.
4. **Cho trước** Người học ở múi giờ khác nhau, **khi** xác định "hôm nay", **thì** dùng một quy tắc múi giờ nhất quán đã công bố (giả định: múi giờ của Người học).

### US-HG-03 — Tối ưu tham số FSRS riêng cho từng Người học
**Là** Bộ hẹn giờ hệ thống, **tôi cần** định kỳ tối ưu lại tham số FSRS cho từng Người học đã có đủ nhiều lượt ôn, **để** lịch ôn sát với trí nhớ thực tế của từng người.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** Người học có từ vài trăm lượt ôn trở lên (ngưỡng cụ thể do nhóm quyết định), **khi** đến chu kỳ tối ưu, **thì** tham số FSRS riêng của người đó được tính lại và lưu.
2. **Cho trước** Người học chưa đủ lượt ôn, **khi** đến chu kỳ, **thì** giữ tham số mặc định chung.
3. **Cho trước** tham số mới tính ra không hợp lệ hoặc làm lịch ôn bất thường, **khi** kiểm tra, **thì** hệ thống giữ tham số cũ và ghi nhật ký.
4. **Cho trước** tham số đã đổi, **khi** tính lịch ôn cho lượt đánh giá tiếp theo, **thì** dùng tham số mới; lịch của các thẻ đã xếp trước đó không bị tính lại hàng loạt.

### US-HG-04 — Gửi nhắc ôn tập hằng ngày
**Là** Bộ hẹn giờ hệ thống, **tôi cần** gửi nhắc ôn tập hằng ngày cho Người học đã bật nhắc nhở, **để** họ duy trì việc ôn đều đặn.

- **Độ ưu tiên:** Could   ·   **Nguồn:** [Đề xuất]

**Tiêu chí chấp nhận (Acceptance Criteria):**
1. **Cho trước** Người học bật nhắc nhở với giờ H và có thẻ đến hạn, **khi** đến giờ H, **thì** gửi đúng một lời nhắc trong ngày kèm số thẻ cần ôn.
2. **Cho trước** Người học không có thẻ đến hạn hoặc đã ôn xong, **khi** đến giờ H, **thì** không gửi.
3. **Cho trước** gửi nhắc thất bại (ví dụ email lỗi), **khi** xảy ra, **thì** ghi nhật ký và không gửi lặp nhiều lần trong ngày.
4. **Cho trước** tài khoản bị khóa, **khi** đến giờ H, **thì** không gửi nhắc.

---

## 10. Ma trận truy vết: chức năng thuyết minh → user story

| Chức năng thuyết minh | User story liên quan |
|---|---|
| Nhận diện văn bản | US-NH-12, 13, 17, 18, 19, 20, 21; US-XL-01 … 09; US-QT-06, 07; US-HG-01 |
| Hover & Dịch | US-KH-05; US-NH-22, 23, 24, 25; US-XL-04, 05 |
| Tra cứu đa chiều | US-NH-26, 27, 28, 29; US-QT-09; US-XL-04 |
| Phân rã chữ Hán | US-NH-30 |
| Sổ tay | US-NH-31, 32, 33, 34, 35, 36, 37, 51, 52, 60; US-QT-10; US-XL-09 |
| Flashcard & SRS | US-NH-38, 39, 40, 41, 42, 43, 44, 48; US-HG-02, 03; US-NH-45 … 50 (kiểm tra); US-LLM-01 … 03 |
| TTS | US-NH-08, 53, 54, 55; US-TTS-01 … 03; US-QT-13 |
| Cá nhân hóa | US-NH-06, 07, 08, 45 … 52, 59; US-HG-03, 04 |
| UI/UX | US-KH-01; US-NH-07, 16, 19, 22, 23, 56, 57; US-QT-08 |
| Quản lý tài khoản và thư viện (hỗ trợ) | US-KH-02, 03, 06; US-NH-01 … 05, 09 … 16; US-QT-01 … 05 |
