// Gọi API Ôn tập (M08): thẻ đến hạn, chấm FSRS, tạm ngưng/đặt lại, lịch sử, tổng kết.
import { apiRequest } from './client';

export type CardType = 'recognition' | 'recall' | 'listening';
export type HintSource = 'meaning' | 'context_sentence' | 'sino_vietnamese' | 'pinyin';

export interface ApiCardSide {
  term: string | null;
  pinyin: string | null;
  meaning_vi: string | null;
  sino_vietnamese: string | null;
  audio_text: string | null;
  /** Nguồn gợi ý mặt trước thẻ recall; có thể vắng khi máy chủ chưa hỗ trợ. */
  hint_source?: HintSource | null;
}

export interface ApiCardContext {
  id: number;
  snippet_url: string | null;
  sentence_zh: string;
  sentence_vi: string | null;
  source_label: string | null;
}

export interface ApiCardState {
  id: number;
  vocab_entry_id: number;
  card_type: CardType;
  state: string;
  due_at: string;
  last_review_at: string | null;
  stability: number | null;
  difficulty: number | null;
  reps: number;
  lapses: number;
  is_suspended: boolean;
}

export interface ApiDueCard extends ApiCardState {
  term: string;
  hsk_level: number | null;
  is_starred: boolean;
  front: ApiCardSide;
  back: ApiCardSide;
  note: string | null;
  context: ApiCardContext | null;
  contexts_count: number;
}

export interface DueBatch {
  total: number;
  deck: string;
  items: ApiDueCard[];
}

export interface GradeResult {
  card: ApiCardState;
  rating: number;
  reviewed_at: string;
  due_at: string;
  interval_seconds: number;
  duplicate: boolean;
  remaining_due: number;
  session_complete: boolean;
  next_card: ApiDueCard | null;
}

export interface ReviewSummary {
  status: 'no_cards' | 'due' | 'completed';
  reviewed_today: number;
  due_now: number;
  due_later_today: number;
  next_due_at: string | null;
  total_cards: number;
  /** Số từ có thẻ đến hạn (có thể vắng khi máy chủ chưa hỗ trợ). */
  due_words?: number;
  status_counts?: { learning: number; known: number; ignored: number };
  timezone: string;
}

export interface ApiReviewLog {
  id: number;
  rating: number;
  state_before: string;
  due_after: string;
  duration_ms: number | null;
  reviewed_at: string;
}

export interface ReviewHistory {
  card: ApiCardState;
  items: ApiReviewLog[];
  total: number;
  page: number;
  size: number;
}

export interface GradeBody {
  rating: 1 | 2 | 3 | 4;
  /** UUID mới cho mỗi lần HIỂN THỊ một thẻ; gửi lại cùng mã chỉ tính một lượt ôn. */
  presentation_id: string;
  duration_ms?: number;
  deck?: string;
}

export function getDueCards(deck: string, size = 20, signal?: AbortSignal): Promise<DueBatch> {
  const query = new URLSearchParams({ size: String(size), deck });
  return apiRequest<DueBatch>(`/cards/due?${query.toString()}`, { signal });
}

export function gradeCard(cardId: number, body: GradeBody): Promise<GradeResult> {
  return apiRequest<GradeResult>(`/cards/${cardId}/grade`, { method: 'POST', body });
}

export function suspendCard(cardId: number): Promise<ApiCardState> {
  return apiRequest<ApiCardState>(`/cards/${cardId}/suspend`, { method: 'POST' });
}

export function resumeCard(cardId: number): Promise<ApiCardState> {
  return apiRequest<ApiCardState>(`/cards/${cardId}/resume`, { method: 'POST' });
}

export function resetCard(cardId: number): Promise<ApiCardState> {
  return apiRequest<ApiCardState>(`/cards/${cardId}/reset`, { method: 'POST' });
}

export function getCardHistory(cardId: number, page = 1, size = 5): Promise<ReviewHistory> {
  return apiRequest<ReviewHistory>(`/cards/${cardId}/history?page=${page}&size=${size}`);
}

export function getReviewSummary(signal?: AbortSignal): Promise<ReviewSummary> {
  return apiRequest<ReviewSummary>('/review/summary', { signal });
}

export const CARD_TYPE_LABEL: Record<CardType, string> = {
  recognition: 'Nhận diện chữ',
  recall: 'Nhớ lại chữ',
  listening: 'Nghe'
};

export const CARD_STATE_LABEL: Record<string, string> = {
  learning: 'Đang học',
  review: 'Ôn tập',
  relearning: 'Học lại'
};

export const RATING_LABEL: Record<number, string> = { 1: 'Quên', 2: 'Khó', 3: 'Được', 4: 'Dễ' };
