import React, { useEffect, useState } from 'react';
import { ContinueItem, listContinueReading } from '../api/library';
import { ReaderTarget } from '../types';
import { formatChapterNumber } from '../utils/format';
import { ReaderSources, useOpenSeries } from '../utils/useReaderSources';
import { AuthImage } from './AuthImage';

/** Số ảnh tải lên gần nhất hiện ở màn chưa chọn truyện. */
const RECENT_UPLOADS_SHOWN = 12;

interface ReaderEmptyStateProps {
  isLoggedIn: boolean;
  sources: ReaderSources;
  onOpenReader: (target: ReaderTarget) => void;
  onBrowse: () => void;
  onOpenUpload: () => void;
}

/** Màn "Chưa chọn truyện để đọc": đọc dở gần đây, truyện riêng tư và ảnh tải lên của người dùng. */
export const ReaderEmptyState: React.FC<ReaderEmptyStateProps> = ({ isLoggedIn, sources, onOpenReader, onBrowse, onOpenUpload }) => {
  const [continueItems, setContinueItems] = useState<ContinueItem[]>([]);
  const { openSeries, busyId, message } = useOpenSeries(onOpenReader);
  const { series, quick, loading, error } = sources;

  useEffect(() => {
    if (!isLoggedIn) return;
    let cancelled = false;
    listContinueReading(5)
      .then(items => {
        if (!cancelled) setContinueItems(items);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [isLoggedIn]);

  const recentUploads = quick ? [...quick].reverse().slice(0, RECENT_UPLOADS_SHOWN) : [];

  return (
    <div className="mx-auto flex w-full max-w-[700px] flex-col items-center gap-5 px-4 py-16 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-3xl border border-pink-200 bg-pink-100 text-[#a43073] shadow-md dark:border-pink-900/40 dark:bg-pink-900/20 dark:text-pink-400 dark:shadow-none">
        <span className="material-symbols-outlined text-[42px]">menu_book</span>
      </div>
      <h2 className="font-['Plus_Jakarta_Sans'] text-2xl font-extrabold text-slate-800 dark:text-white">Chưa chọn truyện để đọc</h2>
      <p className="max-w-md text-sm text-slate-600 dark:text-slate-300">Chọn một truyện ở Trang Chủ hoặc Thư viện, hoặc tải lên ảnh trang truyện của riêng bạn để bắt đầu.</p>

      {continueItems.length > 0 && (
        <div className="flex w-full flex-col gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Đọc dở gần đây</span>
          {continueItems.map(item => (
            <button
              key={item.chapter_id}
              onClick={() => onOpenReader({ chapterId: item.chapter_id, pageNo: item.page_no, pageId: item.page_id ?? undefined })}
              className="flex items-center justify-between gap-3 rounded-2xl border border-pink-100 bg-white px-4 py-3 text-left transition-colors hover:border-pink-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-pink-900/60"
            >
              <span className="truncate text-sm font-bold text-slate-800 dark:text-slate-100">
                {item.series_title} · Chương {formatChapterNumber(item.chapter_number)}
              </span>
              <span className="shrink-0 text-xs font-bold text-[#a43073] dark:text-pink-400">Trang {item.page_no}/{item.total_pages}</span>
            </button>
          ))}
        </div>
      )}

      {isLoggedIn && (
        <>
          {error && <p role="alert" className="w-full rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</p>}
          {message && <p role="alert" className="w-full rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">{message}</p>}
          {series === null && quick === null && loading && (
            <p className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-pink-300 border-t-transparent dark:border-pink-900/40"></span>
              Đang tải truyện và ảnh của bạn...
            </p>
          )}

          {series !== null && series.length > 0 && (
            <section className="w-full text-left" aria-label="Truyện riêng tư của tôi">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Truyện riêng tư của tôi</span>
              <ul className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
                {series.map(item => {
                  const empty = item.chapter_count === 0;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        disabled={empty || busyId !== null}
                        onClick={() => void openSeries(item)}
                        className={`group w-full overflow-hidden rounded-2xl border border-pink-100 bg-white text-left transition-all hover:border-pink-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-800 dark:hover:border-pink-900/60 dark:hover:shadow-none ${empty ? 'cursor-not-allowed opacity-50' : ''}`}
                      >
                        <AuthImage src={item.cover_url} alt="" className="h-36 w-full object-cover" />
                        <span className="block p-2.5">
                          <span className="block truncate text-sm font-bold text-slate-800 dark:text-slate-100">{item.title_vi}</span>
                          <span className="block text-[11px] text-slate-500 dark:text-slate-400">
                            {busyId === item.id ? 'Đang mở...' : empty ? 'Chưa có chương' : `${item.chapter_count} chương`}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {recentUploads.length > 0 && (
            <section className="w-full text-left" aria-label="Ảnh tải lên của tôi">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Ảnh tải lên của tôi{quick && quick.length > recentUploads.length ? ` · ${recentUploads.length}/${quick.length} ảnh gần nhất` : ''}
              </span>
              <ul className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
                {recentUploads.map(page => (
                  <li key={page.id}>
                    <button
                      type="button"
                      onClick={() => onOpenReader({ chapterId: null, pageId: page.id })}
                      aria-label={`Mở ảnh tải lên số ${page.id}`}
                      className="block w-full overflow-hidden rounded-xl border-2 border-transparent bg-white shadow-xs transition-all hover:border-pink-300 dark:bg-slate-800 dark:shadow-none dark:hover:border-pink-900/60"
                    >
                      <AuthImage src={page.original_url} alt="" className="h-24 w-full object-cover object-top" />
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button onClick={onBrowse} className="rounded-full bg-[#a43073] px-6 py-3 text-sm font-bold text-white shadow-md transition-all hover:bg-[#85145a]">
          Khám phá truyện
        </button>
        <button onClick={onOpenUpload} className="rounded-full border border-pink-200 bg-white px-6 py-3 text-sm font-bold text-[#a43073] transition-all hover:bg-pink-50 dark:border-pink-900/40 dark:bg-[#1e293b] dark:text-pink-400 dark:hover:bg-pink-900/20">
          Tải ảnh dịch
        </button>
      </div>
    </div>
  );
};
