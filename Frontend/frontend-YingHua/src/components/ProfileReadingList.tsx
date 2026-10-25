import React, { useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { ContinueItem, listContinueReading } from '../api/library';
import { ReaderTarget } from '../types';
import { formatChapterNumber } from '../utils/format';
import { AuthImage } from './AuthImage';
import { ChapterCoverageBar } from './ChapterCoverageBar';

interface ProfileReadingListProps {
  onOpenReader: (target: ReaderTarget) => void;
  onBrowse: () => void;
  onOpenLearningSettings?: () => void;
}

const CONTINUE_LIMIT = 10;

/** Tab "Đang đọc" của hồ sơ: các truyện đọc dở (tiến độ thật) kèm độ phủ từ vựng của chương (F10.05). */
export const ProfileReadingList: React.FC<ProfileReadingListProps> = ({ onOpenReader, onBrowse, onOpenLearningSettings }) => {
  const [items, setItems] = useState<ContinueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setError(null);
    let cancelled = false;
    listContinueReading(CONTINUE_LIMIT)
      .then(result => {
        if (!cancelled) setItems(result);
      })
      .catch(err => {
        if (!cancelled && !isAbortedError(err)) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [tick]);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl border border-pink-100 bg-white p-8 text-center" role="alert">
        <p className="text-sm text-rose-700">{error}</p>
        <button onClick={() => setTick(value => value + 1)} className="rounded-full border border-pink-200 bg-white px-4 py-1.5 text-xs font-bold text-[#a43073] hover:bg-pink-50">
          Thử lại
        </button>
      </div>
    );
  }

  if (items === null) {
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        {[0, 1].map(key => (
          <div key={key} className="h-40 animate-pulse rounded-3xl border border-pink-100 bg-white"></div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl border border-pink-100 bg-white p-10 text-center">
        <span className="material-symbols-outlined text-[36px] text-pink-300">menu_book</span>
        <p className="text-sm font-bold text-slate-700">Bạn chưa đọc dở truyện nào</p>
        <button onClick={onBrowse} className="rounded-full bg-[#a43073] px-5 py-2 text-xs font-bold text-white hover:opacity-90">
          Khám phá truyện
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {items.map(item => {
        const percent = item.total_pages > 0 ? Math.min(100, Math.round((item.page_no / item.total_pages) * 100)) : 0;
        const chapterName = item.chapter_title ? `: ${item.chapter_title}` : '';
        return (
          <div key={`${item.series_id}-${item.chapter_id}`} className="flex flex-col gap-4 rounded-3xl border border-pink-100 bg-white p-4 shadow-soft transition-shadow hover:shadow-md sm:flex-row">
            <div className="relative h-36 w-full shrink-0 overflow-hidden rounded-2xl bg-slate-100 sm:w-28">
              <AuthImage src={item.cover_url} alt={item.series_title} className="h-full w-full object-cover" />
            </div>
            <div className="flex min-w-0 flex-1 flex-col justify-between">
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-base font-bold text-slate-800">{item.series_title}</h3>
                  <span className="shrink-0 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-900">Tiến độ {percent}%</span>
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-slate-600">
                  Đang đọc đến <strong>Chương {formatChapterNumber(item.chapter_number)}{chapterName}</strong> (Trang {item.page_no}/{item.total_pages}).
                </p>
                <ChapterCoverageBar chapterId={item.chapter_id} isLoggedIn compact onOpenLearningSettings={onOpenLearningSettings} />
              </div>
              <div className="mt-3 flex flex-col gap-2">
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-gradient-to-r from-blue-400 to-[#a43073]" style={{ width: `${percent}%` }}></div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Trang {item.page_no} trên {item.total_pages}</span>
                  <button
                    onClick={() => onOpenReader({ chapterId: item.chapter_id, pageNo: item.page_no, pageId: item.page_id ?? undefined })}
                    className="flex items-center gap-1 rounded-full bg-[#a43073] px-4 py-1.5 text-xs font-bold text-white transition-all hover:opacity-90"
                  >
                    <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                    <span>Đọc tiếp</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
