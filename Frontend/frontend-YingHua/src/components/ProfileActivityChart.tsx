import React from 'react';
import { ActivityReport, LearningOverview } from '../api/stats';

interface ProfileActivityChartProps {
  activity: ActivityReport | null;
  overview: LearningOverview | null;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}

const WEEKDAY = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
const BAR_AREA_PX = 96;

const toDate = (iso: string): Date => new Date(`${iso}T00:00:00`);

const dayLabel = (iso: string): string => {
  const date = toDate(iso);
  return Number.isNaN(date.getTime()) ? '' : `${WEEKDAY[date.getDay()]} ${date.getDate()}/${date.getMonth() + 1}`;
};

/** Biểu đồ cột 14 ngày gần nhất (F12.01): lượt ôn và trang đã đọc mỗi ngày, tự vẽ bằng div. */
export const ProfileActivityChart: React.FC<ProfileActivityChartProps> = ({ activity, overview, loading, error, onRetry }) => {
  const points = activity?.points ?? [];
  const max = Math.max(1, ...points.map(p => Math.max(p.reviews_count, p.pages_read)));
  const empty = points.every(p => p.reviews_count === 0 && p.pages_read === 0);
  const retention = overview?.retention_rate;

  return (
    <div className="p-5 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 flex flex-col gap-3 transition-colors duration-300">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-800 dark:text-white">Hoạt động 14 ngày gần nhất</h3>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Tỉ lệ nhớ:{' '}
            <span className="font-bold text-slate-700 dark:text-slate-200">
              {retention === null || retention === undefined ? 'Chưa có dữ liệu' : `${Math.round(retention * 100)}%`}
            </span>
            {overview ? ` · Ôn hôm nay: ${overview.reviews_today} lượt` : ''}
          </p>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-[#a43073] dark:bg-pink-500"></span>Lượt ôn</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-[#0060ac] dark:bg-blue-400"></span>Trang đọc</span>
        </div>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-2xl bg-rose-50 dark:bg-rose-900/20 p-3 text-xs text-rose-700 dark:text-rose-300">
          <span>Không tải được thống kê hoạt động.</span>
          <button onClick={onRetry} className="px-3 py-1 rounded-full bg-[#a43073] text-white font-bold">Thử lại</button>
        </div>
      )}
      {!error && loading && points.length === 0 && <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">Đang tải...</div>}
      {!error && !loading && points.length > 0 && empty && (
        <div className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">Chưa có hoạt động nào trong 14 ngày qua. Hãy đọc một trang hoặc ôn vài thẻ nhé!</div>
      )}
      {!error && points.length > 0 && !empty && (
        <div className="flex items-end gap-1.5" role="img" aria-label="Biểu đồ lượt ôn và trang đọc 14 ngày gần nhất">
          {points.map(point => (
            <div key={point.start} className="flex-1 min-w-0 flex flex-col items-center gap-1" title={`${dayLabel(point.start)}: ${point.reviews_count} lượt ôn, ${point.pages_read} trang`}>
              <div className="w-full flex items-end justify-center gap-0.5" style={{ height: BAR_AREA_PX }}>
                <div className="w-1/2 max-w-3 rounded-t bg-[#a43073] dark:bg-pink-500" style={{ height: `${(point.reviews_count / max) * 100}%` }}></div>
                <div className="w-1/2 max-w-3 rounded-t bg-[#0060ac] dark:bg-blue-400" style={{ height: `${(point.pages_read / max) * 100}%` }}></div>
              </div>
              <span className="text-[9px] text-slate-400 dark:text-slate-500 whitespace-nowrap">{toDate(point.start).getDate()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
