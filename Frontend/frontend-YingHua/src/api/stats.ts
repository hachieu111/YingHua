// Gọi API Thống kê (M12): tổng quan học tập, biểu đồ hoạt động, chuỗi ngày học.
import { apiRequest } from './client';

export interface LearningOverview {
  words_total: number;
  words_known: number;
  words_learning: number;
  words_ignored: number;
  cards_total: number;
  cards_due: number;
  reviews_total: number;
  reviews_today: number;
  /** 0..1; null khi chưa có lượt ôn. */
  retention_rate: number | null;
  pages_read_total: number;
  study_seconds_total: number;
  timezone: string;
}

export interface ActivityPoint {
  start: string;
  end: string;
  words_saved: number;
  reviews_count: number;
  pages_read: number;
  quizzes_done: number;
  study_seconds: number;
}

export interface ActivityDelta {
  words_saved: number;
  reviews_count: number;
  pages_read: number;
  quizzes_done: number;
  study_seconds: number;
}

export interface ActivityReport {
  granularity: 'day' | 'week' | 'month';
  timezone: string;
  points: ActivityPoint[];
  current_week: ActivityPoint;
  previous_week: ActivityPoint;
  delta: ActivityDelta;
}

export interface StudyDay {
  date: string;
  studied: boolean;
  reviews_count: number;
  pages_read: number;
}

export interface StreakReport {
  current_streak: number;
  longest_streak: number;
  studied_today: boolean;
  /** 7 ngày gần nhất, cũ nhất trước, cuối cùng là hôm nay. */
  week: StudyDay[];
  reading_hint: string | null;
  rule: string;
  timezone: string;
}

export interface TodayAction {
  /** review | reader | quiz | library | chapter_suggestions */
  type: string;
  deck: string | null;
  series_id: number | null;
  chapter_id: number | null;
  page_no: number | null;
}

export interface TodayItem {
  kind: string;
  title: string;
  message: string;
  count: number | null;
  urgent: boolean;
  priority: number;
  action: TodayAction;
}

export interface TodayPlan {
  items: TodayItem[];
  all_done: boolean;
  message: string | null;
  timezone: string;
}

export const getToday = (signal?: AbortSignal): Promise<TodayPlan> => apiRequest<TodayPlan>('/stats/today', { signal });

export const getOverview = (signal?: AbortSignal): Promise<LearningOverview> =>
  apiRequest<LearningOverview>('/stats/overview', { signal });

export const getActivity = (count = 14, signal?: AbortSignal): Promise<ActivityReport> =>
  apiRequest<ActivityReport>(`/stats/activity?granularity=day&count=${count}`, { signal });

export const getStreak = (signal?: AbortSignal): Promise<StreakReport> =>
  apiRequest<StreakReport>('/stats/streak', { signal });
