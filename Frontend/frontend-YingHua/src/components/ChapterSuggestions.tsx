import React, { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { hskLabel } from '../api/dictionary';
import {
  SuggestionItem,
  SuggestionList,
  acceptSuggestion,
  dismissSuggestion,
  isSuggestionAlreadySaved,
  listSuggestions,
  restoreSuggestion
} from '../api/suggestions';
import { saveResultMessage } from '../api/vocab';
import { speakChinese } from '../utils/speech';

interface ChapterSuggestionsProps {
  chapterId: number | null;
  isLoggedIn: boolean;
  onRequireLogin: (message: string) => void;
  /** Nhảy tới trang có từ gợi ý trong trình đọc. */
  onGoToPage: (pageNo: number) => void;
  onOpenLearningSettings?: () => void;
}

const SUGGESTION_LIMIT = 20;
const UNDO_VISIBLE_MS = 6000;

interface UndoState {
  item: SuggestionItem;
  index: number;
}

export const ChapterSuggestions: React.FC<ChapterSuggestionsProps> = ({
  chapterId,
  isLoggedIn,
  onRequireLogin,
  onGoToPage,
  onOpenLearningSettings
}) => {
  const [data, setData] = useState<SuggestionList | null>(null);
  const [items, setItems] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [busyTerms, setBusyTerms] = useState<Set<string>>(() => new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const [undo, setUndo] = useState<UndoState | null>(null);
  const undoTimer = useRef<number | null>(null);

  useEffect(() => {
    setData(null);
    setItems([]);
    setError(null);
    setUndo(null);
    setNotice(null);
    if (!isLoggedIn || chapterId === null) return;
    const controller = new AbortController();
    setLoading(true);
    listSuggestions(chapterId, SUGGESTION_LIMIT, controller.signal)
      .then(result => {
        setData(result);
        setItems(result.items);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [chapterId, isLoggedIn, tick]);

  useEffect(
    () => () => {
      if (undoTimer.current !== null) window.clearTimeout(undoTimer.current);
    },
    []
  );

  const setBusy = (term: string, busy: boolean) =>
    setBusyTerms(prev => {
      const next = new Set(prev);
      if (busy) next.add(term);
      else next.delete(term);
      return next;
    });

  const removeItem = (term: string) => setItems(prev => prev.filter(item => item.term !== term));

  const handleAccept = async (item: SuggestionItem) => {
    if (chapterId === null || busyTerms.has(item.term)) return;
    setBusy(item.term, true);
    setNotice(null);
    try {
      const result = await acceptSuggestion(chapterId, item.term);
      setNotice(saveResultMessage(item.term, result));
      removeItem(item.term);
    } catch (err) {
      if (isSuggestionAlreadySaved(err)) {
        setNotice(`“${item.term}” đã có trong Sổ tay`);
        removeItem(item.term);
      } else {
        setNotice(errorMessage(err));
      }
    } finally {
      setBusy(item.term, false);
    }
  };

  const handleDismiss = async (item: SuggestionItem) => {
    if (busyTerms.has(item.term)) return;
    setBusy(item.term, true);
    setNotice(null);
    try {
      await dismissSuggestion(item.term);
      const index = items.findIndex(candidate => candidate.term === item.term);
      removeItem(item.term);
      setUndo({ item, index: Math.max(0, index) });
      if (undoTimer.current !== null) window.clearTimeout(undoTimer.current);
      undoTimer.current = window.setTimeout(() => setUndo(null), UNDO_VISIBLE_MS);
    } catch (err) {
      setNotice(errorMessage(err));
    } finally {
      setBusy(item.term, false);
    }
  };

  const handleUndo = useCallback(async () => {
    if (!undo) return;
    const { item, index } = undo;
    setUndo(null);
    try {
      await restoreSuggestion(item.term);
      setItems(prev => {
        const next = [...prev];
        next.splice(Math.min(index, next.length), 0, item);
        return next;
      });
    } catch (err) {
      setNotice(errorMessage(err));
    }
  }, [undo]);

  return (
    <div className="rounded-3xl border border-blue-100/70 bg-white p-5 shadow-soft">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-[#a43073]">tips_and_updates</span>
          <span className="text-xs font-bold uppercase tracking-wide text-[#a43073]">Từ nên học</span>
        </div>
        {isLoggedIn && chapterId !== null && (
          <button onClick={() => setTick(value => value + 1)} disabled={loading} className="text-[11px] font-bold text-slate-400 hover:text-[#a43073] disabled:opacity-50" title="Tải lại gợi ý">
            Làm mới
          </button>
        )}
      </div>

      {!isLoggedIn ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs leading-relaxed text-slate-600">Đăng nhập để nhận gợi ý những từ đáng học nhất trong chương này.</p>
          <button onClick={() => onRequireLogin('Vui lòng đăng nhập để xem gợi ý từ nên học!')} className="self-start rounded-full bg-[#a43073] px-4 py-1.5 text-xs font-bold text-white hover:bg-[#85145a]">
            Đăng nhập
          </button>
        </div>
      ) : chapterId === null ? (
        <p className="text-xs leading-relaxed text-slate-500">Gợi ý từ chỉ có khi bạn đọc một chương của truyện.</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {data?.status === 'processing' && (
            <div className="rounded-xl bg-amber-50 px-3 py-2 text-[11px] font-semibold text-amber-800">Chương đang được xử lý, gợi ý có thể chưa đủ.</div>
          )}
          {data && data.hsk_level === null && (
            <div className="rounded-xl bg-blue-50 px-3 py-2 text-[11px] text-blue-900">
              Bạn chưa khai báo trình độ nên gợi ý xếp theo tần suất và số lần tra.{' '}
              {onOpenLearningSettings && (
                <button onClick={onOpenLearningSettings} className="font-bold underline">Khai báo trình độ</button>
              )}
            </div>
          )}
          {notice && <div className="rounded-xl bg-emerald-50 px-3 py-2 text-[11px] font-semibold text-emerald-800">{notice}</div>}

          {loading && <p className="py-3 text-center text-xs text-slate-500">Đang tìm từ nên học...</p>}
          {error && (
            <div className="flex items-center justify-between gap-2 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700">
              <span>{error}</span>
              <button onClick={() => setTick(value => value + 1)} className="font-bold text-[#a43073] hover:underline">Thử lại</button>
            </div>
          )}
          {!loading && !error && data && items.length === 0 && (
            <p className="py-3 text-center text-xs leading-relaxed text-slate-500">
              {data.status === 'processing'
                ? 'Chưa có gợi ý nào, hãy quay lại khi chương xử lý xong.'
                : 'Không còn từ nào để gợi ý trong chương này. Bạn có thể xem lại từ đã bỏ qua trong Sổ tay.'}
            </p>
          )}

          {items.map(item => {
            const busy = busyTerms.has(item.term);
            return (
              <div key={item.term} className="rounded-2xl border border-slate-100 bg-slate-50 p-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-['Noto_Serif_SC'] text-base font-bold text-slate-800">{item.term}</span>
                      {item.pinyin && <span className="font-mono text-[11px] text-slate-500">{item.pinyin}</span>}
                      <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-900">{hskLabel(item.hsk_level)}</span>
                    </div>
                    {item.meaning_vi && <div className="text-xs font-medium text-slate-600">{item.meaning_vi}</div>}
                    <div className="mt-0.5 text-[10px] text-slate-400">
                      Xuất hiện {item.occurrences} lần •{' '}
                      <button onClick={() => onGoToPage(item.page_no)} className="font-semibold text-[#a43073] hover:underline" title="Nhảy tới trang này">
                        trang {item.page_no}
                      </button>
                    </div>
                  </div>
                  <button
                    onClick={() => void speakChinese(item.term)}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-slate-400 hover:bg-pink-100 hover:text-pink-600"
                    title="Phát âm"
                    aria-label={`Phát âm ${item.term}`}
                  >
                    <span className="material-symbols-outlined text-[16px]">volume_up</span>
                  </button>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <button
                    onClick={() => void handleAccept(item)}
                    disabled={busy}
                    className="flex-1 rounded-full bg-[#a43073] py-1.5 text-[11px] font-bold text-white hover:bg-[#85145a] disabled:opacity-60"
                  >
                    {busy ? 'Đang xử lý...' : 'Lưu'}
                  </button>
                  <button
                    onClick={() => void handleDismiss(item)}
                    disabled={busy}
                    className="flex-1 rounded-full bg-white py-1.5 text-[11px] font-bold text-slate-600 hover:bg-slate-200 disabled:opacity-60"
                  >
                    Bỏ qua
                  </button>
                </div>
              </div>
            );
          })}

          {undo && (
            <div className="flex items-center justify-between gap-2 rounded-xl bg-slate-800 px-3 py-2 text-[11px] text-white">
              <span>Đã bỏ qua “{undo.item.term}”</span>
              <button onClick={() => void handleUndo()} className="font-bold text-pink-300 hover:underline">Hoàn tác</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
