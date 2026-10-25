// Gọi API câu thoại đã lưu (F07.11) và lưu tất cả từ của trang (F07.12).
import { ApiError, apiRequest } from './client';

export interface SavedSentence {
  id: number;
  sentence_zh: string;
  sentence_vi: string | null;
  pinyin: string | null;
  source_label: string | null;
  bubble_id: number | null;
  page_id: number | null;
  chapter_id: number | null;
  page_no: number | null;
  note: string | null;
  created_at: string;
}

export interface SavedSentencePage {
  items: SavedSentence[];
  total: number;
  page: number;
  size: number;
}

export interface SaveAllWordsResult {
  saved: string[];
  existing: string[];
  failed: { term: string; code: string }[];
  remaining: number;
  /** Từ một chữ rất phổ biến (是, 吗…) máy chủ không tự lưu. */
  skipped?: string[];
}

export const saveSentence = (bubbleId: number, pageId?: number, note?: string): Promise<SavedSentence> =>
  apiRequest<SavedSentence>('/saved-sentences', {
    method: 'POST',
    body: { bubble_id: bubbleId, ...(pageId ? { page_id: pageId } : {}), ...(note ? { note } : {}) }
  });

export const listSavedSentences = (page = 1, size = 10, signal?: AbortSignal): Promise<SavedSentencePage> =>
  apiRequest<SavedSentencePage>(`/saved-sentences?page=${page}&size=${size}`, { signal });

export const updateSentenceNote = (id: number, note: string | null): Promise<SavedSentence> =>
  apiRequest<SavedSentence>(`/saved-sentences/${id}`, { method: 'PATCH', body: { note } });

export const deleteSavedSentence = (id: number): Promise<void> =>
  apiRequest<void>(`/saved-sentences/${id}`, { method: 'DELETE' });

/** 409 SENTENCE_ALREADY_SAVED: câu đã có trong danh sách, không phải lỗi thật sự. */
export const isSentenceAlreadySaved = (err: unknown): boolean =>
  err instanceof ApiError && err.code === 'SENTENCE_ALREADY_SAVED';

export const saveAllPageWords = (pageId: number): Promise<SaveAllWordsResult> =>
  apiRequest<SaveAllWordsResult>(`/pages/${pageId}/save-all-words`, { method: 'POST' });

export const isPageWithoutWords = (err: unknown): boolean => err instanceof ApiError && err.code === 'PAGE_HAS_NO_WORDS';

/** Thông báo kết quả lưu hàng loạt: "Đã lưu n từ, m từ đã có, k lỗi". */
export function saveAllMessage(result: SaveAllWordsResult): string {
  const parts = [`Đã lưu ${result.saved.length} từ`, `${result.existing.length} từ đã có`, `${result.failed.length} lỗi`];
  const skipped = result.skipped ?? [];
  if (skipped.length > 0) parts.push(`bỏ qua ${skipped.length} từ quá cơ bản (${skipped.slice(0, 5).join('、')})`);
  return `${parts.join(', ')}${result.remaining > 0 ? `. Còn ${result.remaining} từ chưa lưu` : ''}`;
}
