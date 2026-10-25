# Yinghua

Yinghua là một ứng dụng học tiếng Trung theo phong cách manhua, giúp người dùng học từ vựng, đọc truyện, luyện flashcard và theo dõi tiến độ học tập qua hệ thống streak, XP và bảng xếp hạng.

## Tính năng chính

- Trang chủ / Catalog khám phá nội dung
- Đọc truyện tranh tương tác
- Thư viện cá nhân
- Học từ vựng và flashcard
- Bảng xếp hạng người dùng
- Hồ sơ cá nhân, avatar và thành tích
- Chế độ đăng nhập / đăng ký
- Giao diện hiện đại, tối ưu cho trải nghiệm học tập

## Công nghệ sử dụng

- React + TypeScript
- Vite
- Tailwind CSS
- Lucide React
- Google GenAI SDK

## Yêu cầu hệ thống

- Node.js 18+
- npm hoặc pnpm

## Cài đặt

1. Clone dự án:
   ```bash
   git clone <repo-url>
   cd yinghua
   ```

2. Cài đặt dependencies:
   ```bash
   npm install
   ```

> Nếu bạn gặp lỗi peer dependency khi install, có thể dùng:
> ```bash
> npm install --legacy-peer-deps
> ```

## Chạy ứng dụng ở local

```bash
npm run dev -- --host 0.0.0.0
```

Sau đó mở trình duyệt tại:

- http://localhost:3000

## Tài khoản đăng nhập demo

| Vai trò | Email | Mật khẩu |
| --- | --- | --- |
| Học viên (Lam Hiên Vũ) | `sakura@yinghua.vn` | `12345678` |
| Quản trị viên | `admin@yinghua.vn` | `123456` |

Đây là thông tin đăng nhập mô phỏng dùng để thử giao diện. Ứng dụng hiện chưa xác thực tài khoản qua máy chủ.

## Build production

```bash
npm run build
```

## Kết cấu thư mục chính

```bash
src/
  components/      # Các giao diện chính: Navbar, Reader, Flashcards, Profile...
  data/            # Dữ liệu mock cho ứng dụng
  utils/           # Tiện ích helper
  App.tsx          # Entry UI của ứng dụng
  main.tsx         # Render React app
public/
  assets/          # Tài nguyên hình ảnh, assets của app
```

## Ghi chú

Dự án này hiện đang sử dụng dữ liệu mock để mô phỏng trải nghiệm người dùng và các tính năng học tập. Bạn có thể mở rộng thêm API, database hoặc AI dịch/trích xuất văn bản nếu muốn phát triển phiên bản thực tế hơn.

## License

Dự án này được cung cấp cho mục đích phát triển nội bộ / demo. Nếu cần, bạn có thể thêm license phù hợp với yêu cầu của dự án.
