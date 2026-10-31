// Gọi API Gamification (M16): XP, nhiệm vụ, mục tiêu tuần, bảng xếp hạng, mùa thi đua, huy hiệu, mini-game Phi Kiếm Trảm Tự.
import { Paged } from './library';
import { apiRequest } from './client';

export interface Badge {
  code: string;
  name: string;
  tier: number;
  style_key: string;
}

export interface FrameInfo {
  code: string;
  name: string;
  style_key: string;
}

export interface GamificationMe {
  xp_today: number;
  xp_season: number;
  xp_total: number;
  season_rank: number | null;
  streak_current: number;
  next_streak_milestone: { days: number; days_left: number } | null;
  equipped_badge: Badge | null;
}

export interface WeeklyActivity {
  week_start: string;
  days: { date: string; xp: number }[];
  total: number;
}

export interface Quest {
  code: string;
  name: string;
  progress: number;
  target: number;
  xp: number;
  completed: boolean;
  rewarded_at: string | null;
}

export interface QuestsToday {
  date: string;
  quests: Quest[];
  completed_count: number;
  total: number;
  bonus_coins: number;
  bonus_granted: boolean;
}

export interface WeeklyGoal {
  week_start: string;
  goal: number;
  rewarded_goal: number;
  pages_read: number;
  pages_left: number;
  percent: number;
  reward_xp: number;
  reward_frame_code: string;
  reward_frame_days: number;
  rewarded_at: string | null;
}

export type LeaderboardMetric = 'exp' | 'vocab' | 'pages' | 'streak';
export type LeaderboardPeriod = 'week' | 'month' | 'all';

export interface BoardRow {
  rank: number | null;
  display_name: string;
  avatar_url: string | null;
  avatar_preset: string | null;
  hsk_level: number | null;
  score: number;
  unit: string;
  badge: Badge | null;
  frame: FrameInfo | null;
  is_vip: boolean;
  is_me: boolean;
  anonymous: boolean;
}

export interface Leaderboard {
  items: BoardRow[];
  total: number;
  page: number;
  size: number;
  me: BoardRow;
  me_hidden: boolean;
  me_hidden_note: string | null;
  next_milestone: { rank: number; xp_missing: number; ratio: number } | null;
  summary: { learners: number; pages_in_period: number; season_xp: number };
}

export interface SeasonTier {
  tier: 'top3' | 'top10' | 'top50';
  rank_from: number;
  rank_to: number;
  coins: number;
  tickets: number;
  vip_days: number;
  frame_code: string | null;
  badge_code: string | null;
}

export interface CurrentSeason {
  id: number;
  number: number;
  starts_at: string;
  ends_at: string;
  /** Giờ máy chủ: đếm ngược dựa vào đây, không tin đồng hồ máy. */
  server_now: string;
  seconds_left: number;
  status: 'active' | 'finalizing' | 'finalized';
  finalizing_previous: boolean;
  tiers: SeasonTier[];
  min_xp: number;
  my_rank: number | null;
  my_xp: number;
  my_tier: SeasonTier['tier'] | null;
}

export interface SeasonResult {
  season_number: number;
  starts_at: string;
  ends_at: string;
  rank: number;
  xp: number;
  tier: SeasonTier['tier'];
  reward_granted_at: string | null;
}

export interface Achievement {
  code: string;
  name: string;
  description: string;
  style_key: string;
  tier: number;
  max_tier: number;
  progress: number;
  next_threshold: number | null;
  thresholds: number[];
  unlocked_at: string | null;
  equipped: boolean;
}

export interface EquippedBadge {
  achievement_code: string | null;
  name: string | null;
  tier: number | null;
  style_key: string | null;
}

export interface WeakRadicals {
  radicals: { radical: string; count: number }[];
  fallback: boolean;
  message: string | null;
}

export type BladeMode = 'hsk' | 'weak_radical';
export type BladeRank = 'S' | 'A' | 'B' | 'C';

export interface BladeItem {
  index: number;
  text: string;
  pinyin: string;
  /** Các cách gõ được chấp nhận (không dấu). */
  answers: string[];
  han_viet: string | null;
  hsk_level: number | null;
  is_boss: boolean;
}

export interface BladeRound {
  round_id: string;
  mode: BladeMode;
  hsk_band: number | null;
  radical: string | null;
  seconds: number;
  lives: number;
  items: BladeItem[];
}

export interface BladeRoundRequest {
  mode: BladeMode;
  /** 1..6 là HSK tương ứng, 7 là nhóm HSK 7-9. */
  hsk_band: number | null;
  radical: string | null;
}

