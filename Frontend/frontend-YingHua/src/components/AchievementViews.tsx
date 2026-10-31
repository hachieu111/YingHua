import React, { useState } from 'react';
import { errorMessage } from '../api/client';
import { Achievement, equipAchievement, listAchievements } from '../api/gamification';
import { badgeStyle, tierLabel } from '../data/achievements';
import { useApiResource } from '../utils/useApiResource';
import { notifyRewardsChanged } from '../utils/useRewards';

/** Danh sách huy hiệu từ máy chủ kèm thao tác đeo/tháo; mỗi người tối đa một huy hiệu đang đeo (F16.11, F16.12). */
function useAchievements(showToast: (message: string) => void) {
  const list = useApiResource(signal => listAchievements(signal), []);
  const [busyCode, setBusyCode] = useState<string | null>(null);

  const toggleEquip = async (achievement: Achievement) => {
    setBusyCode(achievement.code);
    try {
      await equipAchievement(achievement.equipped ? null : achievement.code);
      showToast(achievement.equipped ? 'Đã tháo huy hiệu.' : `Đã đeo huy hiệu "${achievement.name}".`);
      notifyRewardsChanged();
      list.reload();
    } catch (err) {
      showToast(errorMessage(err));
      list.reload();
    } finally {
      setBusyCode(null);
    }
  };
  return { ...list, busyCode, toggleEquip };
}

const progressText = (a: Achievement): string => {
  if (a.next_threshold === null) return a.tier > 0 ? 'Đã đạt cấp cao nhất' : '';
  return `Tiến độ ${a.progress.toLocaleString('vi-VN')}/${a.next_threshold.toLocaleString('vi-VN')}`;
};

const progressPercent = (a: Achievement): number => {
  if (a.next_threshold === null) return 100;
  return Math.min(100, Math.round((a.progress / Math.max(1, a.next_threshold)) * 100));
};

interface ViewProps {
  showToast: (message: string) => void;
}

const StateLines: React.FC<{ loading: boolean; error: string | null; hasData: boolean; onRetry: () => void }> = ({ loading, error, hasData, onRetry }) => (
  <>
    {loading && <p className="py-8 text-center text-xs text-slate-400">Đang tải huy hiệu...</p>}
    {error && !hasData && (
      <p role="alert" className="py-6 text-center text-xs text-rose-600 dark:text-rose-400">
        {error}{' '}
        <button type="button" onClick={onRetry} className="font-bold underline">
          Thử lại
        </button>
      </p>
    )}
  </>
);

/** Tab "Huy hiệu & Thành tựu" của hồ sơ: ngưỡng và tiến độ lấy từ máy chủ. */
export const ProfileBadgesTab: React.FC<ViewProps> = ({ showToast }) => {
  const { data, loading, error, reload, busyCode, toggleEquip } = useAchievements(showToast);
  return (
    <div className="flex flex-col gap-3">
      <StateLines loading={loading} error={error} hasData={!!data} onRetry={reload} />
      {data && data.length === 0 && <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">Chưa có huy hiệu nào.</p>}
      {data && data.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.map(a => {
            const style = badgeStyle(a.style_key);
            const Icon = style.icon;
            const unlocked = a.tier > 0;
            return (
              <div key={a.code} className={`bg-white p-5 rounded-3xl shadow-soft border flex flex-col items-center text-center ${a.equipped ? 'border-[#a43073]' : 'border-pink-100 dark:border-pink-900/40'} ${unlocked ? '' : 'opacity-80'} dark:bg-slate-800`}>
                <div className={`w-16 h-16 rounded-full border flex items-center justify-center shadow-inner mb-3 ${unlocked ? style.color : 'bg-slate-100 text-slate-400 border-slate-200 dark:bg-[#1e293b] dark:border-slate-700'}`}>
                  <Icon className="w-8 h-8" strokeWidth={2} aria-hidden="true" />
                </div>
                <h4 className="font-bold text-sm text-slate-800 dark:text-slate-100">{a.name}</h4>
                <p className="text-xs text-slate-500 mt-1 dark:text-slate-400">{a.description}</p>
                <span className={`mt-3 px-3 py-0.5 rounded-full text-[10px] font-bold ${unlocked ? 'bg-[#a43073] text-white' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}`}>
                  {tierLabel(a.tier)}
                  {a.max_tier > 1 ? ` / ${a.max_tier}` : ''}
                </span>
                {progressText(a) && (
                  <div className="w-full mt-3">
                    <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden dark:bg-[#1e293b]">
                      <div className="h-full rounded-full bg-gradient-to-r from-pink-400 to-[#a43073]" style={{ width: `${progressPercent(a)}%` }}></div>
                    </div>
                    <span className="text-[10px] text-slate-500 mt-1 block dark:text-slate-400">{progressText(a)}</span>
                  </div>
                )}
                <button
                  type="button"
                  disabled={!unlocked || busyCode === a.code}
                  onClick={() => void toggleEquip(a)}
                  className={`mt-3 px-4 py-1.5 rounded-full text-[11px] font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    a.equipped ? 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-[#1e293b] dark:text-slate-100 dark:hover:bg-slate-700' : 'bg-[#f472b6] text-white hover:opacity-95 dark:bg-[#a43073]'
                  }`}
                >
                  {!unlocked ? 'Chưa mở khóa' : a.equipped ? 'Tháo huy hiệu' : 'Đeo huy hiệu'}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/** Chọn huy hiệu đeo trong hộp "Chỉnh sửa hồ sơ": bấm là lưu ngay lên máy chủ. */
export const BadgePicker: React.FC<ViewProps> = ({ showToast }) => {
  const { data, loading, error, reload, busyCode, toggleEquip } = useAchievements(showToast);
  return (
    <div className="flex flex-col gap-2.5">
      <StateLines loading={loading} error={error} hasData={!!data} onRetry={reload} />
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {data.map(a => {
            const style = badgeStyle(a.style_key);
            const Icon = style.icon;
            const unlocked = a.tier > 0;
            return (
              <button
                type="button"
                key={a.code}
                disabled={!unlocked || busyCode === a.code}
                onClick={() => void toggleEquip(a)}
                aria-pressed={a.equipped}
                className={`p-3 rounded-2xl text-left border transition-all flex items-start gap-3 disabled:cursor-not-allowed ${
                  a.equipped ? 'bg-pink-50/80 border-[#a43073] ring-2 ring-pink-200 dark:bg-pink-900/30' : unlocked ? 'bg-slate-50/70 border-slate-200 hover:bg-slate-100 dark:bg-[#1e293b] dark:border-slate-700 dark:hover:bg-slate-700' : 'bg-slate-50 border-slate-200 opacity-60 dark:bg-[#1e293b] dark:border-slate-700'
                }`}
              >
                <span className={`w-10 h-10 rounded-xl border shrink-0 flex items-center justify-center ${unlocked ? style.color : 'bg-slate-100 text-slate-400 border-slate-200 dark:bg-[#1e293b] dark:border-slate-700'}`}>
                  <Icon className="w-5 h-5" strokeWidth={2.2} aria-hidden="true" />
                </span>
                <span className="flex flex-col min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-slate-800 truncate dark:text-slate-100">{a.name}</span>
                    {a.equipped && <span className="w-4 h-4 rounded-full bg-[#a43073] text-white flex items-center justify-center text-[10px] shrink-0">✓</span>}
                  </span>
                  <span className="text-[10px] text-slate-500 mt-0.5 line-clamp-1 dark:text-slate-400">{unlocked ? a.description : `Chưa mở khóa · ${progressText(a)}`}</span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
