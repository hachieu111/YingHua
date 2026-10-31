import React, { useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { getSettings, updateSettings } from '../api/settings';
import { notifyRewardsChanged } from '../utils/useRewards';

/** Công tắc "Hiện tên trên bảng xếp hạng": tắt thì bạn vẫn có hạng nhưng hiển thị ẩn danh (F16.08). Trạng thái lấy từ máy chủ. */
export const LeaderboardPrivacyToggle: React.FC<{ showToast: (message: string) => void }> = ({ showToast }) => {
  const [visible, setVisible] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    getSettings(controller.signal)
      .then(settings => setVisible(settings.show_on_leaderboard))
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      });
    return () => controller.abort();
  }, [tick]);

  const toggle = async () => {
    if (visible === null || busy) return;
    setBusy(true);
    try {
      const saved = await updateSettings({ show_on_leaderboard: !visible });
      setVisible(saved.show_on_leaderboard);
      notifyRewardsChanged();
      showToast(saved.show_on_leaderboard ? 'Tên của bạn đã hiện trên bảng xếp hạng.' : 'Bạn đã ẩn danh trên bảng xếp hạng.');
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center justify-between gap-4 p-3.5 rounded-2xl bg-slate-50 border border-slate-200 dark:bg-[#1e293b] dark:border-slate-700">
      <div className="flex items-center gap-3 min-w-0">
        <span className="w-9 h-9 rounded-xl bg-blue-100 text-[#0060ac] flex items-center justify-center shrink-0 dark:bg-blue-900/30 dark:text-blue-300">
          <span className="material-symbols-outlined text-[18px]">leaderboard</span>
        </span>
        <span className="min-w-0">
          <span className="block text-xs font-bold text-slate-800 dark:text-slate-100">Hiện tên trên bảng xếp hạng</span>
          <span className="block text-[11px] text-slate-500 dark:text-slate-400">
            {error ? (
              <>
                {error}{' '}
                <button type="button" onClick={() => setTick(value => value + 1)} className="font-bold text-[#a43073] underline dark:text-pink-400">
                  Thử lại
                </button>
              </>
            ) : (
              'Tắt thì bạn vẫn có hạng nhưng người khác chỉ thấy “Người học ẩn danh”.'
            )}
          </span>
        </span>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={visible ?? false}
        aria-label={visible ? 'Ẩn tên khỏi bảng xếp hạng' : 'Hiện tên trên bảng xếp hạng'}
        disabled={visible === null || busy}
        onClick={() => void toggle()}
        className={`relative w-11 h-6 rounded-full transition-colors shrink-0 disabled:opacity-50 ${visible ? 'bg-[#0060ac]' : 'bg-slate-300'}`}
      >
        <span className={`absolute left-1 top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${visible ? 'translate-x-5' : 'translate-x-0'} dark:bg-slate-800`} />
      </button>
    </div>
  );
};
