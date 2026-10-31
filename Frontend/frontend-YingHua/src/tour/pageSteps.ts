import { TourDefinition } from './types';

/** Tour ngắn của từng trang: chỉ chạy khi người dùng tự mở trang đó, không dẫn họ đi nơi khác. */
export const LIBRARY_TOUR: TourDefinition = {
  id: 'library',
  finishLabel: 'Về thư viện',
  steps: [
    {
      id: 'stats',
      targets: ['library-hero'],
      title: 'Toàn cảnh việc học của bạn',
      body: 'Số truyện đã lưu, bộ đang đọc dở và số từ đã lưu luôn cập nhật theo hoạt động thật của bạn.'
    },
    {
      id: 'upload',
      targets: ['library-upload'],
      title: 'Đưa truyện của bạn vào',
      body: 'Tải ảnh manhua của riêng bạn lên để dịch và học. Muốn giữ lâu dài thì tạo truyện riêng tư rồi tải ảnh vào chương.'
    },
    {
      id: 'create',
      targets: ['library-create'],
      title: 'Tạo truyện riêng tư',
      body: 'Truyện riêng tư chỉ bạn thấy được. Mỗi chương có thể chứa nhiều trang, ảnh không tự xóa như tải nhanh.'
    },
    {
      id: 'tabs',
      targets: ['library-tabs'],
      title: 'Lọc theo tiến độ',
      body: 'Chuyển nhanh giữa truyện đang đọc dở và truyện đã xong để đọc tiếp đúng chỗ đã dừng.'
    }
  ]
};

export const FLASHCARDS_TOUR: TourDefinition = {
  id: 'flashcards',
  finishLabel: 'Bắt đầu ôn',
  steps: [
    {
      id: 'overview',
      targets: ['flash-overview'],
      title: 'Từ bạn đã lưu đều ở đây',
      body: 'Mỗi từ lưu từ truyện sẽ thành thẻ ôn, kèm ảnh ngữ cảnh để bạn nhớ từ gặp ở đâu.'
    },
    {
      id: 'review',
      targets: ['flash-review'],
      title: 'Ôn đúng lúc sắp quên',
      body: 'Hệ thống tính ngày ôn cho từng thẻ. Chấm Quên, Khó, Được hoặc Dễ sau mỗi thẻ, từ dễ sẽ giãn lịch, từ khó quay lại sớm hơn.'
    },
    {
      id: 'quiz',
      targets: ['flash-quiz'],
      title: 'Kiểm tra theo từ của bạn',
      body: 'Đề được tạo từ chính sổ tay của bạn, ưu tiên từ sắp quên. Từ làm sai sẽ được đưa trở lại lịch ôn ngay.'
    },
    {
      id: 'notebook',
      targets: ['flash-notebook'],
      title: 'Sổ tay từ vựng',
      body: 'Tìm, lọc, đánh dấu sao và xem lại ngữ cảnh của từng từ. Bạn cũng xuất được sổ tay khi cần.'
    }
  ]
};

export const LEADERBOARD_TOUR: TourDefinition = {
  id: 'leaderboard',
  finishLabel: 'Đua thôi',
  steps: [
    {
      id: 'filters',
      targets: ['board-filters'],
      title: 'Chọn cách so tài',
      body: 'Xem xếp hạng theo tuần, tháng hoặc toàn thời gian, theo điểm XP, chuỗi ngày, từ vựng hay số trang đã đọc.'
    },
    {
      id: 'season',
      targets: ['board-season'],
      title: 'Mùa thi đua mỗi tuần',
      body: 'Mỗi tuần một mùa. Cuối mùa, người đứng top nhận xu, vé, ngày VIP và huy hiệu. Bạn cần ít nhất 50 XP trong mùa để được tính thưởng.'
    },
    {
      id: 'quests',
      targets: ['board-quests'],
      title: 'Nhiệm vụ ngày',
      body: 'Đọc trang, lật thẻ và làm bài kiểm tra để nhận XP. Hoàn thành đủ nhiệm vụ trong ngày được thưởng thêm xu.'
    },
    {
      id: 'goal',
      targets: ['board-goal'],
      title: 'Mục tiêu tuần',
      body: 'Đạt số trang đặt ra trong tuần để nhận XP và khung avatar có hạn 7 ngày.'
    }
  ]
};

