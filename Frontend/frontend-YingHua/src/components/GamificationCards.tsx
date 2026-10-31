import React from 'react';
import { Link } from 'react-router';
import { Quest, getQuestsToday, getWeeklyActivity } from '../api/gamification';
import { BLADE_GAME_PATH, REWARD_SHOP_PATH } from '../routes';
import { useApiResource } from '../utils/useApiResource';

const WEEKDAYS = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
const weekdayOf = (iso: string): string => WEEKDAYS[new Date(`${iso}T00:00:00`).getDay()];

const ErrorLine: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
    {message}{' '}
    <button type="button" onClick={onRetry} className="font-bold underline">
      Thử lại
    </button>
  </p>
);

export interface QuestActions {
  /** Mở trình đọc để làm nhiệm vụ đọc trang. */
  onRead: () => void;
  /** Mở flashcard để ôn thẻ. */
  onReview: () => void;
  /** Mở khu Kiểm tra cá nhân hóa (M09). */
  onQuiz: () => void;
}

const QUEST_ICON: Record<string, string> = { read_pages: 'auto_stories', review_cards: 'style', take_quiz: 'quiz' };

const QuestRow: React.FC<{ quest: Quest; onGo: (() => void) | undefined }> = ({ quest, onGo }) => (
  <div className={`flex items-center justify-between gap-2 p-3 rounded-2xl ${quest.completed ? 'bg-slate-50 dark:bg-slate-800' : 'bg-[#eff4ff] dark:bg-[#1e293b]'}`}>
    <div className="flex items-center gap-2.5 min-w-0">
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
          quest.completed ? 'bg-[#a43073] text-white' : 'bg-white text-blue-700 shadow-xs dark:bg-slate-800 dark:text-blue-400'
        }`}
      >
        <span className="material-symbols-outlined text-[14px]">{quest.completed ? 'check' : (QUEST_ICON[quest.code] ?? 'task_alt')}</span>
      </div>
      <div className="flex flex-col min-w-0">
        <span className={`text-xs font-bold ${quest.completed ? 'line-through text-slate-500 dark:text-slate-400' : 'text-slate-800 dark:text-slate-100'}`}>{quest.name}</span>
        <span className="text-[10px] text-slate-400">
          {quest.completed ? 'Đã hoàn thành' : `Tiến độ ${Math.min(quest.progress, quest.target)}/${quest.target}`}
        </span>
      </div>
    </div>
    {quest.completed ? (
      <span className="px-2 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[10px] font-bold shrink-0 dark:bg-pink-900/30 dark:text-pink-400">+{quest.xp} XP ✓</span>
    ) : onGo ? (
      <button
        type="button"
        onClick={onGo}
        className="px-3 py-1 rounded-full bg-[#0060ac] text-white text-[11px] font-bold hover:bg-[#004883] transition-colors shrink-0"
      >
        Làm ngay (+{quest.xp} XP)
      </button>
    ) : (
      <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-900 text-[10px] font-bold shrink-0 dark:bg-blue-900/30 dark:text-blue-300">+{quest.xp} XP</span>
    )}
  </div>
);

/** Nhiệm vụ ngày kèm tiến độ thật; thưởng được máy chủ cộng tự động khi đủ (F16.04). */
export const DailyQuestsCard: React.FC<{ actions: QuestActions }> = ({ actions }) => {
  const { data, loading, error, reload } = useApiResource(signal => getQuestsToday(signal), []);
  const goTo: Record<string, () => void> = { read_pages: actions.onRead, review_cards: actions.onReview, take_quiz: actions.onQuiz };
  return (
    <div className="rounded-3xl bg-white p-6 shadow-soft border border-pink-100 dark:bg-slate-800 dark:border-pink-900/40">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#0060ac] text-[22px] dark:text-blue-300">task_alt</span>
          <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Nhiệm Vụ Kiếm EXP</h3>
        </div>
        {data && (
          <span className="text-xs font-bold text-[#a43073] dark:text-pink-400">
            {data.completed_count}/{data.total} hoàn thành
          </span>
        )}
      </div>
      <p className="text-xs text-slate-500 mb-4 dark:text-slate-400">Hoàn thành các thử thách học tập hàng ngày để tăng bậc xếp hạng nhanh chóng!</p>

      {loading && <p className="text-xs text-slate-400">Đang tải nhiệm vụ...</p>}
      {error && !data && <ErrorLine message={error} onRetry={reload} />}
      {data && (
        <div className="flex flex-col gap-2.5">
          {data.quests.map(quest => (
            <QuestRow key={quest.code} quest={quest} onGo={goTo[quest.code]} />
          ))}
          <p className="text-[11px] text-slate-500 mt-1 dark:text-slate-400">
            {data.bonus_granted
              ? `Đã nhận thưởng đủ nhiệm vụ: +${data.bonus_coins} xu.`
              : `Hoàn thành cả ${data.total} nhiệm vụ để nhận thêm ${data.bonus_coins} xu.`}
          </p>
        </div>
      )}
    </div>
  );
};

/** Biểu đồ XP từng ngày trong tuần (Thứ Hai đến Chủ Nhật) lấy từ máy chủ (F16.03). */
export const WeeklyActivityCard: React.FC = () => {
  const { data, loading, error, reload } = useApiResource(signal => getWeeklyActivity(signal), []);
  const max = Math.max(1, ...(data?.days.map(day => day.xp) ?? [0]));
  return (
    <div className="rounded-3xl bg-white p-6 shadow-soft border border-pink-100 dark:bg-slate-800 dark:border-pink-900/40">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100">Hoạt Động Tuần Của Bạn</h4>
        {data && <span className="text-xs text-slate-500 font-semibold dark:text-slate-400">Tổng: {data.total.toLocaleString('vi-VN')} XP</span>}
      </div>
      {loading && <p className="text-xs text-slate-400">Đang tải...</p>}
      {error && !data && <ErrorLine message={error} onRetry={reload} />}
      {data && (
        <div className="flex items-end justify-between h-28 pt-4 px-2 gap-2">
          {data.days.map(day => {
            const best = day.xp > 0 && day.xp === max;
            return (
              <div key={day.date} className="flex flex-col items-center gap-1 flex-1 h-full justify-end">
                <span className="text-[10px] text-slate-400">{day.xp > 0 ? day.xp : '-'}</span>
                <div
                  className={`w-full rounded-t-lg transition-all ${
                    day.xp === 0 ? 'bg-slate-100 border-2 border-dashed border-slate-300 dark:bg-[#1e293b] dark:border-slate-700' : best ? 'bg-[#f472b6] dark:bg-[#a43073]' : 'bg-slate-200 hover:bg-[#a43073] dark:bg-slate-700'
                  }`}
                  style={{ height: `${Math.max(8, Math.round((day.xp / max) * 70))}%` }}
                ></div>
                <span className={`text-[11px] font-bold ${best ? 'text-[#a43073] dark:text-pink-400' : 'text-slate-500 dark:text-slate-400'}`}>{weekdayOf(day.date)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/** Lối vào cửa hàng đổi thưởng và mini-game Phi Kiếm Trảm Tự (F17.07, F16.01). */
export const GamificationLinksCard: React.FC = () => (
  <div className="rounded-3xl bg-gradient-to-br from-[#ffd8e7]/70 via-white to-[#eff4ff] p-6 shadow-soft border border-pink-100 flex flex-col gap-3 dark:via-slate-800 dark:to-slate-800 dark:border-pink-900/40">
    <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Tiêu xu &amp; Luyện tập</h3>
    <Link
      to={REWARD_SHOP_PATH}
      className="flex items-center gap-3 p-3 rounded-2xl bg-white border border-pink-100 hover:border-[#a43073] transition-colors dark:bg-slate-800 dark:border-pink-900/40"
    >
      <span className="w-10 h-10 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center dark:bg-amber-900/30 dark:text-amber-300">
        <span className="material-symbols-outlined">storefront</span>
      </span>
      <span className="flex flex-col">
        <span className="text-xs font-bold text-slate-800 dark:text-slate-100">Cửa hàng đổi thưởng</span>
        <span className="text-[11px] text-slate-500 dark:text-slate-400">Đổi xu lấy ngày VIP, vé đọc truyện, khung avatar</span>
      </span>
    </Link>
    <Link
      to={BLADE_GAME_PATH}
      className="flex items-center gap-3 p-3 rounded-2xl bg-white border border-pink-100 hover:border-[#a43073] transition-colors dark:bg-slate-800 dark:border-pink-900/40"
    >
      <span className="w-10 h-10 rounded-xl bg-blue-100 text-[#0060ac] flex items-center justify-center dark:bg-blue-900/30 dark:text-blue-300">
        <span className="material-symbols-outlined">swords</span>
      </span>
      <span className="flex flex-col">
        <span className="text-xs font-bold text-slate-800 dark:text-slate-100">Phi Kiếm Trảm Tự</span>
        <span className="text-[11px] text-slate-500 dark:text-slate-400">Gõ pinyin chém chữ rơi theo HSK, nhận XP</span>
      </span>
    </Link>
  </div>
);
