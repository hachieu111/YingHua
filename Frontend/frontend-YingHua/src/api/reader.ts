// Gọi API Đọc truyện (M05): dữ liệu trang, tra từ trong bong bóng, sửa dịch, dấu trang, ghi chú.
import { apiRequest } from './client';
import { WordLookup } from './dictionary';
import { TranslationStatus } from './library';

export interface ReadingToken {
  word: string;
  pinyin: string | null;
  entry_id: number | null;
}

export interface ReadingBubble {
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
  text_vi_effective: string | null;
  has_edit: boolean;
  tokens: ReadingToken[];
}

export interface ApiStroke {
  color: string;
  points: { x: number; y: number }[];
}

export interface ApiAnnotation {
  is_bookmarked: boolean;
  highlights: Record<string, string>;
  strokes: ApiStroke[];
  updated_at: string;
}

export interface ReadingData {
  page: {
    id: number;
    page_no: number;
    chapter_id: number | null;
    series_id: number | null;
    width: number | null;
    height: number | null;
    status: TranslationStatus | null;
    error_step: string | null;
    error_message: string | null;
    can_edit: boolean;
  };
  variants: { original: string | null; inpainted: string | null; rendered: string | null };
  bubbles: ReadingBubble[];
  annotation: ApiAnnotation | null;
}

export interface BubbleLookup {
  bubble_id: number;
  word: string;
  lookup: WordLookup;
  guest: { session_id: string; limit: number; used: number; remaining: number } | null;
}

export interface BookmarkItem {
  page_id: number;
  page_no: number;
  chapter_id: number | null;
  chapter_number: number | null;
  series_id: number | null;
  series_title: string | null;
  original_url: string | null;
  bookmarked_at: string;
}

const GUEST_KEY = 'yinghua-guest-session';

const loadGuestSession = (): string | null => {
  try {
    return localStorage.getItem(GUEST_KEY);
  } catch {
    return null;
  }
};

const saveGuestSession = (id: string) => {
  try {
    localStorage.setItem(GUEST_KEY, id);
  } catch {
    // Không lưu được thì mỗi lần tải lại trang là một phiên khách mới.
  }
};

export const getReading = (pageId: number, signal?: AbortSignal): Promise<ReadingData> =>
  apiRequest<ReadingData>(`/pages/${pageId}/reading`, { signal });

/** Tra một từ trong bong bóng; Khách gửi kèm mã phiên để tính hạn mức (F05.04). */
export async function lookupBubbleWord(bubbleId: number, word: string, isGuest: boolean): Promise<BubbleLookup> {
  const headers: Record<string, string> = {};
  const guest = isGuest ? loadGuestSession() : null;
  if (guest) headers['X-Guest-Session'] = guest;
  const result = await apiRequest<BubbleLookup>(`/bubbles/${bubbleId}/lookup?word=${encodeURIComponent(word)}`, { headers });
  if (result.guest) saveGuestSession(result.guest.session_id);
  return result;
}

export const saveBubbleEdit = (
  bubbleId: number,
  textVi: string
): Promise<{ bubble_id: number; text_vi: string | null; text_vi_effective: string | null; has_edit: boolean }> =>
  apiRequest(`/bubbles/${bubbleId}/edit`, { method: 'PUT', body: { text_vi: textVi } });

export const deleteBubbleEdit = (bubbleId: number): Promise<void> =>
  apiRequest<void>(`/bubbles/${bubbleId}/edit`, { method: 'DELETE' });

export const setBookmark = (pageId: number, isBookmarked: boolean): Promise<{ page_id: number; is_bookmarked: boolean }> =>
  apiRequest(`/pages/${pageId}/bookmark`, { method: 'PUT', body: { is_bookmarked: isBookmarked } });

export const listBookmarks = (
  page = 1,
  size = 50
): Promise<{ items: BookmarkItem[]; total: number; page: number; size: number }> =>
  apiRequest(`/bookmarks?page=${page}&size=${size}`);

export const saveAnnotations = (
  pageId: number,
  annotations: { highlights: Record<string, string>; strokes: ApiStroke[] }
): Promise<ApiAnnotation> => apiRequest<ApiAnnotation>(`/pages/${pageId}/annotations`, { method: 'PUT', body: annotations });

export const clearAnnotations = (pageId: number): Promise<void> => apiRequest<void>(`/pages/${pageId}/annotations`, { method: 'DELETE' });
