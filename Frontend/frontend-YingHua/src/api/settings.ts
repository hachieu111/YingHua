import { apiRequest } from './client';

export interface ApiSettings {
  hsk_level: number | null;
  default_mode: 'read' | 'learn';
  tts_voice: string | null;
  learning_goal: 'study' | 'entertainment' | 'both' | null;
  weekly_page_goal: number | null;
  show_xianxia: boolean;
  /** Cỡ chữ lớp dịch trên trang, %: 80..160, bước 10 (F02.04). */
  bubble_font_scale: number;
  /** Bật nhắc ôn hằng ngày (F14.03). */
  reminder_enabled: boolean;
  /** Giờ nhắc "HH:MM" theo múi giờ của người học. */
  reminder_time: string | null;
  /** Hiện tên trên bảng xếp hạng; tắt thì ẩn danh (F16.08). */
  show_on_leaderboard: boolean;
  /** Các tour hướng dẫn đã xem; máy chủ chưa hỗ trợ thì không có trường này. */
  dismissed_tours?: string[];
}

export const getSettings = (signal?: AbortSignal): Promise<ApiSettings> => apiRequest<ApiSettings>('/settings', { signal });

export const updateSettings = (changes: Partial<ApiSettings>): Promise<ApiSettings> =>
  apiRequest<ApiSettings>('/settings', { method: 'PATCH', body: changes });

export const BUBBLE_FONT_SCALE_MIN = 80;
export const BUBBLE_FONT_SCALE_MAX = 160;
export const BUBBLE_FONT_SCALE_STEP = 10;
export const BUBBLE_FONT_SCALE_DEFAULT = 100;
