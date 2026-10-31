import { TourDefinition } from './types';

/** Tour trình đọc: phần giá trị cốt lõi, chạy lần đầu mở được một trang truyện. */
export const READER_TOUR: TourDefinition = {
  id: 'reader',
  finishLabel: 'Đọc thôi',
  steps: [
    {
      id: 'canvas',
      targets: ['reader-canvas'],
      title: 'Học ngay trên trang truyện',
      body: 'Rê chuột vào bóng thoại để xem pinyin và nghĩa tiếng Việt, bấm vào bóng thoại để nghe đọc. Trang đang xử lý thì chữ và bản dịch sẽ tự hiện khi có.'
    },
    {
      id: 'modes',
      targets: ['reader-modes'],
      title: 'Ba cách xem một trang',
      body: 'Bóng Thoại giữ ảnh gốc để luyện đọc chữ Hán, Đã xóa chữ để tự đoán nội dung, Đã đắp chữ để đọc thẳng bản tiếng Việt. Hai chế độ sau mở khi trang xử lý xong.'
    },
    {
      id: 'vocab',
      targets: ['reader-vocab'],
      title: 'Giữ lại từ mới của trang này',
      body: ({ isLoggedIn }) =>
        isLoggedIn
          ? 'Các từ trong trang được gom sẵn ở đây. Lưu từ nào vào Sổ tay là có thẻ ôn cho từ đó, kèm ngữ cảnh trang truyện.'
          : 'Các từ trong trang được gom sẵn ở đây để bạn tra nghĩa. Đăng nhập để lưu từ vào Sổ tay và ôn lại sau.'
    },
    {
      id: 'listen',
      targets: ['reader-listen'],
      title: 'Nghe đọc cả trang',
      body: 'Nghe toàn bộ lời thoại của trang để luyện tai và phát âm, đổi tốc độ cho vừa sức bằng nút bên cạnh.'
    },
    {
      id: 'source',
      targets: ['reader-source'],
      audience: 'user',
      title: 'Đổi sang truyện của bạn',
      body: 'Chuyển nhanh sang ảnh bạn đã tải lên hoặc một truyện riêng tư mà không phải rời trình đọc.'
    }
  ]
};
