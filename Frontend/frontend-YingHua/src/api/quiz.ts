// Gọi API Bài kiểm tra (M09): tóm tắt, tạo đề, nộp bài, lịch sử, lưu từ mở rộng.
import { ApiError, apiRequest } from './client';
import { SaveWordResult } from './vocab';

export type QuizQuestionType = 'multiple_choice' | 'fill_blank';
export type QuizTargetKind = 'saved' | 'related';
export type QuizStatus = 'in_progress' | 'submitted' | string;

export interface QuizSummary {
  eligible_words: number;
  min_words: number;
  question_count: number;
  llm_enabled: boolean;
}

export interface QuizExample {
  zh: string;
  pinyin?: string | null;
  /** Chỉ có sau khi nộp bài. */
  vi?: string | null;
}

export interface QuizQuestion {
  id: number;
  position: number;
  question_type: QuizQuestionType;
  prompt: string;
  options?: string[] | null;
  target_kind: QuizTargetKind;
  hint?: string | null;
  example?: QuizExample | null;
  // --- chỉ có sau khi nộp bài ---
  term?: string | null;
  related_to?: { vocab_entry_id: number; term: string } | null;
  can_save?: boolean | null;
  user_answer?: string | null;
  correct_answer?: string | null;
  accepted_answers?: string[] | null;
  explanation?: string | null;
  is_correct?: boolean | null;
  vocab_entry_id?: number | null;
}

export interface QuizItem {
  id: number;
  status: QuizStatus;
  source: 'llm' | 'fallback' | 'mixed' | string;
  score: number | null;
  question_count: number;
  related_score: number | null;
  related_count: number;
  note: string | null;
  created_at: string;
  submitted_at: string | null;
}

export interface QuizDetail extends QuizItem {
  questions: QuizQuestion[];
  rescheduled_terms: string[];
}

export interface QuizPage {
  items: QuizItem[];
  total: number;
  page: number;
  size: number;
}

export interface QuizAnswer {
  question_id: number;
  answer: string | null;
}

export const QUIZ_MIN_QUESTIONS = 5;
export const QUIZ_MAX_QUESTIONS = 20;

export function getQuizSummary(signal?: AbortSignal): Promise<QuizSummary> {
  return apiRequest<QuizSummary>('/quizzes/summary', { signal });
}

export function createQuiz(questionCount?: number): Promise<QuizDetail> {
  return apiRequest<QuizDetail>('/quizzes', {
    method: 'POST',
    body: questionCount === undefined ? {} : { question_count: questionCount }
  });
}

export function listQuizzes(page = 1, size = 5, signal?: AbortSignal): Promise<QuizPage> {
  return apiRequest<QuizPage>(`/quizzes?page=${page}&size=${size}`, { signal });
}

export function getQuiz(quizId: number, signal?: AbortSignal): Promise<QuizDetail> {
  return apiRequest<QuizDetail>(`/quizzes/${quizId}`, { signal });
}

export function submitQuiz(quizId: number, answers: QuizAnswer[]): Promise<QuizDetail> {
  return apiRequest<QuizDetail>(`/quizzes/${quizId}/submit`, { method: 'POST', body: { answers } });
}

export function saveQuizWord(quizId: number, questionId: number): Promise<SaveWordResult> {
  return apiRequest<SaveWordResult>(`/quizzes/${quizId}/questions/${questionId}/save-word`, { method: 'POST' });
}

export const isNotEnoughWords = (err: unknown): err is ApiError =>
  err instanceof ApiError && err.code === 'NOT_ENOUGH_WORDS_FOR_QUIZ';

export const isAlreadySubmitted = (err: unknown): boolean =>
  err instanceof ApiError && err.code === 'QUIZ_ALREADY_SUBMITTED';

/** Nhãn nguồn đề: không lộ lý do kỹ thuật của việc dùng đề dự phòng. */
export const quizSourceLabel = (source: string): string =>
  source === 'llm' || source === 'mixed' ? 'Đề AI' : 'Đề từ điển';

// --- Lưu tạm đáp án (F09.02): giữ khi tải lại trang hoặc mất mạng ---
const draftKey = (quizId: number) => `yinghua-quiz-draft-${quizId}`;

export function loadQuizDraft(quizId: number): Record<number, string> {
  try {
    const raw = localStorage.getItem(draftKey(quizId));
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const draft: Record<number, string> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === 'string') draft[Number(key)] = value;
    }
    return draft;
  } catch {
    return {};
  }
}

export function saveQuizDraft(quizId: number, draft: Record<number, string>): void {
  try {
    localStorage.setItem(draftKey(quizId), JSON.stringify(draft));
  } catch {
    // Không lưu được: đáp án vẫn còn trong phiên hiện tại.
  }
}

export function clearQuizDraft(quizId: number): void {
  try {
    localStorage.removeItem(draftKey(quizId));
  } catch {
    // Bỏ qua.
  }
}
