// Trang mẫu đã xử lý thật để thử Hover & Dịch (F04.16).
import { ApiError, apiRequest } from './client';

export interface SampleToken {
  word: string;
  pinyin: string | null;
  entry_id: number | null;
}

export interface SampleBubble {
  id: number;
  idx: number;
  class_name: string;
  x_pct: number | null;
  y_pct: number | null;
  w_pct: number | null;
  h_pct: number | null;
  text_zh: string;
  pinyin: string | null;
  text_vi: string | null;
  tokens: SampleToken[];
}

export interface SamplePage {
  page_id: number;
  width: number | null;
  height: number | null;
  variants: { original: string | null; inpainted: string | null; rendered: string | null };
  bubbles: SampleBubble[];
}

export const getSamplePage = (signal?: AbortSignal): Promise<SamplePage> =>
  apiRequest<SamplePage>('/sample-page', { signal });

/** Quản trị viên chưa chọn trang mẫu. */
export const isSampleMissing = (err: unknown): boolean =>
  err instanceof ApiError && err.code === 'SAMPLE_PAGE_NOT_CONFIGURED';
