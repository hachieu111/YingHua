# Quy tắc frontend React (người dùng chốt 25/10/2026, chuẩn bị đưa lên web)

Nguồn tổng hợp: [Rules of React — react.dev](https://react.dev/reference/rules),
[React Router — chế độ declarative](https://reactrouter.com/start/declarative/installation),
[OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html).
Áp dụng cho `Frontend/frontend-YingHua/`. Khi sửa giao diện: **không đổi chức năng**, giữ bộ màu, font, logo (`dev-workflow.md`).

## 1. Rules of React (bắt buộc)
- Component và hook phải **thuần**: cùng props/state/context → cùng kết quả; không có tác dụng phụ trong lúc render
  (gọi API, ghi `localStorage`, đổi biến ngoài…) — đặt trong `useEffect` hoặc handler sự kiện.
- Props, state, giá trị truyền vào hook và giá trị đã dùng trong JSX là **bất biến**: tạo bản sao mới, không sửa trực tiếp.
- Chỉ gọi hook ở **cấp trên cùng** của component/hook tự viết, trước mọi `return` sớm; không gọi trong vòng lặp, điều kiện, hàm lồng.
- Không gọi component như hàm thường (`Foo()`); chỉ dùng trong JSX. Không truyền hook như một giá trị.
- Danh sách render phải có `key` ổn định (id từ máy chủ), không dùng chỉ số mảng khi danh sách có thể đổi thứ tự.
- Bật `<StrictMode>` ở gốc ứng dụng.

## 2. Điều hướng (React Router 8, chế độ declarative)
- Mọi trang có **URL riêng**; điều hướng bằng `<Link>`/`useNavigate`, không dùng biến trạng thái để đổi trang.
  Nút Back/Forward, F5 và chia sẻ link phải giữ đúng trang.
- Đường dẫn tiếng Việt không dấu, `kebab-case`; tham số đọc từ URL (`useParams`, `useSearchParams`) luôn được **kiểm và ép kiểu**
  (số nguyên dương…), sai thì về trang 404 hoặc giá trị mặc định — không tin dữ liệu trên URL.
- Trang cần đăng nhập/quyền quản trị bọc bằng route bảo vệ (chuyển hướng về trang chủ/mở hộp đăng nhập). Đây chỉ là trải nghiệm;
  **quyền thật luôn do API kiểm** (`security.md`).
- Có route `*` cho trang 404. Chuyển hướng sau đăng nhập chỉ tới đường dẫn nội bộ bắt đầu bằng `/` (chống open redirect).
- Tách mã theo trang bằng `React.lazy` + `<Suspense>` để giảm kích thước bundle ban đầu.

## 3. Cấu trúc & code
- Một component một trách nhiệm; file > ~300 dòng thì tách. Component dạng hàm + TypeScript chặt (không `any` khi tránh được).
- Gọi API chỉ qua `src/api/*` (`apiRequest`), có `AbortController` khi component có thể unmount giữa chừng.
- Trạng thái dùng chung nhiều trang (phiên đăng nhập, hồ sơ) đặt trong context/hook riêng, không truyền props xuyên nhiều tầng.
- Luôn có trạng thái đang tải / rỗng / lỗi; lỗi hiển thị bằng tiếng Việt, không lộ chi tiết kỹ thuật.
- **Trạng thái hiển thị phải lấy từ máy chủ, đồng bộ theo thời gian thực** (người dùng chốt 25/10/2026): mọi dấu
  "đã lưu / đã thêm / đã yêu thích / đã đọc…" phải đọc từ API khi mở màn hình, và đọc lại khi quay lại tab
  (`focus`/`visibilitychange`) hoặc sau thao tác ở màn khác — **không** chỉ giữ trong state cục bộ, vì F5 hay sửa ở màn khác
  sẽ làm sai. Thiếu API để hỏi trạng thái thì thêm API (và cập nhật SRS), không giả lập ở giao diện.
- Máy chủ tạm không phản hồi (lỗi mạng) không được coi như phiên hết hạn: giữ phiên và thử lại.
- Không để code chết, `console.log` debug, dữ liệu giả không dùng tới.

## 4. Bảo mật frontend (OWASP)
- Hiển thị dữ liệu bằng JSX (React tự escape). **Cấm** `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function` với dữ liệu
  người dùng/máy chủ/LLM. Nếu buộc phải hiển thị HTML thì phải làm sạch bằng thư viện được duyệt (hỏi trước khi thêm).
- URL lấy từ dữ liệu (ảnh, liên kết) chỉ chấp nhận `http(s):`, đường dẫn tương đối hoặc `blob:` do chính app tạo; không dùng `javascript:`.
- **Không đưa bí mật vào frontend**: mọi biến `VITE_*` đều lộ trong bundle; khóa API (Gemini…) chỉ ở máy chủ.
- Token: access token chỉ giữ ngắn hạn; xóa sạch khi đăng xuất/401 không làm mới được. Không ghi token, mật khẩu ra console/log.
- Bản build triển khai: tắt source map công khai, có Content-Security-Policy và các header bảo mật ở máy chủ web (cấu hình khi triển khai).
- Phụ thuộc **ghim phiên bản chính xác**, gỡ gói không dùng; thêm thư viện mới phải hỏi (`tech-stack.md`).
