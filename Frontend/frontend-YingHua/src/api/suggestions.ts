// Gọi API Gợi ý từ (M10): từ nên học trong chương, nhận vào Sổ tay, bỏ qua / khôi phục.
import { ApiError, apiRequest } from './client';
import { SaveWordResult } from './vocab';

export interface SuggestionItem {
  term: string;
  pinyin: string | null;
  meaning_vi: string | null;
  hsk_level: number | null;
  occurrences: number;
  lookups: number;
  score: number;
  bubble_id: number;
  page_id: number;
  page_no: number;
}

export interface SuggestionList {
  status: 'ready' | 'processing' | string;
  hsk_level: number | null;
  items: SuggestionItem[];
}

export interface DismissedItem {
  term: string;
  dismissed_at: string;
  pinyin: string | null;
  meaning_vi: string | null;
  hsk_level: number | null;
}

export interface DismissedPage {
  items: DismissedItem[];
  total: number;
  page: number;
  size: number;
}

export function listSuggestions(chapterId: number, limit = 20, signal?: AbortSignal): Promise<SuggestionList> {
  return apiRequest<SuggestionList>(`/chapters/${chapterId}/suggestions?limit=${limit}`, { signal });
}

export function acceptSuggestion(chapterId: number, term: string): Promise<SaveWordResult> {
  return apiRequest<SaveWordResult>(`/chapters/${chapterId}/suggestions/accept`, { method: 'POST', body: { term } });
}

export function dismissSuggestion(term: string): Promise<void> {
  return apiRequest<void>(`/suggestions/dismissed/${encodeURIComponent(term)}`, { method: 'PUT' });
}

export function restoreSuggestion(term: string): Promise<void> {
  return apiRequest<void>(`/suggestions/dismissed/${encodeURIComponent(term)}`, { method: 'DELETE' });
}

export function listDismissed(page = 1, size = 20, signal?: AbortSignal): Promise<DismissedPage> {
  return apiRequest<DismissedPage>(`/suggestions/dismissed?page=${page}&size=${size}`, { signal });
}

/** 409: từ đã có đúng ngữ cảnh này trong Sổ tay (coi như đã nhận). */
export const isSuggestionAlreadySaved = (err: unknown): boolean =>
  err instanceof ApiError && err.code === 'VOCAB_CONTEXT_ALREADY_SAVED';

export interface RecommendedSeries {
  id: number;
  title_vi: string;
  title_zh: string | null;
  cover_url: string | null;
  est_hsk_level: number | null;
  genres: string[];
  rating_avg: number | null;
  rating_count: number;
  chapter_count: number;
  reason: string;
}

export interface SeriesRecommendations {
  hsk_level: number | null;
  needs_level: boolean;
  items: RecommendedSeries[];
}

/** Gợi ý truyện theo trình độ HSK đã khai báo (F10.04). */
export function listSeriesRecommendations(limit = 3, signal?: AbortSignal): Promise<SeriesRecommendations> {
  return apiRequest<SeriesRecommendations>(`/series/recommendations?limit=${limit}`, { signal });
}

export interface ChapterCoverage {
  hsk_level: number | null;
  needs_level: boolean;
  known_terms: number;
  total_terms: number;
  percent: number;
  status: 'ready' | 'processing' | 'empty' | string;
}

/** Độ phủ từ vựng của chương: đã nắm X/Y từ HSK n (F10.05). */
export function getChapterCoverage(chapterId: number, signal?: AbortSignal): Promise<ChapterCoverage> {
  return apiRequest<ChapterCoverage>(`/chapters/${chapterId}/vocab-coverage`, { signal });
}
