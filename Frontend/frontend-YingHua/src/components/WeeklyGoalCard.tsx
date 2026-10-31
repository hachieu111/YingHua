import React from 'react';
import { getWeeklyGoal } from '../api/gamification';
import { useApiResource } from '../utils/useApiResource';

interface WeeklyGoalCardProps {
  /** Mở cài đặt học tập để đổi số trang mục tiêu mỗi tuần. */
  onOpenLearningSettings?: () => void;
}

/** Mục tiêu đọc trong tuần và phần thưởng khi hoàn thành; tiến độ lấy từ máy chủ (F16.05). */
export const WeeklyGoalCard: React.FC<WeeklyGoalCardProps> = ({ onOpenLearningSettings }) => {
  const { data, loading, error, reload } = useApiResource(signal => getWeeklyGoal(signal), []);
  return (
    <div className="p-6 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col gap-3 dark:bg-slate-800 dark:border-pink-900/40">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-800 flex items-center gap-1.5 dark:text-slate-100">
          <span className="material-symbols-outlined text-[#a43073] text-[20px] dark:text-pink-400">flag</span>
          <span>Mục tiêu tuần này</span>
        </h3>
        {data && <span className="text-xs font-bold text-[#0060ac] dark:text-blue-300">{data.percent}%</span>}
      </div>

      {loading && <p className="text-xs text-slate-400">Đang tải mục tiêu...</p>}
      {error && !data && (
        <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
          {error}{' '}
          <button type="button" onClick={reload} className="font-bold underline">
            Thử lại
          </button>
        </p>
      )}

      {data && (
        <>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Đọc {data.goal} trang manhua trong tuần để duy trì đà ghi nhớ từ vựng tự nhiên.
            {data.rewarded_goal > data.goal && ` Phần thưởng tính từ mức tối thiểu ${data.rewarded_goal} trang.`}
          </p>
          <div className="flex flex-col gap-1.5 mt-1">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-slate-800 dark:text-slate-100">
                {data.pages_read} / {data.goal} trang
              </span>
              <span className="text-slate-400">{data.pages_left > 0 ? `Còn ${data.pages_left} trang nữa` : 'Đã đạt mục tiêu'}</span>
            </div>
            <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden dark:bg-[#1e293b]">
              <div
                className="bg-gradient-to-r from-pink-400 to-[#a43073] h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, data.percent))}%` }}
              ></div>
            </div>
          </div>
          <div className="p-3 rounded-2xl bg-[#eff4ff] flex items-center gap-3 mt-1 dark:bg-[#1e293b]">
            <span className="material-symbols-outlined text-[#a43073] text-[24px] dark:text-pink-400">emoji_events</span>
            <div className="flex flex-col">
              <span className="text-xs font-bold text-slate-800 dark:text-slate-100">{data.rewarded_at ? 'Đã nhận phần thưởng tuần này' : 'Phần thưởng khi hoàn thành'}</span>
              <span className="text-[11px] text-slate-500 dark:text-slate-400">
                +{data.reward_xp} XP và khung avatar tặng {data.reward_frame_days} ngày
              </span>
            </div>
          </div>
          {onOpenLearningSettings && (
            <button type="button" onClick={onOpenLearningSettings} className="self-start text-[11px] font-bold text-[#a43073] hover:underline dark:text-pink-400">
              Đổi số trang mục tiêu
            </button>
          )}
        </>
      )}
    </div>
  );
};
