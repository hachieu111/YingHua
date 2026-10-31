import React, { useState } from 'react';
import { BookOpen, Flame, Layers, Star } from 'lucide-react';
import { LeaderboardMetric, LeaderboardPeriod, getLeaderboard } from '../api/gamification';
import { useApiResource } from '../utils/useApiResource';
import { DailyQuestsCard, GamificationLinksCard, WeeklyActivityCard } from './GamificationCards';
import { LeaderboardPodium } from './LeaderboardPodium';
import { LeaderboardRows, MyRankCard } from './LeaderboardRows';
import { SeasonBanner, SeasonHistoryCard, SeasonRewardsCard, useCurrentSeason } from './SeasonPanel';
import { WeeklyGoalCard } from './WeeklyGoalCard';
import { useTourPage } from '../tour/TourProvider';

interface LeaderboardPageProps {
  isLoggedIn: boolean;
  /** Mở khu Kiểm tra cá nhân hóa (M09). */
  onStartQuiz: () => void;
  onNavigateToReader: () => void;
  onNavigateToFlashcards: () => void;
  /** Mở hộp thoại đăng nhập (Khách chỉ xem được phần giới thiệu). */
  onRequireLogin: (message: string) => void;
  /** Mở cài đặt riêng tư để bật/tắt hiện tên trên bảng xếp hạng. */
  onOpenPrivacySettings: () => void;
}

const PAGE_SIZE = 20;
const PODIUM_SIZE = 3;

const METRICS: { id: LeaderboardMetric; label: string; Icon: typeof Flame }[] = [
  { id: 'streak', label: 'Chuỗi Streak', Icon: Flame },
  { id: 'exp', label: 'Điểm EXP Học Tập', Icon: Star },
  { id: 'vocab', label: 'Từ vựng ghi nhớ', Icon: Layers },
  { id: 'pages', label: 'Trang Manhua đã đọc', Icon: BookOpen }
];

const PERIODS: { id: LeaderboardPeriod; label: string }[] = [
  { id: 'week', label: 'Tuần này' },
  { id: 'month', label: 'Tháng này' },
  { id: 'all', label: 'Toàn thời gian' }
];

