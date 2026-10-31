import { MAX_CHAPTER_UPLOAD_FILES } from '../api/library';
import { TourDefinition } from './types';

/** Tour hộp tải ảnh. Khách không mở được hộp này (phải đăng nhập), nên nội dung chỉ dành cho người đã đăng nhập. */
export const UPLOAD_TOUR: TourDefinition = {
  id: 'upload',
  insideModal: true,
  finishLabel: 'Tải ảnh thôi',
  steps: [
    {
      id: 'destination',
      targets: ['upload-destination'],
      title: 'Chọn nơi lưu trước',
      body: 'Tải nhanh dành cho ảnh lẻ, ảnh tự xóa sau 7 ngày. Muốn giữ lâu dài thì lưu vào chương của truyện riêng tư. Đổi lựa chọn sẽ bỏ các ảnh đã chọn, nên hãy chọn nơi lưu trước.'
    },
    {
      id: 'files',
      targets: ['upload-dropzone'],
      title: 'Chọn hoặc kéo thả ảnh',
      body: `Nhận JPG, PNG, WebP, mỗi ảnh tối đa 10 MB. Tải nhanh được 5 ảnh mỗi lần, vào chương được ${MAX_CHAPTER_UPLOAD_FILES} ảnh mỗi lần.`
    },
    {
      id: 'submit',
      targets: ['upload-submit'],
      title: 'Bắt đầu dịch',
      body: 'Nút này sáng lên khi đã có ảnh. Bấm là ảnh được gửi lên và xếp hàng xử lý, bạn không cần chờ trong hộp này.'
    },
    {
      id: 'progress',
      targets: ['upload-results', 'upload-callout'],
      title: 'Xong phần nào hiện phần đó',
      body: 'Mỗi ảnh có nhãn trạng thái riêng. Chữ và bản dịch có trước, ảnh đã xóa chữ và đắp bản dịch có sau. Thời gian chờ tùy số ảnh đang xử lý; bạn có thể đóng hộp, kết quả vẫn ở Thư viện.'
    },
    {
      id: 'open',
      targets: ['upload-results', 'upload-panel'],
      title: 'Mở ra đọc và học',
      body: 'Ảnh xong sẽ có nút Mở bản dịch. Ảnh chưa xong vẫn bấm được Xem ảnh gốc, chữ và bản dịch tự hiện dần trong trình đọc để bạn tra từ và lưu từ.'
    }
  ]
};
