import React, { useState } from 'react';
import { errorMessage } from '../api/client';
import { ApiChapter, deleteChapter, updateChapter } from '../api/library';
import { formatChapterNumber } from '../utils/format';
import { ConfirmDialog } from './ConfirmDialog';

interface ChapterManageRowProps {
  chapter: ApiChapter;
  canEdit: boolean;
  /** Chỉ quản trị viên được bật "đọc thử" và chỉ với truyện công khai. */
  canSetTrial: boolean;
  disabled: boolean;
  onUploadPages: () => void;
  onChanged: () => void;
  showToast: (message: string) => void;
}

const inputClass =
  'w-full text-xs font-medium text-slate-700 bg-white p-2 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-[#f472b6]';

/** Một dòng chương trong hộp quản lý truyện: tải trang, sửa số/tên/đọc thử, xóa chương (F03.09). */
export const ChapterManageRow: React.FC<ChapterManageRowProps> = ({
  chapter,
  canEdit,
  canSetTrial,
  disabled,
  onUploadPages,
  onChanged,
  showToast
}) => {
  const [editing, setEditing] = useState(false);
  const [number, setNumber] = useState(String(chapter.number));
  const [title, setTitle] = useState(chapter.title ?? '');
  const [trial, setTrial] = useState(chapter.is_trial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const startEdit = () => {
    setNumber(String(chapter.number));
    setTitle(chapter.title ?? '');
    setTrial(chapter.is_trial);
    setError(null);
    setEditing(true);
  };

  const handleSave = async () => {
    const parsed = Number(number);
    if (!Number.isFinite(parsed) || parsed < 0) {
      setError('Số chương không hợp lệ.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateChapter(chapter.id, {
        number: parsed,
        title: title.trim() || null,
        ...(canSetTrial ? { is_trial: trial } : {})
      });
      showToast('Đã lưu chương.');
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    setBusy(true);
    try {
      await deleteChapter(chapter.id);
      setConfirmDelete(false);
      showToast(`Đã xóa chương ${formatChapterNumber(chapter.number)}.`);
      onChanged();
    } catch (err) {
      setConfirmDelete(false);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="px-4 py-2.5 rounded-2xl bg-slate-50 border border-slate-100">
      <div className="flex items-center justify-between gap-3">
        <span className="min-w-0">
          <span className="text-xs font-bold text-slate-800">Chương {formatChapterNumber(chapter.number)}</span>
          {chapter.title && <span className="text-xs text-slate-500"> · {chapter.title}</span>}
          <span className="block text-[10px] text-slate-400">
            {chapter.page_count} trang{chapter.is_trial ? ' · đọc thử' : ''}
          </span>
        </span>
        <span className="shrink-0 flex items-center gap-1.5">
          {canEdit && (
            <>
              <button
                onClick={editing ? () => setEditing(false) : startEdit}
                disabled={disabled || busy}
                className="w-8 h-8 rounded-full bg-white border border-slate-200 text-slate-600 hover:text-[#a43073] hover:border-pink-200 flex items-center justify-center disabled:opacity-60"
                aria-label={editing ? 'Đóng sửa chương' : 'Sửa chương'}
                title="Sửa chương"
              >
                <span className="material-symbols-outlined text-[16px]">{editing ? 'close' : 'edit'}</span>
              </button>
              <button
                onClick={() => setConfirmDelete(true)}
                disabled={disabled || busy}
                className="w-8 h-8 rounded-full bg-white border border-slate-200 text-slate-600 hover:text-red-600 hover:border-red-200 flex items-center justify-center disabled:opacity-60"
                aria-label="Xóa chương"
                title="Xóa chương"
              >
                <span className="material-symbols-outlined text-[16px]">delete</span>
              </button>
            </>
          )}
          <button
            onClick={onUploadPages}
            disabled={disabled || busy}
            className="px-3 py-1.5 rounded-full bg-[#a43073] text-white text-[11px] font-bold hover:bg-[#85145a] disabled:opacity-60 flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">add_photo_alternate</span>
            Tải trang
          </button>
        </span>
      </div>

      {editing && (
        <div className="mt-3 space-y-2.5">
          {error && <div className="p-2 rounded-xl bg-red-50 border border-red-200 text-[11px] text-red-700" role="alert">{error}</div>}
          <div className="grid grid-cols-3 gap-2.5">
            <div>
              <label className="text-[11px] font-bold text-slate-500 block mb-1" htmlFor={`chapter-edit-number-${chapter.id}`}>Số chương</label>
              <input id={`chapter-edit-number-${chapter.id}`} type="number" min={0} step="0.1" value={number} onChange={e => setNumber(e.target.value)} className={inputClass} />
            </div>
            <div className="col-span-2">
              <label className="text-[11px] font-bold text-slate-500 block mb-1" htmlFor={`chapter-edit-title-${chapter.id}`}>Tên chương</label>
              <input id={`chapter-edit-title-${chapter.id}`} value={title} onChange={e => setTitle(e.target.value)} maxLength={255} className={inputClass} />
            </div>
          </div>
          {canSetTrial && (
            <label className="flex items-center gap-2 text-xs text-slate-600">
              <input type="checkbox" checked={trial} onChange={e => setTrial(e.target.checked)} />
              Cho Khách đọc thử chương này
            </label>
          )}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={busy}
              className="px-4 py-1.5 rounded-full bg-white border border-pink-200 text-[#a43073] text-[11px] font-bold hover:bg-pink-50 disabled:opacity-60"
            >
              {busy ? 'Đang lưu...' : 'Lưu chương'}
            </button>
          </div>
        </div>
      )}

      {!editing && error && (
        <div className="mt-2 p-2 rounded-xl bg-red-50 border border-red-200 text-[11px] text-red-700" role="alert">{error}</div>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Xóa chương?"
          message={`Chương ${formatChapterNumber(chapter.number)} cùng ${chapter.page_count} trang sẽ bị xóa vĩnh viễn. Thao tác không thể hoàn tác.`}
          confirmLabel="Xóa chương"
          busy={busy}
          onConfirm={handleDelete}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  );
};
