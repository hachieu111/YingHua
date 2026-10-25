import React, { useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { ChapterCoverage, getChapterCoverage } from '../api/suggestions';

interface ChapterCoverageBarProps {
  chapterId: number | null;
  isLoggedIn: boolean;
  /** Đổi giá trị này để tải lại (vd. sau khi lưu thêm từ vào Sổ tay). */
  refreshKey?: number;
  /** Gọn: dùng trong thẻ danh sách; không gọn: thẻ riêng trong trình đọc. */
  compact?: boolean;
  onOpenLearningSettings?: () => void;
}

/** Thanh "Đã nắm X/Y từ HSK n" của một chương (F10.05). */
export const ChapterCoverageBar: React.FC<ChapterCoverageBarProps> = ({
  chapterId,
  isLoggedIn,
  refreshKey = 0,
  compact = false,
  onOpenLearningSettings
}) => {
  const [data, setData] = useState<ChapterCoverage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setError(null);
    if (!isLoggedIn || chapterId === null) {
      setData(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    getChapterCoverage(chapterId, controller.signal)
      .then(setData)
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [chapterId, isLoggedIn, refreshKey]);

  if (!isLoggedIn || chapterId === null) return null;

  const wrapperClass = compact ? 'mt-2' : 'rounded-3xl border border-emerald-100 bg-white p-5 shadow-soft';
  const title = (
    <div className="mb-1.5 flex items-center gap-1.5">
      <span className="material-symbols-outlined text-[16px] text-emerald-600">donut_small</span>
      <span className="text-[11px] font-bold uppercase tracking-wide text-emerald-700">Độ phủ từ vựng</span>
    </div>
  );

  if (loading && !data) {
    return (
      <div className={wrapperClass} aria-busy="true">
        {!compact && title}
        <div className="h-2 w-full animate-pulse rounded-full bg-slate-100"></div>
      </div>
    );
  }
  if (error) return <div className={`${wrapperClass} text-[11px] text-rose-700`}>{error}</div>;
  if (!data || data.status === 'empty') {
    return data && !compact ? (
      <div className={wrapperClass}>
        {title}
        <p className="text-xs text-slate-500">Chương này chưa có từ để tính độ phủ.</p>
      </div>
    ) : null;
  }

  const levelText = data.hsk_level !== null ? `HSK ${data.hsk_level}` : 'HSK';
  const percent = Math.max(0, Math.min(100, data.percent));
  return (
    <div className={wrapperClass}>
      {!compact && title}
      <div className="flex items-center justify-between gap-2 text-[11px] font-semibold text-slate-600">
        <span>
          Đã nắm {data.known_terms}/{data.total_terms} từ {levelText}
        </span>
        <span className="font-bold text-emerald-700">{percent}%</span>
      </div>
      <div
        className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Độ phủ từ vựng của chương"
      >
        <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all" style={{ width: `${percent}%` }}></div>
      </div>
      {data.status === 'processing' && <p className="mt-1 text-[10px] text-amber-700">Chương đang xử lý, số liệu là tạm tính.</p>}
      {data.needs_level && (
        <p className="mt-1 text-[10px] text-slate-500">
          Chưa khai báo trình độ nên tính trên mọi từ có cấp HSK.{' '}
          {onOpenLearningSettings && (
            <button onClick={onOpenLearningSettings} className="font-bold text-[#a43073] underline">
              Khai báo trình độ
            </button>
          )}
        </p>
      )}
    </div>
  );
};
