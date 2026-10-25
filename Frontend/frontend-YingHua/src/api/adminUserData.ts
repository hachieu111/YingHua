// Quản trị viên xem/sửa dữ liệu của một người dùng (M13: F13.07, US-QT-14). Mọi thay đổi được máy chủ ghi nhật ký quản trị.
import { apiRequest } from './client';
import { AdminUser } from './adminUsers';
import { ApiPage, ApiSeries, ContinueItem, LibraryTab, Paged, SeriesInput } from './library';
import { ApiStroke, BookmarkItem } from './reader';
import { ApiCardState, ReviewHistory, ReviewSummary } from './review';
import { ApiSettings } from './settings';
import { ApiVocabDetail, UpdateVocabBody, VocabListParams, VocabPage } from './vocab';

export interface UserOverview {
  user: AdminUser;
  vocab_counts: { learning: number; known: number; ignored: number };
  vocab_total: number;
  cards_total: number;
  cards_due: number;
  reviews_today: number;
  reviews_total: number;
  private_series: number;
  quick_uploads: number;
  last_active_at: string | null;
}

export interface AdminCard extends ApiCardState {
  term: string | null;
  pinyin: string | null;
  meaning_vi: string | null;
  entry_status: string | null;
}

export interface AdminCardQuery {
  state?: 'learning' | 'review' | 'relearning';
  suspended?: boolean;
  due?: boolean;
  page?: number;
  size?: number;
}

export interface AdminSettings extends ApiSettings {
  show_xianxia: boolean;
}

export interface AdminAnnotation {
  is_bookmarked: boolean;
  highlights: Record<string, string>;
  strokes: ApiStroke[];
  updated_at: string;
}

export interface AdminBubbleEdit {
  bubble_id: number;
  text_vi: string | null;
  text_vi_effective: string | null;
  has_edit: boolean;
}

const base = (userId: number): string => `/admin/users/${userId}`;

const qs = (params: Record<string, string | number | boolean | null | undefined>): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') query.set(key, String(value));
  });
  const text = query.toString();
  return text ? `?${text}` : '';
};

export const getUserOverview = (userId: number, signal?: AbortSignal): Promise<UserOverview> =>
  apiRequest<UserOverview>(`${base(userId)}/overview`, { signal });

// --- Sổ tay ---
export const listUserVocab = (userId: number, params: VocabListParams = {}, signal?: AbortSignal): Promise<VocabPage> =>
  apiRequest<VocabPage>(
    `${base(userId)}/vocab-entries${qs({
      status: params.status,
      hsk: params.hsk,
      q: params.q,
      starred: params.starred,
      due: params.due,
      series_id: params.seriesId,
      page: params.page ?? 1,
      size: params.size ?? 10
    })}`,
    { signal }
  );

export const getUserVocab = (userId: number, entryId: number, signal?: AbortSignal): Promise<ApiVocabDetail> =>
  apiRequest<ApiVocabDetail>(`${base(userId)}/vocab-entries/${entryId}`, { signal });

export const updateUserVocab = (userId: number, entryId: number, body: UpdateVocabBody): Promise<ApiVocabDetail> =>
  apiRequest<ApiVocabDetail>(`${base(userId)}/vocab-entries/${entryId}`, { method: 'PATCH', body });

export const deleteUserVocab = (userId: number, entryId: number): Promise<void> =>
  apiRequest<void>(`${base(userId)}/vocab-entries/${entryId}`, { method: 'DELETE' });

export const deleteUserVocabContext = (userId: number, entryId: number, contextId: number): Promise<void> =>
  apiRequest<void>(`${base(userId)}/vocab-entries/${entryId}/contexts/${contextId}`, { method: 'DELETE' });

// --- Thẻ ôn ---
export const getUserReviewSummary = (userId: number, signal?: AbortSignal): Promise<ReviewSummary> =>
  apiRequest<ReviewSummary>(`${base(userId)}/review/summary`, { signal });

