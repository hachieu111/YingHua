// Gọi API Thư viện (M03): truyện, chương, trang, tải ảnh, tiến độ đọc, Thư viện cá nhân.
import { apiRequest } from './client';

export interface ApiSeries {
  id: number;
  title_vi: string;
  title_zh: string | null;
  author: string | null;
  description: string | null;
  cover_url: string | null;
  visibility: 'public' | 'private';
  status: 'ongoing' | 'completed';
  est_hsk_level: number | null;
  genres: string[];
  owner_id: number | null;
  chapter_count: number;
  rating_avg: number | null;
  rating_count: number;
  in_library: boolean;
  is_favorite: boolean;
  can_edit: boolean;
  progress: SeriesProgress | null;
  created_at: string;
  updated_at: string;
}

/** Tiến độ cả truyện; các trường điểm dừng là null khi chỉ có số trang đã đọc mà chưa có dòng tiến độ. */
export interface SeriesProgress {
  chapter_id: number | null;
  chapter_number: number | null;
  page_no: number | null;
  page_id: number | null;
  total_pages: number | null;
  mode: 'read' | 'learn' | null;
  completed: boolean;
  updated_at: string | null;
  pages_read: number;
  pages_total: number;
  percent: number;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface ApiChapter {
  id: number;
  series_id: number;
  number: number;
  title: string | null;
  is_trial: boolean;
  page_count: number;
  created_at: string;
}

export interface ApiResume {
  series_id: number;
  chapter_id: number;
  chapter_number: number;
  page_no: number;
  page_id: number | null;
  total_pages: number;
  mode: 'read' | 'learn';
  completed: boolean;
  updated_at: string;
}

export interface SeriesDetail {
  series: ApiSeries;
  chapters: ApiChapter[];
  progress: ApiResume | null;
  my_rating: number | null;
}

/** queued · running · done · failed; null nếu trang chưa có bản dịch. */
export type TranslationStatus = 'queued' | 'running' | 'done' | 'failed';

export interface ApiPage {
  id: number;
  chapter_id: number | null;
  series_id: number | null;
  page_no: number;
  width: number | null;
  height: number | null;
  status: TranslationStatus | null;
  error_step: string | null;
  error_message: string | null;
  original_url: string | null;
  inpainted_url: string | null;
  rendered_url: string | null;
  expires_at: string | null;
  can_edit: boolean;
  created_at: string;
}

export interface ApiProgress {
  chapter_id: number;
  page_no: number;
  mode: 'read' | 'learn';
  completed: boolean;
  updated_at: string;
}

export interface ChapterDetail {
  chapter: ApiChapter;
  series_id: number;
  series_title: string;
  pages: ApiPage[];
  can_edit: boolean;
  progress: ApiProgress | null;
}

export interface UploadItemResult {
  filename: string | null;
  page: ApiPage | null;
  error: { code: string; message: string } | null;
}

export interface ContinueItem {
  series_id: number;
  series_title: string;
  cover_url: string | null;
  chapter_id: number;
  chapter_number: number;
  chapter_title: string | null;
  page_no: number;
  page_id: number | null;
  total_pages: number;
  mode: 'read' | 'learn';
  updated_at: string;
}

export interface Rating {
  my_stars: number;
  rating_avg: number | null;
  rating_count: number;
}

export type LibraryTab = 'all' | 'reading' | 'favorites' | 'completed';

export interface SeriesQuery {
  scope?: 'public' | 'mine';
  q?: string;
  hsk?: number | null;
  genre?: string;
  page?: number;
  size?: number;
}

export interface SeriesInput {
  title_vi: string;
  title_zh?: string | null;
  author?: string | null;
  description?: string | null;
  est_hsk_level?: number | null;
  genres?: string[];
  status?: 'ongoing' | 'completed';
  visibility?: 'public' | 'private';
  confirm_duplicate?: boolean;
}

/** Giới hạn ảnh tải lên khớp máy chủ (F03.07): jpg/png/webp, tối đa 10 MB. */
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** Kiểm tra ảnh phía trình duyệt trước khi gửi; trả thông báo lỗi tiếng Việt hoặc null nếu hợp lệ. */
export function validateImageFile(file: File): string | null {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) return `“${file.name}”: chỉ nhận ảnh JPG, PNG hoặc WebP.`;
  if (file.size > MAX_UPLOAD_BYTES) return `“${file.name}”: ảnh vượt quá 10 MB.`;
  return null;
}

const qs = (params: Record<string, string | number | null | undefined>): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') query.set(key, String(value));
  });
  const text = query.toString();
  return text ? `?${text}` : '';
};

export const listSeries = (query: SeriesQuery = {}, signal?: AbortSignal): Promise<Paged<ApiSeries>> =>
  apiRequest<Paged<ApiSeries>>(
    `/series${qs({ scope: query.scope, q: query.q?.trim(), hsk: query.hsk, genre: query.genre, page: query.page, size: query.size })}`,
    { signal }
  );

export const getSeries = (id: number, signal?: AbortSignal): Promise<SeriesDetail> =>
  apiRequest<SeriesDetail>(`/series/${id}`, { signal });

