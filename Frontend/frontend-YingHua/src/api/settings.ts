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
}

export const getSettings = (): Promise<ApiSettings> => apiRequest<ApiSettings>('/settings');

export const updateSettings = (changes: Partial<ApiSettings>): Promise<ApiSettings> =>
  apiRequest<ApiSettings>('/settings', { method: 'PATCH', body: changes });

export const BUBBLE_FONT_SCALE_MIN = 80;
export const BUBBLE_FONT_SCALE_MAX = 160;
export const BUBBLE_FONT_SCALE_STEP = 10;
export const BUBBLE_FONT_SCALE_DEFAULT = 100;