export const listUserCards = (userId: number, query: AdminCardQuery = {}, signal?: AbortSignal): Promise<Paged<AdminCard>> =>
  apiRequest<Paged<AdminCard>>(
    `${base(userId)}/cards${qs({
      state: query.state,
      suspended: query.suspended,
      due: query.due,
      page: query.page ?? 1,
      size: query.size ?? 10
    })}`,
    { signal }
  );

export const getUserCardHistory = (userId: number, cardId: number, page = 1, size = 10): Promise<ReviewHistory> =>
  apiRequest<ReviewHistory>(`${base(userId)}/cards/${cardId}/history${qs({ page, size })}`);

export const suspendUserCard = (userId: number, cardId: number): Promise<ApiCardState> =>
  apiRequest<ApiCardState>(`${base(userId)}/cards/${cardId}/suspend`, { method: 'POST' });

export const resumeUserCard = (userId: number, cardId: number): Promise<ApiCardState> =>
  apiRequest<ApiCardState>(`${base(userId)}/cards/${cardId}/resume`, { method: 'POST' });

export const resetUserCard = (userId: number, cardId: number): Promise<ApiCardState> =>
  apiRequest<ApiCardState>(`${base(userId)}/cards/${cardId}/reset`, { method: 'POST' });

// --- Cài đặt ---
export const getUserSettings = (userId: number, signal?: AbortSignal): Promise<AdminSettings> =>
  apiRequest<AdminSettings>(`${base(userId)}/settings`, { signal });

export const updateUserSettings = (userId: number, changes: Partial<AdminSettings>): Promise<AdminSettings> =>
  apiRequest<AdminSettings>(`${base(userId)}/settings`, { method: 'PATCH', body: changes });

// --- Thư viện & đọc ---
export const listUserLibrary = (userId: number, tab: LibraryTab, page = 1, size = 50, signal?: AbortSignal): Promise<Paged<ApiSeries>> =>
  apiRequest<Paged<ApiSeries>>(`${base(userId)}/library${qs({ tab, page, size })}`, { signal });

export const listUserReadingProgress = (userId: number, limit = 20, signal?: AbortSignal): Promise<ContinueItem[]> =>
  apiRequest<ContinueItem[]>(`${base(userId)}/reading-progress${qs({ limit })}`, { signal });

export const listUserQuickUploads = (userId: number, page = 1, size = 12, signal?: AbortSignal): Promise<Paged<ApiPage>> =>
  apiRequest<Paged<ApiPage>>(`${base(userId)}/quick-uploads${qs({ page, size })}`, { signal });

export const listUserBookmarks = (userId: number, page = 1, size = 20, signal?: AbortSignal): Promise<Paged<BookmarkItem>> =>
  apiRequest<Paged<BookmarkItem>>(`${base(userId)}/bookmarks${qs({ page, size })}`, { signal });

export const getUserAnnotations = (userId: number, pageId: number): Promise<AdminAnnotation | null> =>
  apiRequest<AdminAnnotation | null>(`${base(userId)}/pages/${pageId}/annotations`);

export const clearUserAnnotations = (userId: number, pageId: number): Promise<void> =>
  apiRequest<void>(`${base(userId)}/pages/${pageId}/annotations`, { method: 'DELETE' });

export const listUserBubbleEdits = (userId: number, pageId: number): Promise<AdminBubbleEdit[]> =>
  apiRequest<AdminBubbleEdit[]>(`${base(userId)}/bubble-edits${qs({ page_id: pageId })}`);

export const deleteUserBubbleEdit = (userId: number, bubbleId: number): Promise<void> =>
  apiRequest<void>(`${base(userId)}/bubbles/${bubbleId}/edit`, { method: 'DELETE' });

// --- Truyện riêng của người dùng: dùng API truyện sẵn có (admin có quyền sửa/xóa) ---
export const updateSeriesAsAdmin = (seriesId: number, changes: Partial<SeriesInput>): Promise<ApiSeries> =>
  apiRequest<ApiSeries>(`/series/${seriesId}`, { method: 'PATCH', body: changes });

export const deleteSeriesAsAdmin = (seriesId: number): Promise<void> =>
  apiRequest<void>(`/series/${seriesId}`, { method: 'DELETE' });