export const createSeries = (input: SeriesInput): Promise<ApiSeries> =>
  apiRequest<ApiSeries>('/series', { method: 'POST', body: input });

export const createChapter = (
  seriesId: number,
  input: { number: number; title?: string | null; is_trial?: boolean }
): Promise<ApiChapter> => apiRequest<ApiChapter>(`/series/${seriesId}/chapters`, { method: 'POST', body: input });

/** Sửa một phần thông tin truyện (F03.09); chỉ trường có mặt được đổi. */
export const updateSeries = (seriesId: number, changes: Partial<Omit<SeriesInput, 'confirm_duplicate'>>): Promise<ApiSeries> =>
  apiRequest<ApiSeries>(`/series/${seriesId}`, { method: 'PATCH', body: changes });

export const deleteSeries = (seriesId: number): Promise<void> => apiRequest<void>(`/series/${seriesId}`, { method: 'DELETE' });

export const updateChapter = (
  chapterId: number,
  changes: { number?: number; title?: string | null; is_trial?: boolean }
): Promise<ApiChapter> => apiRequest<ApiChapter>(`/chapters/${chapterId}`, { method: 'PATCH', body: changes });

export const deleteChapter = (chapterId: number): Promise<void> => apiRequest<void>(`/chapters/${chapterId}`, { method: 'DELETE' });

export const rateSeries = (seriesId: number, stars: number): Promise<Rating> =>
  apiRequest<Rating>(`/series/${seriesId}/rating`, { method: 'PUT', body: { stars } });

export const getChapter = (id: number, signal?: AbortSignal): Promise<ChapterDetail> =>
  apiRequest<ChapterDetail>(`/chapters/${id}`, { signal });

export const saveProgress = (
  chapterId: number,
  progress: { page_no: number; mode: 'read' | 'learn'; completed: boolean }
): Promise<ApiProgress> => apiRequest<ApiProgress>(`/chapters/${chapterId}/progress`, { method: 'PUT', body: progress });

export function uploadChapterPages(chapterId: number, files: File[]): Promise<{ results: UploadItemResult[]; created: number }> {
  const form = new FormData();
  files.forEach(file => form.append('files', file));
  return apiRequest(`/chapters/${chapterId}/pages`, { method: 'POST', body: form });
}

export function quickUpload(file: File): Promise<ApiPage> {
  const form = new FormData();
  form.append('file', file);
  return apiRequest<ApiPage>('/quick-uploads', { method: 'POST', body: form });
}

export const listQuickUploads = (page = 1, size = 20): Promise<Paged<ApiPage>> =>
  apiRequest<Paged<ApiPage>>(`/quick-uploads${qs({ page, size })}`);

export const deletePage = (pageId: number): Promise<void> => apiRequest<void>(`/pages/${pageId}`, { method: 'DELETE' });

export const listLibrary = (tab: LibraryTab, page = 1, size = 100): Promise<Paged<ApiSeries>> =>
  apiRequest<Paged<ApiSeries>>(`/library${qs({ tab, page, size })}`);

export const addToLibrary = (seriesId: number): Promise<ApiSeries> =>
  apiRequest<ApiSeries>(`/library/${seriesId}`, { method: 'PUT' });

export const removeFromLibrary = (seriesId: number): Promise<void> =>
  apiRequest<void>(`/library/${seriesId}`, { method: 'DELETE' });

export const setFavorite = (seriesId: number, isFavorite: boolean): Promise<ApiSeries> =>
  apiRequest<ApiSeries>(`/library/${seriesId}/favorite`, { method: 'PUT', body: { is_favorite: isFavorite } });

export const listContinueReading = (limit = 10): Promise<ContinueItem[]> =>
  apiRequest<ContinueItem[]>(`/reading-progress/continue${qs({ limit })}`);

export const getPage = (pageId: number, signal?: AbortSignal): Promise<ApiPage> =>
  apiRequest<ApiPage>(`/pages/${pageId}`, { signal });

export function setSeriesCover(seriesId: number, file: File): Promise<ApiSeries> {
  const form = new FormData();
  form.append('file', file);
  return apiRequest<ApiSeries>(`/series/${seriesId}/cover`, { method: 'PUT', body: form });
}

/** Vị trí mở truyện: đọc tiếp nếu có tiến độ, không thì chương đầu có trang (hoặc chương dùng thử với Khách). */
export function pickReadTarget(
  detail: SeriesDetail,
  options: { restart?: boolean; guest?: boolean } = {}
): { chapterId: number; pageNo?: number; pageId?: number } | null {
  const readable = detail.chapters.filter(c => c.page_count > 0 && (!options.guest || c.is_trial));
  const progress = detail.progress;
  if (progress && !options.restart && readable.some(c => c.id === progress.chapter_id)) {
    return { chapterId: progress.chapter_id, pageNo: progress.page_no, pageId: progress.page_id ?? undefined };
  }
  const first = [...readable].sort((a, b) => a.number - b.number)[0];
  if (!first) return null;
  // Đọc lại phải mở trang đầu; không ghi pageNo thì trình đọc sẽ quay về tiến độ đã lưu.
  return options.restart ? { chapterId: first.id, pageNo: 1 } : { chapterId: first.id };
}
