import React, { useState } from 'react';
import { errorMessage } from '../api/client';
import { ApiSeries, deleteSeries, updateSeries } from '../api/library';
import { ConfirmDialog } from './ConfirmDialog';

interface SeriesEditPanelProps {
  series: ApiSeries;
  isAdmin: boolean;
  /** Gọi sau khi sửa xong để nơi gọi tải lại dữ liệu. */
  onUpdated: () => void;
  /** Gọi sau khi xóa truyện (đóng hộp quản lý). */
  onDeleted: () => void;
  showToast: (message: string) => void;
}

const inputClass =
  'w-full text-xs font-medium text-slate-700 dark:text-slate-100 bg-white dark:bg-[#1e293b] p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-[#f472b6]';

/** Sửa thông tin và xóa truyện của mình (F03.09); chỉ hiển thị khi người dùng có quyền sửa. */
export const SeriesEditPanel: React.FC<SeriesEditPanelProps> = ({ series, isAdmin, onUpdated, onDeleted, showToast }) => {
  const [open, setOpen] = useState(false);
  const [titleVi, setTitleVi] = useState(series.title_vi);
  const [titleZh, setTitleZh] = useState(series.title_zh ?? '');
  const [author, setAuthor] = useState(series.author ?? '');
  const [description, setDescription] = useState(series.description ?? '');
  const [hsk, setHsk] = useState(series.est_hsk_level ? String(series.est_hsk_level) : '');
  const [genres, setGenres] = useState(series.genres.join(', '));
  const [status, setStatus] = useState<ApiSeries['status']>(series.status);
  const [visibility, setVisibility] = useState<ApiSeries['visibility']>(series.visibility);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = async () => {
    if (!titleVi.trim()) {
      setError('Tên truyện không được để trống.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateSeries(series.id, {
        title_vi: titleVi.trim(),
        title_zh: titleZh.trim() || null,
        author: author.trim() || null,
        description: description.trim() || null,
        est_hsk_level: hsk ? Number(hsk) : null,
        genres: genres.split(',').map(item => item.trim()).filter(Boolean),
        status,
        ...(isAdmin ? { visibility } : {})
      });
      showToast('Đã lưu thông tin truyện.');
      setOpen(false);
      onUpdated();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    setBusy(true);
    try {
      await deleteSeries(series.id);
      setConfirmDelete(false);
      showToast(`Đã xóa truyện “${series.title_vi}”.`);
      onDeleted();
    } catch (err) {
      setConfirmDelete(false);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 overflow-hidden">
      <div className="flex items-center justify-between gap-2 p-3">
        <button
          onClick={() => setOpen(value => !value)}
          className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-1.5"
          aria-expanded={open}
        >
          <span className="material-symbols-outlined text-[16px] text-[#a43073] dark:text-pink-400">edit</span>
          Sửa thông tin truyện
          <span className="material-symbols-outlined text-[16px] text-slate-400 dark:text-slate-500">{open ? 'expand_less' : 'expand_more'}</span>
        </button>
        <button
          onClick={() => setConfirmDelete(true)}
          disabled={busy}
          className="px-3 py-1.5 rounded-full bg-white dark:bg-[#1e293b] border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 text-[11px] font-bold hover:bg-red-50 dark:hover:bg-slate-700 disabled:opacity-60 flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-[14px]">delete</span>
          Xóa truyện
        </button>
      </div>

      {open && (
        <div className="p-3 pt-0 space-y-3">
          {error && (
            <div className="p-2.5 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 text-[11px] text-red-700 dark:text-red-400" role="alert">{error}</div>
          )}
          <div>
            <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-title-vi">Tên truyện (tiếng Việt) *</label>
            <input id="edit-series-title-vi" value={titleVi} onChange={e => setTitleVi(e.target.value)} maxLength={255} className={inputClass} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-title-zh">Tên gốc (tiếng Trung)</label>
              <input id="edit-series-title-zh" value={titleZh} onChange={e => setTitleZh(e.target.value)} maxLength={255} className={inputClass} />
            </div>
            <div>
              <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-author">Tác giả</label>
              <input id="edit-series-author" value={author} onChange={e => setAuthor(e.target.value)} maxLength={255} className={inputClass} />
            </div>
          </div>
          <div>
            <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-description">Mô tả</label>
            <textarea id="edit-series-description" value={description} onChange={e => setDescription(e.target.value)} maxLength={5000} rows={3} className={inputClass} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-hsk">Cấp HSK ước lượng</label>
              <select id="edit-series-hsk" value={hsk} onChange={e => setHsk(e.target.value)} className={inputClass}>
                <option value="">Chưa xác định</option>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(level => (
                  <option key={level} value={level}>HSK {level}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-status">Tình trạng</label>
              <select id="edit-series-status" value={status} onChange={e => setStatus(e.target.value as ApiSeries['status'])} className={inputClass}>
                <option value="ongoing">Đang ra</option>
                <option value="completed">Hoàn thành</option>
              </select>
            </div>
          </div>
          <div className={isAdmin ? 'grid grid-cols-2 gap-3' : ''}>
            <div>
              <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-genres">Thể loại (cách nhau dấu phẩy)</label>
              <input id="edit-series-genres" value={genres} onChange={e => setGenres(e.target.value)} className={inputClass} />
            </div>
            {isAdmin && (
              <div>
                <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="edit-series-visibility">Hiển thị</label>
                <select id="edit-series-visibility" value={visibility} onChange={e => setVisibility(e.target.value as ApiSeries['visibility'])} className={inputClass}>
                  <option value="private">Riêng tư</option>
                  <option value="public">Công khai</option>
                </select>
              </div>
            )}
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={busy}
              className="px-5 py-2 rounded-full text-xs font-bold text-white bg-gradient-to-r from-pink-500 to-[#a43073] shadow-md disabled:opacity-60"
            >
              {busy ? 'Đang lưu...' : 'Lưu thông tin'}
            </button>
          </div>
        </div>
      )}

      {!open && error && (
        <div className="m-3 mt-0 p-2.5 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 text-[11px] text-red-700 dark:text-red-400" role="alert">{error}</div>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Xóa truyện?"
          message={`Truyện “${series.title_vi}” cùng mọi chương và trang sẽ bị xóa vĩnh viễn. Thao tác không thể hoàn tác.`}
          confirmLabel="Xóa truyện"
          busy={busy}
          onConfirm={handleDelete}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  );
};
