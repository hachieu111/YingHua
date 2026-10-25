import { CURRENT_USER } from '../data/mockData';
import { UserProfileData } from '../types';
import { ApiUser } from './auth';
import { ApiSettings } from './settings';

const DEFAULT_WEEKLY_PAGE_GOAL = 20;

/**
 * Ghép dữ liệu thật từ máy chủ thành hồ sơ hiển thị.
 * Các số liệu học tập (chuỗi ngày, từ vựng, trang đã đọc...) chưa có API nên để 0 thay vì dùng số giả;
 * avatar tải lên lấy từ máy chủ (avatarUrl), huy hiệu và avatar gợi ý giữ giá trị đang chọn (chưa có API lưu).
 */
export function toUserProfile(user: ApiUser, settings: ApiSettings | null, previous?: UserProfileData): UserProfileData {
  return {
    name: user.display_name,
    chineseName: user.chinese_name ?? '',
    badge: previous?.badge ?? CURRENT_USER.badge,
    hskLevel: settings?.hsk_level ? `Cấp độ HSK ${settings.hsk_level}` : 'Chưa chọn trình độ HSK',
    id: `#YH-${user.id}`,
    vipExpiry: '—',
    joinDate: new Date(user.created_at).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }),
    email: user.email,
    showEmail: user.show_email,
    showJoinDate: user.show_join_date,
    avatar: previous?.avatar ?? CURRENT_USER.avatar,
    avatarUrl: user.avatar_url,
    streak: 0,
    totalVocab: 0,
    pagesRead: 0,
    hoursLearned: 0,
    weeklyProgress: { current: 0, target: settings?.weekly_page_goal ?? DEFAULT_WEEKLY_PAGE_GOAL }
  };
}
