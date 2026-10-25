// Gọi API Từ điển (M06): tìm kiếm, tra từ, từ vựng trong ngày, phân rã chữ, tách câu.
import { apiRequest } from './client';

export interface SearchHit {
  term: string;
  pinyin: string;
  han_viet: string | null;
  preview: string | null;
  hsk_level: number | null;
}

export interface SearchPage {
  items: SearchHit[];
  total: number;
  page: number;
  size: number;
}

export interface ApiExample {
  zh: string;
  pinyin: string | null;
  vi: string | null;
  /** gloss (Thiên Chửu) · tatoeba · llm */
  source: string;
}

export interface ApiDefinition {
  source: string;
  gloss: string;
}

export interface ApiReading {
  pinyin: string;
  han_viet: string | null;
  part_of_speech: string[];
  definitions: ApiDefinition[];
  english: string[];
  examples: ApiExample[];
}

export interface ApiHsk {
  level: number | null;
  source: 'list' | 'derived' | 'none';
}

export interface ApiSpecialized {
  kind: string;
  label: string;
  meanings: string[];
}

export interface ApiCharacter {
  ch: string;
  found: boolean;
  pinyin: string | null;
  han_viet: string | null;
  radical: string | null;
  stroke_count: number | null;
  decomposition: string | null;
  components: string[];
  definition_en: string | null;
  /** Path SVG từng nét; rỗng/thiếu nếu chưa có dữ liệu nét. */
  strokes?: string[];
  /** Điểm [x, y] của đường trung tuyến từng nét. */
  medians?: number[][][];
  etymology?: {
    type?: string | null;
    hint?: string | null;
    phonetic?: string | null;
    semantic?: string | null;
  } | null;
}

export interface WordLookup {
  term: string;
  found: boolean;
  pinyin: string | null;
  han_viet: string | null;
  hsk: ApiHsk;
  readings: ApiReading[];
  specialized: ApiSpecialized[];
  characters: ApiCharacter[];
  /** true: Khách chỉ thấy phần cơ bản. */
  limited: boolean;
}

export interface WordOfTheDay {
  term: string;
  pinyin: string;
  han_viet: string | null;
  meaning: string;
  hsk_level: number;
  example: ApiExample | null;
}

export interface SegmentToken {
  text: string;
  pinyin: string | null;
  lookupable: boolean;
}

export function searchWords(q: string, page = 1, size = 8): Promise<SearchPage> {
  const query = new URLSearchParams({ q, page: String(page), size: String(size) });
  return apiRequest<SearchPage>(`/dictionary/search?${query.toString()}`);
}

export function lookupWord(term: string): Promise<WordLookup> {
  return apiRequest<WordLookup>(`/dictionary/lookup?term=${encodeURIComponent(term)}`);
}

export function getWordOfTheDay(): Promise<WordOfTheDay> {
  return apiRequest<WordOfTheDay>('/dictionary/word-of-the-day');
}

export async function decomposeCharacters(text: string): Promise<ApiCharacter[]> {
  const data = await apiRequest<{ characters: ApiCharacter[] }>(
    `/dictionary/characters?text=${encodeURIComponent(text)}`
  );
  return data.characters;
}

export async function segmentSentence(text: string): Promise<SegmentToken[]> {
  const data = await apiRequest<{ tokens: SegmentToken[] }>('/dictionary/segment', {
    method: 'POST',
    body: { text }
  });
  return data.tokens;
}

/** Nhãn cấp HSK hiển thị: 7 = nhóm 7–9 của HSK 3.0. */
export function hskLabel(level: number | null | undefined): string {
  if (level === null || level === undefined) return 'Ngoài HSK';
  return level >= 7 ? 'HSK 7–9' : `HSK ${level}`;
}