export const LeaderboardPage: React.FC<LeaderboardPageProps> = ({
  isLoggedIn,
  onStartQuiz,
  onNavigateToReader,
  onNavigateToFlashcards,
  onRequireLogin,
  onOpenPrivacySettings
}) => {
  useTourPage(isLoggedIn ? 'leaderboard' : null);
  const [period, setPeriod] = useState<LeaderboardPeriod>('week');
  const [metric, setMetric] = useState<LeaderboardMetric>('exp');
  const [page, setPage] = useState(1);
  const season = useCurrentSeason(isLoggedIn);
  const board = useApiResource(signal => getLeaderboard({ metric, period, page, size: PAGE_SIZE }, signal), [metric, period, page], isLoggedIn);

  const activeMetric = METRICS.find(item => item.id === metric) ?? METRICS[1];
  const activePeriod = PERIODS.find(item => item.id === period) ?? PERIODS[0];
  const data = board.data;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const showPodium = !!data && page === 1;
  const listRows = data ? (showPodium ? data.items.slice(PODIUM_SIZE) : data.items) : [];

  const changeMetric = (next: LeaderboardMetric) => {
    setMetric(next);
    setPage(1);
  };
  const changePeriod = (next: LeaderboardPeriod) => {
    setPeriod(next);
    setPage(1);
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-10">
      {/* HEADER SECTION & SEASON INFO */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="flex flex-col gap-2 max-w-2xl">
          {isLoggedIn ? (
            <SeasonBanner state={season} />
          ) : (
            <span className="inline-flex w-fit items-center gap-1.5 px-3 py-1 rounded-full bg-[#ffd8e7] dark:bg-pink-900/30 text-[#85145a] dark:text-pink-300 font-bold text-xs shadow-xs dark:shadow-none">
              <span>🌸</span> Mùa Đua Top Hoa Anh Đào
            </span>
          )}

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-800 dark:text-white tracking-tight flex items-center gap-3 font-['Plus_Jakarta_Sans']">
            <span>Bảng Vàng Danh Dự Yinghua</span>
            <span className="text-[#a43073] dark:text-pink-400 font-['Noto_Serif_SC'] italic text-2xl font-light">榜样</span>
          </h1>

          <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
            Nỗ lực tích luỹ từng từ vựng trong trang manhua, mở rộng cánh cửa tri thức Hán ngữ. Đua top sôi nổi, rinh trọn huy hiệu mùa giải danh giá và đặc quyền đọc truyện không giới hạn!
          </p>
        </div>

        {data && (
          <div className="grid grid-cols-3 sm:flex sm:items-center sm:gap-4 w-full lg:w-auto p-3 rounded-2xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 transition-colors duration-300">
            <div className="px-2 sm:px-3 py-1 border-r border-slate-100 dark:border-slate-700 flex flex-col gap-0.5 min-w-0">
              <span className="text-[10px] leading-tight text-slate-400 dark:text-slate-500 font-bold uppercase">Tổng học viên</span>
              <span className="text-lg sm:text-xl font-bold text-[#0060ac] truncate dark:text-blue-300">{data.summary.learners.toLocaleString('vi-VN')}</span>
            </div>
            <div className="px-2 sm:px-3 py-1 border-r border-slate-100 dark:border-slate-700 flex flex-col gap-0.5 min-w-0">
              <span className="text-[10px] leading-tight text-slate-400 dark:text-slate-500 font-bold uppercase">Trang truyện đọc</span>
              <span className="text-lg sm:text-xl font-bold text-[#a43073] truncate dark:text-pink-400">{data.summary.pages_in_period.toLocaleString('vi-VN')}</span>
            </div>
            <div className="px-2 sm:px-3 py-1 flex flex-col gap-0.5 min-w-0">
              <span className="text-[10px] leading-tight text-slate-400 dark:text-slate-500 font-bold uppercase">Điểm EXP mùa này</span>
              <span className="text-lg sm:text-xl font-bold text-amber-600 truncate dark:text-amber-400">{data.summary.season_xp.toLocaleString('vi-VN')}</span>
            </div>
          </div>
        )}
      </div>

      {!isLoggedIn ? (
        <div className="rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 p-10 text-center flex flex-col items-center gap-3 transition-colors duration-300">
          <span className="material-symbols-outlined text-[44px] text-pink-300 dark:text-pink-400">lock</span>
          <h2 className="text-lg font-bold text-slate-800 dark:text-white">Đăng nhập để xem bảng xếp hạng</h2>
          <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">
            Bảng vàng, nhiệm vụ ngày và phần thưởng mùa giải gắn với tài khoản của bạn. Đăng nhập để so tài cùng cộng đồng.
          </p>
          <button
            type="button"
            onClick={() => onRequireLogin('Vui lòng đăng nhập để xem bảng xếp hạng và nhận thưởng mùa giải!')}
            className="px-6 py-2.5 rounded-full bg-[#a43073] text-white text-xs font-bold shadow-md hover:opacity-95"
          >
            Đăng nhập
          </button>
        </div>
      ) : (
        <>
          {/* FILTER CONTROLS BAR */}
          <div data-tour="board-filters" className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 p-2 bg-[#eff4ff] dark:bg-[#0f172a] rounded-2xl border border-blue-100 dark:border-slate-800 transition-colors duration-300">
            <div role="group" aria-label="Lọc theo thời gian" className="flex items-center p-1 rounded-full bg-white dark:bg-[#1e293b] shadow-xs dark:shadow-none gap-1 shrink-0 overflow-x-auto max-w-full">
              {PERIODS.map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => changePeriod(id)}
                  aria-pressed={period === id}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                    period === id ? 'bg-[#f472b6] text-white shadow-xs dark:bg-[#a43073]' : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div role="tablist" aria-label="Chọn bảng xếp hạng" className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 custom-scrollbar">
              {METRICS.map(({ id, label, Icon }) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={metric === id}
                  onClick={() => changeMetric(id)}
                  className={`inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                    metric === id ? 'bg-[#0060ac] text-white shadow-xs' : 'bg-white dark:bg-[#1e293b] text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" strokeWidth={2} aria-hidden="true" />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* LEFT COLUMN: bục top 3, thẻ vị trí của bạn, danh sách */}
            <div className="lg:col-span-8 flex flex-col gap-8">
              {board.loading && (
                <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-500 dark:text-slate-400" role="status">
                  <span className="w-5 h-5 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
                  Đang tải bảng xếp hạng...
                </div>
              )}
              {board.error && !data && (
                <div role="alert" className="rounded-3xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-900/50 p-6 text-center text-sm text-rose-700 dark:text-rose-300">
                  <p>{board.error}</p>
                  <button type="button" onClick={board.reload} className="mt-3 px-4 py-2 rounded-full bg-white text-rose-700 text-xs font-bold dark:bg-slate-800 dark:text-rose-400">
                    Thử lại
                  </button>
                </div>
              )}

              {data && (
                <>
                  {showPodium && <LeaderboardPodium top={data.items.slice(0, PODIUM_SIZE)} metricLabel={activeMetric.label} />}
                  {showPodium && data.items.length === 0 && (
                    <p className="text-center text-sm text-slate-500 dark:text-slate-400">Chưa ai có điểm ở bảng này. Hãy là người đầu tiên!</p>
                  )}

                  <MyRankCard data={data} periodLabel={activePeriod.label} onOpenPrivacy={onOpenPrivacySettings} />

                  <LeaderboardRows rows={listRows} unitLabel={data.me.unit} startRank={(page - 1) * PAGE_SIZE + (showPodium ? PODIUM_SIZE : 0) + 1} />

                  {totalPages > 1 && (
                    <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                      <span>
                        Trang {page}/{totalPages} · {data.total.toLocaleString('vi-VN')} người học
                      </span>
                      <div className="flex gap-1.5">
                        <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-4 py-1.5 rounded-full bg-white border border-pink-100 font-bold text-[#a43073] disabled:opacity-40 dark:bg-slate-800 dark:border-pink-900/40 dark:text-pink-400">
                          Trước
                        </button>
                        <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="px-4 py-1.5 rounded-full bg-white border border-pink-100 font-bold text-[#a43073] disabled:opacity-40 dark:bg-slate-800 dark:border-pink-900/40 dark:text-pink-400">
                          Sau
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* RIGHT COLUMN: thưởng mùa, nhiệm vụ, mục tiêu tuần, hoạt động tuần */}
            <div className="lg:col-span-4 flex flex-col gap-6">
              <div data-tour="board-season">
              <SeasonRewardsCard state={season} />
              </div>
              <div data-tour="board-quests">
              <DailyQuestsCard actions={{ onRead: onNavigateToReader, onReview: onNavigateToFlashcards, onQuiz: onStartQuiz }} />
              </div>
              <div data-tour="board-goal">
              <WeeklyGoalCard />
              </div>
              <WeeklyActivityCard />
              <GamificationLinksCard />
              <SeasonHistoryCard enabled />
            </div>
          </div>
        </>
      )}
    </div>
  );
};
