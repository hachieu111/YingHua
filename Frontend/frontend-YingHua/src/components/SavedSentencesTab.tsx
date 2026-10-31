import React, { useCallback, useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import {
  SavedSentence,
  deleteSavedSentence,
  listSavedSentences,
  updateSentenceNote
} from '../api/sentences';
import { ReaderTarget } from '../types';
import { speakChinese } from '../utils/speech';
import { ConfirmDialog } from './ConfirmDialog';

interface SavedSentencesTabProps {
  onOpenReader: (target: ReaderTarget) => void;
  showToast: (message: string) => void;
}

const PAGE_SIZE = 10;
const NOTE_MAX = 1000;

/** Tab "Câu thoại đã lưu" của hồ sơ (F07.11): nghe, ghi chú, bỏ lưu, mở lại trang gốc. */
export const SavedSentencesTab: React.FC<SavedSentencesTabProps> = ({ onOpenReader, showToast }) => {
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<SavedSentence[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [noteDraft, setNoteDraft] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<SavedSentence | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    listSavedSentences(page, PAGE_SIZE, controller.signal)
      .then(result => {
        // Xóa hết mục ở trang cuối thì lùi về trang trước.
        if (result.items.length === 0 && result.total > 0 && page > 1) {
          setPage(page - 1);
          return;
        }
        setItems(result.items);
        setTotal(result.total);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, tick]);

  const reload = useCallback(() => setTick(value => value + 1), []);

  const startEdit = (item: SavedSentence) => {
    setEditingId(item.id);
    setNoteDraft(item.note ?? '');
  };

  const saveNote = async (item: SavedSentence) => {
    setBusyId(item.id);
    try {
      const updated = await updateSentenceNote(item.id, noteDraft.trim() || null);
      setItems(current => current.map(entry => (entry.id === item.id ? updated : entry)));
      setEditingId(null);
      showToast('Đã lưu ghi chú.');
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    setBusyId(confirmDelete.id);
    try {
      await deleteSavedSentence(confirmDelete.id);
      setConfirmDelete(null);
      showToast('Đã bỏ lưu câu thoại.');
      reload();
    } catch (err) {
      showToast(errorMessage(err));
      setConfirmDelete(null);
    } finally {
      setBusyId(null);
    }
  };

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  if (loading && items.length === 0) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true">
        {[0, 1].map(key => (
          <div key={key} className="h-24 animate-pulse rounded-3xl border border-pink-100 bg-white dark:border-pink-900/40 dark:bg-slate-800"></div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl border border-pink-100 bg-white p-8 text-center dark:border-pink-900/40 dark:bg-slate-800" role="alert">
        <p className="text-sm text-rose-700 dark:text-rose-400">{error}</p>
        <button onClick={reload} className="rounded-full border border-pink-200 bg-white px-4 py-1.5 text-xs font-bold text-[#a43073] hover:bg-pink-50 dark:border-pink-900/40 dark:bg-slate-800 dark:text-pink-400 dark:hover:bg-pink-900/40">
          Thử lại
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-3xl border border-pink-100 bg-white p-10 text-center dark:border-pink-900/40 dark:bg-slate-800">
        <span className="material-symbols-outlined text-[36px] text-pink-300">bookmark_add</span>
        <p className="text-sm font-bold text-slate-700 dark:text-slate-100">Bạn chưa lưu câu thoại nào</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">Trong trình đọc, rê chuột vào một khung thoại và bấm “Lưu câu” để lưu lại.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {items.map(item => (
        <div key={item.id} className="flex flex-col gap-2 rounded-3xl border border-pink-100 bg-white p-4 shadow-soft dark:border-pink-900/40 dark:bg-slate-800">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="font-['Noto_Serif_SC'] text-lg font-bold text-slate-800 dark:text-slate-100">{item.sentence_zh}</span>
                <button
                  onClick={() => void speakChinese(item.sentence_zh, 0.85)}
                  className="rounded-full bg-blue-100 p-1 text-blue-700 transition-transform hover:scale-110 dark:bg-blue-900/30 dark:text-blue-400"
                  title="Nghe câu"
                  aria-label="Nghe câu"
                >
                  <span className="material-symbols-outlined text-[16px]">volume_up</span>
                </button>
              </div>
              {item.pinyin && <span className="font-mono text-xs font-semibold text-blue-600 dark:text-blue-400">{item.pinyin}</span>}
              {item.sentence_vi && <p className="text-xs font-medium text-slate-700 dark:text-slate-100">“{item.sentence_vi}”</p>}
              {item.source_label && <span className="mt-0.5 text-[10px] text-slate-400">Trích từ: {item.source_label}</span>}
              {item.note && editingId !== item.id && (
                <p className="mt-1 whitespace-pre-wrap rounded-xl bg-amber-50 px-2.5 py-1.5 text-xs text-amber-900 dark:bg-amber-900/30 dark:text-amber-300">{item.note}</p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {item.chapter_id !== null && item.page_no !== null && (
                <button
                  onClick={() => onOpenReader({ chapterId: item.chapter_id, pageNo: item.page_no ?? undefined, pageId: item.page_id ?? undefined })}
                  className="rounded-full p-2 text-slate-400 transition-colors hover:bg-pink-50 hover:text-[#a43073] dark:hover:bg-pink-900/40 dark:hover:text-pink-300"
                  title="Mở trang gốc"
                  aria-label="Mở trang gốc"
                >
                  <span className="material-symbols-outlined text-[20px]">auto_stories</span>
                </button>
              )}
              <button
                onClick={() => startEdit(item)}
                className="rounded-full p-2 text-slate-400 transition-colors hover:bg-blue-50 hover:text-blue-700 dark:hover:bg-blue-900/40"
                title="Sửa ghi chú"
                aria-label="Sửa ghi chú"
              >
                <span className="material-symbols-outlined text-[20px]">edit_note</span>
              </button>
              <button
                onClick={() => setConfirmDelete(item)}
                className="rounded-full p-2 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/40"
                title="Bỏ lưu"
                aria-label="Bỏ lưu"
              >
                <span className="material-symbols-outlined text-[20px]">bookmark_remove</span>
              </button>
            </div>
          </div>

          {editingId === item.id && (
            <div className="flex flex-col gap-2">
              <textarea
                value={noteDraft}
                onChange={event => setNoteDraft(event.target.value)}
                maxLength={NOTE_MAX}
                rows={3}
                aria-label="Ghi chú"
                placeholder="Ghi chú của bạn về câu này..."
                className="w-full rounded-xl border border-slate-200 p-2.5 text-xs text-slate-700 outline-none focus:ring-2 focus:ring-[#f472b6] dark:border-slate-700 dark:text-slate-100"
              />
              <div className="flex items-center justify-end gap-2">
                <button onClick={() => setEditingId(null)} className="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700">Hủy</button>
                <button
                  onClick={() => void saveNote(item)}
                  disabled={busyId === item.id}
                  className="rounded-full bg-[#a43073] px-4 py-1.5 text-xs font-bold text-white hover:bg-[#85145a] disabled:opacity-60"
                >
                  {busyId === item.id ? 'Đang lưu...' : 'Lưu ghi chú'}
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      {pageCount > 1 && (
        <div className="flex items-center justify-center gap-3 pt-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
          <button
            onClick={() => setPage(value => Math.max(1, value - 1))}
            disabled={page <= 1 || loading}
            className="rounded-full bg-white px-3 py-1.5 shadow-xs hover:bg-pink-50 disabled:opacity-40 dark:bg-slate-800 dark:hover:bg-pink-900/40"
          >
            Trước
          </button>
          <span>Trang {page}/{pageCount} · {total} câu</span>
          <button
            onClick={() => setPage(value => Math.min(pageCount, value + 1))}
            disabled={page >= pageCount || loading}
            className="rounded-full bg-white px-3 py-1.5 shadow-xs hover:bg-pink-50 disabled:opacity-40 dark:bg-slate-800 dark:hover:bg-pink-900/40"
          >
            Sau
          </button>
        </div>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Bỏ lưu câu thoại?"
          message={`Câu “${confirmDelete.sentence_zh}” sẽ bị xóa khỏi danh sách đã lưu.`}
          confirmLabel="Bỏ lưu"
          busy={busyId === confirmDelete.id}
          onConfirm={() => void handleDelete()}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
};
