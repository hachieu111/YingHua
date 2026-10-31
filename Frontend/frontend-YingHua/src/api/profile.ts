import { CURRENT_USER } from '../data/mockData';
import { UserProfileData } from '../types';
import { ApiUser } from './auth';
import { ApiSettings } from './settings';
import { presetAvatarUrl } from '../data/avatarPresets';

const DEFAULT_WEEKLY_PAGE_GOAL = 20;

/**
 * Ghép dữ liệu thật từ máy chủ thành hồ sơ hiển thị.
 * Các số liệu học tập (chuỗi ngày, từ vựng, trang đã đọc...) chưa có API nên để 0 thay vì dùng số giả;
 * avatar tải lên (avatarUrl) và ảnh đại diện có sẵn (avatar_preset) đều lấy từ máy chủ; huy hiệu, VIP và khung avatar lấy từ M16/M17 qua `useRewards`.
 */
/** Phần avatar của hồ sơ sau khi tải lên/gỡ/chọn ảnh có sẵn. */
export const avatarFields = (user: ApiUser): Pick<UserProfileData, 'avatar' | 'avatarUrl' | 'avatarPreset'> => ({
  avatar: presetAvatarUrl(user.avatar_preset) ?? CURRENT_USER.avatar,
  avatarUrl: user.avatar_url,
  avatarPreset: user.avatar_preset
});

export function toUserProfile(user: ApiUser, settings: ApiSettings | null): UserProfileData {
  return {
    name: user.display_name,
    chineseName: user.chinese_name ?? '',
    hskLevel: settings?.hsk_level ? `Cấp độ HSK ${settings.hsk_level}` : 'Chưa chọn trình độ HSK',
    id: `#YH-${user.id}`,
    joinDate: new Date(user.created_at).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }),
    email: user.email,
    showEmail: user.show_email,
    showJoinDate: user.show_join_date,
    avatar: presetAvatarUrl(user.avatar_preset) ?? CURRENT_USER.avatar,
    avatarUrl: user.avatar_url,
    avatarPreset: user.avatar_preset,
    streak: 0,
    totalVocab: 0,
    pagesRead: 0,
    hoursLearned: 0,
    weeklyProgress: { current: 0, target: settings?.weekly_page_goal ?? DEFAULT_WEEKLY_PAGE_GOAL }
  };
}
