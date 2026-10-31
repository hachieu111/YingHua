import React, { useCallback, useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { hskLabel } from '../api/dictionary';
import { DismissedItem, listDismissed, restoreSuggestion } from '../api/suggestions';
import { formatDateTime } from '../utils/format';

interface DismissedSuggestionsProps {
  showToast: (message: string) => void;
}

const PAGE_SIZE = 10;

/** Mục "Đã bỏ qua" (F10.03): các từ gợi ý người học đã loại, có thể khôi phục. */
export const DismissedSuggestions: React.FC<DismissedSuggestionsProps> = ({ showToast }) => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<DismissedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [busyTerm, setBusyTerm] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    listDismissed(page, PAGE_SIZE, controller.signal)
      .then(data => {
        setItems(data.items);
        setTotal(data.total);
        // Khôi phục hết mục ở trang cuối: lùi về trang trước.
        if (data.items.length === 0 && page > 1) setPage(page - 1);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [open, page, tick]);

  const handleRestore = useCallback(
    async (term: string) => {
      setBusyTerm(term);
      try {
        await restoreSuggestion(term);
        showToast(`Đã khôi phục “${term}” vào danh sách gợi ý`);
        setTick(value => value + 1);
      } catch (err) {
        showToast(errorMessage(err));
      } finally {
        setBusyTerm(null);
      }
    },
    [showToast]
  );

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="rounded-3xl border border-pink-100 bg-white p-5 shadow-soft sm:p-6 dark:border-slate-700 dark:bg-[#0f172a] dark:shadow-none transition-colors duration-300">
      <button onClick={() => setOpen(value => !value)} className="flex w-full items-center justify-between gap-3 text-left" aria-expanded={open}>
        <div>
          <h3 className="font-['Plus_Jakarta_Sans'] text-base font-bold text-slate-800 dark:text-white">Từ gợi ý đã bỏ qua</h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">Những từ bạn đã chọn “Bỏ qua” khi đọc truyện; khôi phục để chúng được gợi ý lại.</span>
        </div>
        <span className="material-symbols-outlined text-slate-400 dark:text-slate-500">{open ? 'expand_less' : 'expand_more'}</span>
      </button>

      {open && (
        <div className="mt-4 flex flex-col gap-2">
          {loading && items.length === 0 && <p className="py-3 text-center text-xs text-slate-500 dark:text-slate-400">Đang tải...</p>}
          {error && (
            <div className="flex items-center justify-between gap-2 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
              <span>{error}</span>
              <button onClick={() => setTick(value => value + 1)} className="font-bold text-[#a43073] dark:text-pink-400 hover:underline">Thử lại</button>
            </div>
          )}
          {!loading && !error && items.length === 0 && <p className="py-3 text-center text-xs text-slate-500 dark:text-slate-400">Bạn chưa bỏ qua từ gợi ý nào.</p>}
          {items.map(item => (
            <div key={item.term} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-800">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-['Noto_Serif_SC'] text-base font-bold text-slate-800 dark:text-slate-100">{item.term}</span>
                  {item.pinyin && <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">{item.pinyin}</span>}
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-900 dark:bg-blue-900/30 dark:text-blue-300">{hskLabel(item.hsk_level)}</span>
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-300">{item.meaning_vi ?? 'Chưa có nghĩa trong từ điển'}</div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500">Bỏ qua lúc {formatDateTime(item.dismissed_at)}</div>
              </div>
              <button
                onClick={() => void handleRestore(item.term)}
                disabled={busyTerm === item.term}
                className="shrink-0 rounded-full bg-pink-50 px-4 py-1.5 text-xs font-bold text-[#a43073] hover:bg-pink-100 dark:bg-pink-900/20 dark:text-pink-400 dark:hover:bg-pink-900/30 disabled:opacity-60"
              >
                {busyTerm === item.term ? 'Đang khôi phục...' : 'Khôi phục'}
              </button>
            </div>
          ))}
          {pageCount > 1 && (
            <div className="flex items-center justify-center gap-3 pt-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded-full bg-slate-100 px-4 py-1.5 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 disabled:opacity-40">Trước</button>
              <span>{page} / {pageCount}</span>
              <button disabled={page >= pageCount} onClick={() => setPage(page + 1)} className="rounded-full bg-slate-100 px-4 py-1.5 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 disabled:opacity-40">Sau</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