export const PROFILE_TOUR: TourDefinition = {
  id: 'profile',
  finishLabel: 'Đã hiểu',
  steps: [
    {
      id: 'activity',
      targets: ['profile-activity'],
      title: 'Nhìn lại quá trình học',
      body: 'Biểu đồ cho thấy số lượt ôn và số trang đã đọc gần đây, giúp bạn giữ nhịp học đều.'
    },
    {
      id: 'badges',
      targets: ['profile-badges'],
      title: 'Huy hiệu và thành tựu',
      body: 'Huy hiệu tự mở khi bạn đạt mốc. Đeo một huy hiệu để hiện cùng tên trên bảng xếp hạng.'
    },
    {
      id: 'wallet',
      targets: ['profile-wallet'],
      title: 'Ví phần thưởng',
      body: 'Xu, vé và ngày VIP đều kiếm bằng việc học, không mua bằng tiền. Bấm vào để sang cửa hàng đổi thưởng.'
    },
    {
      id: 'edit',
      targets: ['profile-edit'],
      title: 'Hồ sơ của bạn',
      body: 'Đổi tên hiển thị, ảnh đại diện, khai báo trình độ HSK để gợi ý truyện và từ vừa sức hơn.'
    }
  ]
};

export const SHOP_TOUR: TourDefinition = {
  id: 'shop',
  finishLabel: 'Xem cửa hàng',
  steps: [
    {
      id: 'wallet',
      targets: ['shop-wallet'],
      title: 'Bạn đang có gì',
      body: 'Xu kiếm từ huy hiệu, nhiệm vụ và thưởng mùa. Vé dùng để mở khóa vĩnh viễn một truyện VIP.'
    },
    {
      id: 'tabs',
      targets: ['shop-tabs'],
      title: 'Đổi thưởng, khung, lịch sử',
      body: 'Đổi xu lấy ngày VIP, vé hoặc khung avatar; đeo khung đã có; xem lại mọi khoản xu đã nhận và đã dùng.'
    },
    {
      id: 'items',
      targets: ['shop-items'],
      title: 'Chọn món muốn đổi',
      body: 'Đang VIP thì hạn mức AI mỗi ngày cao hơn và đọc được mọi truyện VIP. Đổi thưởng không dùng tiền thật.'
    }
  ]
};

export const GAME_TOUR: TourDefinition = {
  id: 'game',
  finishLabel: 'Chơi thôi',
  steps: [
    {
      id: 'bands',
      targets: ['game-bands'],
      title: 'Chọn cấp HSK',
      body: 'Chữ Hán rơi xuống, bạn gõ pinyin không dấu để phi kiếm chém chữ. Chữ ü gõ là u. Mỗi cấp có kỷ lục riêng.'
    },
    {
      id: 'radicals',
      targets: ['game-radicals'],
      title: 'Luyện bộ thủ hay quên',
      body: 'Hệ thống chọn bộ thủ từ những thẻ bạn hay quên, để bạn luyện đúng chỗ còn yếu.'
    },
    {
      id: 'options',
      targets: ['game-options'],
      title: 'Tùy chỉnh ván chơi',
      body: 'Bật tắt âm thanh, gợi ý pinyin và chọn tốc độ rơi. Mỗi ngày 5 ván đầu được tính XP.'
    }
  ]
};

export const SAMPLE_TOUR: TourDefinition = {
  id: 'sample',
  finishLabel: 'Thử ngay',
  steps: [
    {
      id: 'page',
      targets: ['sample-page'],
      title: 'Thử trên trang mẫu',
      body: 'Đây là trang đã xử lý sẵn. Chạm vào khung thoại để xem pinyin, nghĩa và tách từ.'
    },
    {
      id: 'variants',
      targets: ['sample-variants'],
      title: 'So sánh trước và sau',
      body: 'Xem ảnh gốc, ảnh đã xóa chữ và ảnh đã đắp bản dịch để hiểu hệ thống xử lý một trang thế nào.'
    },
    {
      id: 'panel',
      targets: ['sample-panel'],
      title: 'Tra từ ngay bên cạnh',
      body: 'Khung thoại bạn chọn hiện ở đây, bấm vào từng từ để tra nghĩa chi tiết.'
    }
  ]
};

export const ADMIN_TOUR: TourDefinition = {
  id: 'admin',
  finishLabel: 'Vào việc',
  steps: [
    {
      id: 'nav',
      targets: ['admin-nav'],
      title: 'Khu quản trị',
      body: 'Người dùng, kho truyện, kiểm duyệt, đổi thưởng, xử lý ảnh, tác vụ nền và cài đặt hệ thống đều nằm ở thanh này.'
    },
    {
      id: 'header',
      targets: ['admin-header'],
      title: 'Thao tác nhanh',
      body: 'Từng mục có tiêu đề và nút thao tác chính ở đây. Mọi thao tác sửa dữ liệu của người khác đều được ghi nhật ký quản trị.'
    }
  ]
};
