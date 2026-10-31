import { TourDefinition } from './types';

/** Tour trang chủ: mỗi bước nói lợi ích cho người học; bước không có phần tử trên màn hình tự bị bỏ qua. */
export const HOME_TOUR: TourDefinition = {
  id: 'home',
  finishLabel: 'Bắt đầu học',
  steps: [
    {
      id: 'welcome',
      targets: [],
      welcome: true,
      title: 'Chào mừng bạn đến với Yinghua',
      body: 'Đọc truyện tranh tiếng Trung, rê chuột vào lời thoại là thấy pinyin và nghĩa, rồi lưu từ để ôn lại. Mình đưa bạn xem nhanh các khu vực chính nhé?'
    },
    {
      id: 'search',
      targets: ['nav-search', 'catalog-search'],
      title: ({ target }) => (target === 'nav-search' ? 'Tra từ ngay khi cần' : 'Tìm truyện bạn muốn đọc'),
      body: ({ target }) =>
        target === 'nav-search'
          ? 'Gõ một từ vào đây để xem pinyin, cấp HSK và nghĩa, không phải rời trang đang xem. Muốn tìm truyện thì dùng ô tìm kiếm ở phần lộ trình phía dưới.'
          : 'Gõ tên truyện hoặc từ khóa để tìm nhanh truyện đúng ý thay vì phải lướt cả danh mục.'
    },
    {
      id: 'upload',
      targets: ['nav-upload'],
      title: 'Dịch ảnh manhua của riêng bạn',
      body: ({ isLoggedIn }) =>
        `Tải ảnh manhua của bạn lên, hệ thống nhận chữ, dịch sang tiếng Việt, và bạn học được từ ngay trên chính ảnh đó.${isLoggedIn ? '' : ' Tính năng này cần đăng nhập.'}`
    },
    {
      id: 'catalog',
      targets: ['catalog-roadmap'],
      title: 'Chọn truyện vừa sức',
      body: 'Lộ trình HSK giúp bạn lọc truyện theo trình độ và thể loại ngay bên dưới, để đọc được mà không bị ngợp vì quá nhiều từ mới.'
    },
    {
      id: 'sample',
      targets: ['home-sample'],
      title: 'Thử Hover & Dịch trong một phút',
      body: ({ isLoggedIn }) =>
        `Trang mẫu cho bạn thấy kết quả thật: rê vào bóng thoại là có pinyin và nghĩa, chưa cần tự tải ảnh.${isLoggedIn ? '' : ' Bạn cần đăng nhập để mở trang này.'}`
    },
    {
      id: 'nav',
      targets: ['nav-links', 'nav-menu'],
      title: 'Mọi thứ để học đều ở đây',
      body: ({ target, isLoggedIn }) => {
        const where = target === 'nav-menu' ? 'Mở menu này để tới ' : 'Từ thanh này bạn tới ';
        const login = isLoggedIn ? '' : ' Riêng Từ Vựng cần đăng nhập.';
        return `${where}Đọc Truyện, Từ Vựng với Flashcard ôn đúng lúc sắp quên, và Bảng Xếp Hạng để thi đua cùng mọi người. Mini-game Phi Kiếm Trảm Tự luyện pinyin có lối vào ở Bảng Xếp Hạng.${login}`;
      }
    },
    {
      id: 'streak',
      targets: ['nav-streak'],
      title: 'Giữ nhịp học mỗi ngày',
      body: ({ isLoggedIn }) =>
        isLoggedIn
          ? 'Đây là chuỗi ngày học liên tiếp và số XP kiếm được hôm nay. Mỗi ngày học một chút là chuỗi lại dài thêm.'
          : 'Sau khi đăng nhập, đây là nơi theo dõi chuỗi ngày học liên tiếp và số XP kiếm được trong ngày.'
    },
    {
      id: 'theme',
      targets: ['nav-theme', 'nav-menu'],
      title: 'Đọc thoải mái cả khi trời tối',
      body: ({ target }) =>
        target === 'nav-menu'
          ? 'Trong menu này có nút đổi giao diện sáng hoặc tối cho trang chủ, chọn kiểu nào dễ nhìn với bạn.'
          : 'Đổi giao diện sáng hoặc tối cho trang chủ, chọn kiểu nào dễ nhìn với bạn.'
    },
    {
      id: 'register',
      targets: ['nav-register'],
      audience: 'guest',
      title: 'Tạo tài khoản để giữ tiến độ',
      body: 'Đăng ký để lưu tiến độ đọc, sổ tay từ vựng và lịch ôn. Tài khoản mới được tặng 3 ngày VIP.'
    },
    {
      id: 'profile',
      targets: ['nav-profile'],
      audience: 'user',
      title: 'Hồ sơ của bạn',
      body: 'Xem lại tiến độ học, thành tích và các truyện đang đọc ở đây. Bạn có thể xem lại hướng dẫn này bất cứ lúc nào trong Cài đặt tài khoản.'
    }
  ]
};