export interface BladeEvent {
  index: number;
  result: 'hit' | 'miss';
  /** Mốc tính từ lúc bắt đầu ván, đã trừ thời gian tạm dừng; không giảm dần. */
  ms: number;
}

export interface BladeSessionRequest {
  round_id: string;
  events: BladeEvent[];
  typos: number;
  duration_ms: number;
}

export interface BladeMissedItem {
  text: string;
  pinyin: string;
  han_viet: string | null;
}

export interface BladeSession {
  id: number;
  mode: BladeMode;
  hsk_band: number | null;
  radical: string | null;
  score: number;
  correct: number;
  wrong: number;
  typos: number;
  max_combo: number;
  /** Tỉ lệ 0..1. */
  accuracy: number;
  rank: BladeRank;
  duration_ms: number;
  xp_awarded: number;
  is_best: boolean;
  missed: BladeMissedItem[];
}

export interface BladeBest {
  mode: BladeMode;
  hsk_band: number | null;
  best_score: number;
  best_combo: number;
  plays: number;
}

const PREFIX = '/gamification';

export const getMyGamification = (signal?: AbortSignal): Promise<GamificationMe> =>
  apiRequest<GamificationMe>(`${PREFIX}/me`, { signal });

export const getWeeklyActivity = (signal?: AbortSignal): Promise<WeeklyActivity> =>
  apiRequest<WeeklyActivity>(`${PREFIX}/me/weekly-activity`, { signal });

export const getQuestsToday = (signal?: AbortSignal): Promise<QuestsToday> =>
  apiRequest<QuestsToday>(`${PREFIX}/quests/today`, { signal });

export const getWeeklyGoal = (signal?: AbortSignal): Promise<WeeklyGoal> =>
  apiRequest<WeeklyGoal>(`${PREFIX}/weekly-goal`, { signal });

export const getLeaderboard = (
  query: { metric: LeaderboardMetric; period: LeaderboardPeriod; page: number; size: number },
  signal?: AbortSignal
): Promise<Leaderboard> => {
  const params = new URLSearchParams({
    metric: query.metric,
    period: query.period,
    page: String(query.page),
    size: String(query.size)
  });
  return apiRequest<Leaderboard>(`${PREFIX}/leaderboard?${params.toString()}`, { signal });
};

export const getCurrentSeason = (signal?: AbortSignal): Promise<CurrentSeason> =>
  apiRequest<CurrentSeason>(`${PREFIX}/seasons/current`, { signal });

export const listMySeasons = (page = 1, size = 20, signal?: AbortSignal): Promise<Paged<SeasonResult>> =>
  apiRequest<Paged<SeasonResult>>(`${PREFIX}/seasons/me?page=${page}&size=${size}`, { signal });

export const listAchievements = (signal?: AbortSignal): Promise<Achievement[]> =>
  apiRequest<Achievement[]>(`${PREFIX}/achievements`, { signal });

/** Đeo huy hiệu đã mở khóa; truyền null để tháo. */
export const equipAchievement = (achievementCode: string | null): Promise<EquippedBadge> =>
  apiRequest<EquippedBadge>(`${PREFIX}/achievements/equipped`, { method: 'PUT', body: { achievement_code: achievementCode } });

export const getWeakRadicals = (signal?: AbortSignal): Promise<WeakRadicals> =>
  apiRequest<WeakRadicals>(`${PREFIX}/minigames/radicals/weak`, { signal });

/** Dựng một ván Phi Kiếm Trảm Tự (F16.01). */
export const buildBladeRound = (body: BladeRoundRequest, signal?: AbortSignal): Promise<BladeRound> =>
  apiRequest<BladeRound>(`${PREFIX}/minigames/blade/rounds`, { method: 'POST', body, signal });

/** Nộp diễn biến ván; máy chủ tự chấm điểm, hạng và XP. */
export const submitBladeSession = (body: BladeSessionRequest): Promise<BladeSession> =>
  apiRequest<BladeSession>(`${PREFIX}/minigames/blade/sessions`, { method: 'POST', body });

export const getBladeBest = (signal?: AbortSignal): Promise<BladeBest[]> =>
  apiRequest<BladeBest[]>(`${PREFIX}/minigames/blade/best`, { signal });

/** Nhãn bậc thưởng mùa. */
export const TIER_LABEL: Record<SeasonTier['tier'], string> = {
  top3: 'Top 1 ~ 3',
  top10: 'Top 4 ~ 10',
  top50: 'Top 11 ~ 50'
};
