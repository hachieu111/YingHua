import React, { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router';
import { ApiSeries } from '../api/library';
import { TAB_PATHS } from '../routes';
import { ReaderTarget } from '../types';
import { ReaderSources, useOpenSeries } from '../utils/useReaderSources';
import { AuthImage } from './AuthImage';

interface ReaderSourcePickerProps {
  sources: ReaderSources;
  /** Truyện đang đọc (để đánh dấu); null khi đang đọc ảnh tải lên. */
  currentSeriesId: number | null;
  /** Đang đọc trong bộ ảnh tải lên. */
  inQuickSet: boolean;
  onOpenReader: (target: ReaderTarget) => void;
}

/** Nút "Đổi nguồn đọc" trên thanh đầu trang: chọn ảnh tải lên hoặc một truyện riêng tư của mình. */
export const ReaderSourcePicker: React.FC<ReaderSourcePickerProps> = ({ sources, currentSeriesId, inQuickSet, onOpenReader }) => {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const panelId = useId();
  const { openSeries, busyId, message } = useOpenSeries(onOpenReader);
  const { series, quick, loading, error, reload } = sources;

  useEffect(() => {
    if (!open) return;
    panelRef.current?.focus();
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const toggle = () => {
    if (!open) reload();
    setOpen(value => !value);
  };

  const openQuick = () => {
    const newest = quick?.[quick.length - 1];
    if (!newest) return;
    setOpen(false);
    onOpenReader({ chapterId: null, pageId: newest.id });
  };

  const pickSeries = async (item: ApiSeries) => {
    if (await openSeries(item)) setOpen(false);
  };

  const noData = series === null && quick === null;

  return (
    <div ref={rootRef} data-tour="reader-source" className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        className="inline-flex items-center gap-1 rounded-full border border-pink-200 bg-white px-2.5 py-1 text-xs font-semibold text-[#a43073] transition-colors hover:bg-pink-50 dark:border-pink-900/40 dark:bg-[#1e293b] dark:text-pink-400 dark:hover:bg-pink-900/20"
      >
        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">auto_stories</span>
        Đổi nguồn đọc
        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">{open ? 'expand_less' : 'expand_more'}</span>
      </button>

      {open && (
        <div
          id={panelId}
          ref={panelRef}
          role="dialog"
          aria-label="Chọn nguồn đọc"
          tabIndex={-1}
          className="absolute left-0 top-full z-40 mt-2 max-h-[70vh] w-80 max-w-[90vw] overflow-y-auto rounded-2xl border border-pink-100 bg-white p-3 text-left shadow-xl outline-none dark:border-slate-700 dark:bg-[#0f172a] dark:shadow-none"
        >
          {noData && loading && (
            <p className="flex items-center gap-2 px-1 py-3 text-xs text-slate-500 dark:text-slate-400">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-pink-300 border-t-transparent dark:border-pink-900/40"></span>
              Đang tải danh sách...
            </p>
          )}
          {error && <p role="alert" className="mb-2 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</p>}
          {message && <p role="alert" className="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">{message}</p>}

          {quick !== null && quick.length > 0 && (
            <button
              type="button"
              onClick={openQuick}
              aria-current={inQuickSet ? 'true' : undefined}
              className={`mb-2 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${inQuickSet ? 'bg-pink-50 ring-1 ring-pink-200 dark:bg-pink-900/20 dark:ring-pink-900/50' : 'hover:bg-pink-50 dark:hover:bg-slate-700'}`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-pink-100 text-[#a43073] dark:bg-pink-900/20 dark:text-pink-400">
                <span className="material-symbols-outlined text-[22px]" aria-hidden="true">add_photo_alternate</span>
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-bold text-slate-800 dark:text-slate-100">Ảnh tải lên của tôi</span>
                <span className="block text-[11px] text-slate-500 dark:text-slate-400">{quick.length} ảnh</span>
              </span>
              {inQuickSet && <span className="material-symbols-outlined text-[18px] text-[#a43073] dark:text-pink-400" aria-label="Đang đọc">check_circle</span>}
            </button>
          )}

          <div className="px-1 pb-1 pt-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Truyện riêng tư của tôi</div>
          {series !== null && series.length === 0 && (
            <p className="px-1 py-2 text-xs text-slate-500 dark:text-slate-400">Bạn chưa có truyện riêng tư nào. Tạo truyện trong Thư viện để đọc tại đây.</p>
          )}
          <ul className="space-y-1">
            {(series ?? []).map(item => {
              const empty = item.chapter_count === 0;
              const current = item.id === currentSeriesId;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    disabled={empty || busyId !== null}
                    onClick={() => void pickSeries(item)}
                    aria-current={current ? 'true' : undefined}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition-colors ${current ? 'bg-pink-50 ring-1 ring-pink-200 dark:bg-pink-900/20 dark:ring-pink-900/50' : 'hover:bg-pink-50 dark:hover:bg-slate-700'} ${empty ? 'cursor-not-allowed opacity-50' : ''}`}
                  >
                    <AuthImage src={item.cover_url} alt="" className="h-12 w-9 shrink-0 rounded-md object-cover" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-bold text-slate-800 dark:text-slate-100">{item.title_vi}</span>
                      <span className="block text-[11px] text-slate-500 dark:text-slate-400">{empty ? 'Chưa có chương' : `${item.chapter_count} chương`}</span>
                    </span>
                    {busyId === item.id && <span className="h-4 w-4 animate-spin rounded-full border-2 border-pink-300 border-t-transparent dark:border-pink-900/40"></span>}
                    {current && <span className="material-symbols-outlined text-[18px] text-[#a43073] dark:text-pink-400" aria-label="Đang đọc">check_circle</span>}
                  </button>
                </li>
              );
            })}
          </ul>

          <Link
            to={TAB_PATHS.library}
            onClick={() => setOpen(false)}
            className="mt-3 flex items-center justify-center gap-1 rounded-xl border border-pink-100 px-3 py-2 text-xs font-bold text-[#a43073] hover:bg-pink-50 dark:border-pink-900/40 dark:text-pink-400 dark:hover:bg-pink-900/20"
          >
            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">explore</span>
            Khám phá thêm ở Thư viện
          </Link>
        </div>
      )}
    </div>
  );
};
