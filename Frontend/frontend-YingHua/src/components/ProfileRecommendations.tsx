import React, { useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { SeriesRecommendations, listSeriesRecommendations } from '../api/suggestions';
import { AuthImage } from './AuthImage';

interface ProfileRecommendationsProps {
  onOpenSeries: (seriesId: number) => void;
  onBrowse: () => void;
  onOpenLearningSettings?: () => void;
}

const RECOMMEND_LIMIT = 3;

/** Khối "Gợi ý tiếp theo" của hồ sơ: truyện hợp trình độ HSK đã khai báo (F10.04). */
export const ProfileRecommendations: React.FC<ProfileRecommendationsProps> = ({ onOpenSeries, onBrowse, onOpenLearningSettings }) => {
  const [data, setData] = useState<SeriesRecommendations | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setError(null);
    const controller = new AbortController();
    listSeriesRecommendations(RECOMMEND_LIMIT, controller.signal)
      .then(setData)
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      });
    return () => controller.abort();
  }, [tick]);

  const title = data?.hsk_level != null ? `Gợi ý tiếp theo (HSK ${data.hsk_level})` : 'Gợi ý tiếp theo';

  return (
    <div className="flex flex-col gap-4 rounded-3xl border border-pink-100 dark:border-slate-800 bg-white dark:bg-[#0f172a] p-6 shadow-soft dark:shadow-none transition-colors duration-300">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-800 dark:text-white">
          <span className="material-symbols-outlined text-[20px] text-[#0060ac] dark:text-blue-300">recommend</span>
          <span>{title}</span>
        </h3>
        <button onClick={onBrowse} className="text-xs font-bold text-[#a43073] dark:text-pink-400 hover:underline">
          Xem tất cả
        </button>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-2 rounded-xl bg-rose-50 dark:bg-rose-900/20 px-3 py-2 text-xs text-rose-700 dark:text-rose-300" role="alert">
          <span>{error}</span>
          <button onClick={() => setTick(value => value + 1)} className="font-bold text-[#a43073] dark:text-pink-400 hover:underline">Thử lại</button>
        </div>
      )}

      {!error && data === null && (
        <div className="flex flex-col gap-3" aria-busy="true">
          {[0, 1].map(key => (
            <div key={key} className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800"></div>
          ))}
        </div>
      )}

      {data?.needs_level && (
        <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 px-3 py-2 text-[11px] leading-relaxed text-blue-900 dark:text-blue-300">
          Hãy khai báo trình độ HSK để nhận gợi ý đúng sức bạn.{' '}
          {onOpenLearningSettings && (
            <button onClick={onOpenLearningSettings} className="font-bold underline">Khai báo trình độ</button>
          )}
        </div>
      )}

      {data && data.items.length === 0 && (
        <p className="py-2 text-center text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          Chưa có truyện nào để gợi ý lúc này. Bạn có thể tự khám phá ở mục Khám phá truyện.
        </p>
      )}

      {data?.items.map(item => (
        <button key={item.id} onClick={() => onOpenSeries(item.id)} className="group flex items-center gap-3 text-left">
          <AuthImage src={item.cover_url} alt={item.title_vi} className="h-[4.5rem] w-14 shrink-0 rounded-xl object-cover" />
          <div className="flex min-w-0 flex-col">
            {item.est_hsk_level !== null && (
              <span className="w-fit rounded-full bg-pink-100 dark:bg-pink-900/30 px-2 py-0.5 text-[10px] font-bold text-[#a43073] dark:text-pink-400">HSK {item.est_hsk_level}</span>
            )}
            <h4 className="mt-0.5 text-xs font-bold text-slate-800 dark:text-white transition-colors group-hover:text-[#a43073] dark:group-hover:text-pink-400">{item.title_vi}</h4>
            {item.title_zh && <span className="font-['Noto_Serif_SC'] text-[10px] text-slate-400 dark:text-slate-500">{item.title_zh}</span>}
            <span className="mt-0.5 text-[10px] font-medium text-[#0060ac] dark:text-blue-300">{item.reason}</span>
          </div>
        </button>
      ))}
    </div>
  );
};
