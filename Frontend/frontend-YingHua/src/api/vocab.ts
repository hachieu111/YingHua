// Gọi API Sổ tay (M07): lưu từ, danh sách, chi tiết, sửa, xóa, bộ thẻ.
import { ApiError, apiRequest } from './client';

export type VocabStatus = 'learning' | 'known' | 'ignored';
export type VocabSource = 'highlight' | 'lookup' | 'suggestion' | 'manual' | 'quiz';

export interface SaveWordBody {
  term: string;
  source: VocabSource;
  bubble_id?: number;
  page_id?: number;
  meaning_vi?: string;
}

export interface ApiContextBrief {
  id: number;
  snippet_url: string | null;
  sentence_zh: string;
  sentence_vi: string | null;
  source_label: string | null;
}

export interface ApiContextSource {
  series_id: number | null;
  series_title: string | null;
  chapter_id: number | null;
  chapter_number: number | null;
  page_id: number;
  page_no: number;
}

export interface ApiVocabContext extends ApiContextBrief {
  bubble_id: number | null;
  page_id: number | null;
  source: ApiContextSource | null;
  created_at: string;
}

export interface ApiSrsSummary {
  card_count: number;
  due_count: number;
  review_count: number;
  next_due_at: string | null;
}

export interface ApiCardBrief {
  id: number;
  card_type: 'recognition' | 'recall' | 'listening';
  state: string;
  due_at: string;
  last_review_at: string | null;
  is_suspended: boolean;
  reps: number;
  lapses: number;
}

interface VocabEntryBase {
  id: number;
  term: string;
  pinyin: string | null;
  meaning_vi: string | null;
  sino_vietnamese: string | null;
  hsk_level: number | null;
  hsk_source: 'list' | 'derived' | 'none';
  status: VocabStatus;
  source: string;
  note: string | null;
  is_starred: boolean;
  is_due: boolean;
  srs: ApiSrsSummary | null;
  contexts_count: number;
  created_at: string;
  updated_at: string;
}

export interface ApiVocabItem extends VocabEntryBase {
  first_context: ApiContextBrief | null;
}

export interface ApiVocabDetail extends VocabEntryBase {
  contexts: ApiVocabContext[];
  cards: ApiCardBrief[];
}

export interface SaveWordResult {
  entry: ApiVocabDetail;
  created: boolean;
  context_added: boolean;
  cards_created: number;
  snippet_missing: boolean;
}

export interface VocabPage {
  items: ApiVocabItem[];
  total: number;
  page: number;
  size: number;
}

export interface VocabListParams {
  status?: VocabStatus;
  hsk?: number | 'none';
  q?: string;
  starred?: boolean;
  due?: boolean;
  seriesId?: number;
  page?: number;
  size?: number;
}

export interface ApiDeck {
  key: string;
  kind: 'starred' | 'series';
  series_id: number | null;
  title: string;
  word_count: number;
  reviewed_count: number;
  due_count: number;
}

export interface UpdateVocabBody {
  status?: VocabStatus;
  note?: string | null;
  meaning_vi?: string;
  is_starred?: boolean;
}

export function saveWord(body: SaveWordBody): Promise<SaveWordResult> {
  return apiRequest<SaveWordResult>('/vocab-entries', { method: 'POST', body });
}

export function listVocab(params: VocabListParams = {}, signal?: AbortSignal): Promise<VocabPage> {
  const query = new URLSearchParams();
  if (params.status) query.set('status', params.status);
  if (params.hsk !== undefined) query.set('hsk', String(params.hsk));
  if (params.q) query.set('q', params.q);
  if (params.starred !== undefined) query.set('starred', String(params.starred));
  if (params.seriesId !== undefined) query.set('series_id', String(params.seriesId));
  if (params.due !== undefined) query.set('due', String(params.due));
  query.set('page', String(params.page ?? 1));
  query.set('size', String(params.size ?? 20));
  return apiRequest<VocabPage>(`/vocab-entries?${query.toString()}`, { signal });
}

/** Tổng số từ trong Sổ tay (dùng cho số liệu tóm tắt). */
export async function countVocab(signal?: AbortSignal): Promise<number> {
  return (await listVocab({ size: 1 }, signal)).total;
}

export function getVocab(id: number, signal?: AbortSignal): Promise<ApiVocabDetail> {
  return apiRequest<ApiVocabDetail>(`/vocab-entries/${id}`, { signal });
}

export function updateVocab(id: number, body: UpdateVocabBody): Promise<ApiVocabDetail> {
  return apiRequest<ApiVocabDetail>(`/vocab-entries/${id}`, { method: 'PATCH', body });
}

export function deleteVocab(id: number): Promise<void> {
  return apiRequest<void>(`/vocab-entries/${id}`, { method: 'DELETE' });
}

export function deleteVocabContext(id: number, contextId: number): Promise<void> {
  return apiRequest<void>(`/vocab-entries/${id}/contexts/${contextId}`, { method: 'DELETE' });
}

export async function listDecks(signal?: AbortSignal): Promise<ApiDeck[]> {
  return (await apiRequest<{ items: ApiDeck[] }>('/vocab-entries/decks', { signal })).items;
}

/** Thông báo đúng sự thật sau khi lưu từ (F07.01, F07.02). */
export function saveResultMessage(term: string, result: SaveWordResult): string {
  if (result.created) return `Đã lưu “${term}” vào Sổ tay (kèm ${result.cards_created} thẻ ôn)`;
  if (result.context_added) return `Đã thêm ngữ cảnh mới cho “${term}”`;
  return `“${term}” đã có trong Sổ tay`;
}

/** 409 VOCAB_CONTEXT_ALREADY_SAVED: từ đã có đúng ngữ cảnh này, không phải lỗi thật sự. */
export const isAlreadySaved = (err: unknown): boolean =>
  err instanceof ApiError && err.code === 'VOCAB_CONTEXT_ALREADY_SAVED';

export interface AiExample {
  zh: string;
  pinyin: string | null;
  vi: string | null;
}

export interface AiNote {
  vocab_entry_id: number;
  source: 'llm' | 'fallback' | string;
  source_label: string;
  examples: AiExample[];
  mnemonic: string | null;
  phrases: AiExample[];
  generated_at: string;
  regenerate_count: number;
  regenerate_remaining: number;
}

/** Thẻ mở rộng AI của mục từ (F08.11); chưa có thì máy chủ tạo rồi trả. */
export const getAiNote = (entryId: number, signal?: AbortSignal): Promise<AiNote> =>
  apiRequest<AiNote>(`/vocab-entries/${entryId}/ai-note`, { signal });

export const regenerateAiNote = (entryId: number): Promise<AiNote> =>
  apiRequest<AiNote>(`/vocab-entries/${entryId}/ai-note/regenerate`, { method: 'POST' });

/** 429 AI_NOTE_REGENERATE_LIMIT: hết lượt Tạo lại cho từ này. */
export const isAiRegenerateLimit = (err: unknown): boolean => err instanceof ApiError && err.code === 'AI_NOTE_REGENERATE_LIMIT';
