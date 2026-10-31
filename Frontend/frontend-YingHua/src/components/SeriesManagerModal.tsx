import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, errorMessage, isAbortedError } from '../api/client';
import {
  ApiPage,
  SeriesDetail,
  createChapter,
  createSeries,
  getSeries,
  setSeriesCover,
  uploadChapterPages,
  validateImageFile,
  MAX_CHAPTER_UPLOAD_FILES
} from '../api/library';
import { ChapterManageRow } from './ChapterManageRow';
import { SeriesEditPanel } from './SeriesEditPanel';
import { StatusPill } from './StatusPill';
import { usePageStatuses } from './usePageStatuses';

interface SeriesManagerModalProps {
  isOpen: boolean;
  /** null = tạo truyện mới; có id = quản lý truyện đã có. */
  seriesId: number | null;
  isAdmin: boolean;
  onClose: () => void;
  /** Gọi khi tạo/sửa xong để danh sách bên ngoài tải lại. */
  onChanged: () => void;
  showToast: (message: string) => void;
}

const inputClass =
  'w-full text-xs font-medium text-slate-700 dark:text-slate-100 bg-white dark:bg-[#1e293b] p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-[#f472b6]';

export const SeriesManagerModal: React.FC<SeriesManagerModalProps> = ({
  isOpen,
  seriesId,
  isAdmin,
  onClose,
  onChanged,
  showToast
}) => {
  const [currentId, setCurrentId] = useState<number | null>(seriesId);
  const [detail, setDetail] = useState<SeriesDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duplicate, setDuplicate] = useState(false);

  const [titleVi, setTitleVi] = useState('');
  const [titleZh, setTitleZh] = useState('');
  const [author, setAuthor] = useState('');
  const [description, setDescription] = useState('');
  const [hsk, setHsk] = useState('');
  const [genres, setGenres] = useState('');
  const [visibility, setVisibility] = useState<'private' | 'public'>('private');

  const [chapterNumber, setChapterNumber] = useState('');
  const [chapterTitle, setChapterTitle] = useState('');
  const [chapterTrial, setChapterTrial] = useState(false);

  const [uploadChapterId, setUploadChapterId] = useState<number | null>(null);
  const [uploaded, setUploaded] = useState<{ page: ApiPage; filename: string }[]>([]);
  const pageInputRef = useRef<HTMLInputElement>(null);
  const coverInputRef = useRef<HTMLInputElement>(null);
  const { statuses } = usePageStatuses(uploaded.map(row => row.page.id), isOpen);

  const load = useCallback(async (id: number, signal?: AbortSignal) => {
    setLoading(true);
    try {
      const data = await getSeries(id, signal);
      setDetail(data);
      const maxNumber = data.chapters.reduce((max, chapter) => Math.max(max, chapter.number), 0);
      setChapterNumber(String(Math.floor(maxNumber) + 1));
      setError(null);
    } catch (err) {
      if (!isAbortedError(err)) setError(errorMessage(err));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  // Mỗi lần mở: đặt lại biểu mẫu theo chế độ tạo hoặc quản lý.
  useEffect(() => {
    if (!isOpen) return;
    setCurrentId(seriesId);
    setDetail(null);
    setError(null);
    setDuplicate(false);
    setUploaded([]);
    setTitleVi('');
    setTitleZh('');
    setAuthor('');
    setDescription('');
    setHsk('');
    setGenres('');
    setVisibility('private');
    setChapterTitle('');
    setChapterTrial(false);
    setChapterNumber('1');
    if (seriesId === null) return;
    const controller = new AbortController();
    void load(seriesId, controller.signal);
    return () => controller.abort();
  }, [isOpen, seriesId, load]);

  if (!isOpen) return null;

  const handleCreate = async (confirmDuplicate = false) => {
    if (!titleVi.trim()) {
      setError('Vui lòng nhập tên truyện.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await createSeries({
        title_vi: titleVi.trim(),
        title_zh: titleZh.trim() || null,
        author: author.trim() || null,
        description: description.trim() || null,
        est_hsk_level: hsk ? Number(hsk) : null,
        genres: genres.split(',').map(item => item.trim()).filter(Boolean),
        visibility: isAdmin ? visibility : 'private',
        confirm_duplicate: confirmDuplicate
      });
      setDuplicate(false);
      setCurrentId(created.id);
      onChanged();
      showToast(`Đã tạo truyện “${created.title_vi}”. Hãy thêm chương và tải trang.`);
      await load(created.id);
    } catch (err) {
      if (err instanceof ApiError && err.code === 'SERIES_TITLE_DUPLICATE') setDuplicate(true);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleAddChapter = async () => {
    if (currentId === null) return;
    const number = Number(chapterNumber);
    if (!Number.isFinite(number) || number < 0) {
      setError('Số chương không hợp lệ.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createChapter(currentId, { number, title: chapterTitle.trim() || null, is_trial: chapterTrial });
      setChapterTitle('');
      setChapterTrial(false);
      onChanged();
      await load(currentId);
      showToast('Đã thêm chương mới.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handlePagesChosen = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = Array.from(event.target.files ?? []);
    event.target.value = '';
    if (uploadChapterId === null || chosen.length === 0) return;
    const picked = chosen.slice(0, MAX_CHAPTER_UPLOAD_FILES);
    const truncated = chosen.length > MAX_CHAPTER_UPLOAD_FILES;
    const invalid = picked.map(validateImageFile).filter((message): message is string => message !== null);
    if (invalid.length > 0) {
      setError(invalid.join(' '));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await uploadChapterPages(uploadChapterId, picked);
      const rows = result.results.flatMap(item =>
        item.page ? [{ page: item.page, filename: item.filename ?? `Trang ${item.page.page_no}` }] : []
      );
      const failures = result.results.filter(item => item.error).map(item => `“${item.filename ?? 'ảnh'}”: ${item.error?.message}`);
      setUploaded(current => [...current, ...rows]);
      const notices = [...failures];
      if (truncated) notices.push(`Mỗi lần tải tối đa ${MAX_CHAPTER_UPLOAD_FILES} ảnh, đã lấy ${MAX_CHAPTER_UPLOAD_FILES} ảnh đầu`);
      if (notices.length > 0) setError(notices.join(' '));
      if (result.created > 0) {
        showToast(`Đã tải ${result.created} trang vào chương, đang xếp hàng xử lý.`);
        onChanged();
        if (currentId !== null) await load(currentId);
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleCover = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || currentId === null) return;
    const problem = validateImageFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    try {
      await setSeriesCover(currentId, file);
      onChanged();
      showToast('Đã đặt ảnh bìa.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const creating = currentId === null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white dark:bg-[#0f172a] w-full max-w-xl max-h-[92vh] overflow-y-auto rounded-3xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 transition-colors duration-300">
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 dark:border-slate-700 bg-gradient-to-r from-pink-50/70 via-white to-pink-50/40 dark:from-pink-900/20 dark:via-[#0f172a] dark:to-pink-900/10 sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center text-[#a43073] dark:text-pink-400">
              <span className="material-symbols-outlined text-[20px]">auto_stories</span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800 dark:text-white">{creating ? 'Tạo truyện mới' : (detail?.series.title_vi ?? 'Quản lý truyện')}</h3>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                {creating ? 'Truyện riêng tư chỉ mình bạn xem được' : 'Thêm chương và tải ảnh các trang'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 flex items-center justify-center transition-colors"
            aria-label="Đóng"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-2xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 text-[11px] text-red-700 dark:text-red-400" role="alert">
              {error}
              {duplicate && (
                <button onClick={() => handleCreate(true)} disabled={busy} className="ml-2 font-bold underline">
                  Vẫn tạo truyện này
                </button>
              )}
            </div>
          )}

          {creating ? (
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="series-title-vi">Tên truyện (tiếng Việt) *</label>
                <input id="series-title-vi" value={titleVi} onChange={event => setTitleVi(event.target.value)} maxLength={255} className={inputClass} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="series-title-zh">Tên gốc (tiếng Trung)</label>
                  <input id="series-title-zh" value={titleZh} onChange={event => setTitleZh(event.target.value)} maxLength={255} className={inputClass} />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="series-author">Tác giả</label>
                  <input id="series-author" value={author} onChange={event => setAuthor(event.target.value)} maxLength={255} className={inputClass} />
                </div>
              </div>
              <div>
                <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="series-description">Mô tả</label>
                <textarea id="series-description" value={description} onChange={event => setDescription(event.target.value)} maxLength={5000} rows={3} className={inputClass} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="series-hsk">Cấp HSK ước lượng</label>
                  <select id="series-hsk" value={hsk} onChange={event => setHsk(event.target.value)} className={inputClass}>
                    <option value="">Chưa xác định</option>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(level => (
                      <option key={level} value={level}>HSK {level}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="series-genres">Thể loại (cách nhau dấu phẩy)</label>
                  <input id="series-genres" value={genres} onChange={event => setGenres(event.target.value)} placeholder="Học đường, Hài hước" className={inputClass} />
                </div>
              </div>
              {isAdmin && (
                <div>
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="series-visibility">Hiển thị</label>
                  <select id="series-visibility" value={visibility} onChange={event => setVisibility(event.target.value as 'private' | 'public')} className={inputClass}>
                    <option value="private">Riêng tư (chỉ mình tôi)</option>
                    <option value="public">Công khai (mọi người thấy ở Trang Chủ)</option>
                  </select>
                </div>
              )}
            </div>
          ) : (
            <>
              {loading && !detail && (
                <div className="flex justify-center py-6">
                  <span className="w-6 h-6 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
                </div>
              )}

              {detail && (
                <>
                  <div className="flex items-center justify-between gap-3 p-3 rounded-2xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                    <span className="text-xs text-slate-600 dark:text-slate-300">
                      {detail.series.visibility === 'public' ? 'Truyện công khai' : 'Truyện riêng tư'} · {detail.chapters.length} chương
                    </span>
                    <button
                      onClick={() => coverInputRef.current?.click()}
                      disabled={busy}
                      className="px-3 py-1.5 rounded-full bg-white dark:bg-[#1e293b] border border-pink-100 dark:border-pink-900/40 text-[#a43073] dark:text-pink-400 text-[11px] font-bold hover:bg-pink-50 dark:hover:bg-slate-700 disabled:opacity-60"
                    >
                      Đặt ảnh bìa
                    </button>
                    <input ref={coverInputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleCover} />
                  </div>

                  {detail.series.can_edit && (
                    <SeriesEditPanel
                      key={detail.series.updated_at}
                      series={detail.series}
                      isAdmin={isAdmin}
                      onUpdated={() => {
                        onChanged();
                        if (currentId !== null) void load(currentId);
                      }}
                      onDeleted={() => {
                        onChanged();
                        onClose();
                      }}
                      showToast={showToast}
                    />
                  )}

                  <div>
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100 mb-2">Chương</h4>
                    {detail.chapters.length === 0 ? (
                      <p className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 rounded-2xl p-4 text-center">Chưa có chương nào. Thêm chương đầu tiên bên dưới.</p>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {detail.chapters.map(chapter => (
                          <ChapterManageRow
                            key={chapter.id}
                            chapter={chapter}
                            canEdit={detail.series.can_edit}
                            canSetTrial={isAdmin && detail.series.visibility === 'public'}
                            disabled={busy}
                            onUploadPages={() => {
                              setUploadChapterId(chapter.id);
                              pageInputRef.current?.click();
                            }}
                            onChanged={() => {
                              onChanged();
                              if (currentId !== null) void load(currentId);
                            }}
                            showToast={showToast}
                          />
                        ))}
                      </div>
                    )}
                    <p className="mt-2 text-[10px] text-slate-400 dark:text-slate-500">Tải trang: tối đa {MAX_CHAPTER_UPLOAD_FILES} ảnh mỗi lần, mỗi ảnh ≤ 10MB.</p>
                    <input ref={pageInputRef} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={handlePagesChosen} />
                  </div>

                  <div className="p-4 rounded-2xl border border-pink-100 dark:border-slate-700 bg-pink-50/30 dark:bg-pink-900/10 space-y-3">
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100">Thêm chương</h4>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="chapter-number">Số chương</label>
                        <input id="chapter-number" type="number" min={0} step="0.1" value={chapterNumber} onChange={event => setChapterNumber(event.target.value)} className={inputClass} />
                      </div>
                      <div className="col-span-2">
                        <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1" htmlFor="chapter-title">Tên chương (tùy chọn)</label>
                        <input id="chapter-title" value={chapterTitle} onChange={event => setChapterTitle(event.target.value)} maxLength={255} className={inputClass} />
                      </div>
                    </div>
                    {isAdmin && detail.series.visibility === 'public' && (
                      <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                        <input type="checkbox" checked={chapterTrial} onChange={event => setChapterTrial(event.target.checked)} />
                        Cho Khách đọc thử chương này
                      </label>
                    )}
                    <button
                      onClick={handleAddChapter}
                      disabled={busy}
                      className="px-4 py-2 rounded-full bg-white dark:bg-[#1e293b] border border-pink-200 dark:border-pink-900/40 text-[#a43073] dark:text-pink-400 text-xs font-bold hover:bg-pink-50 dark:hover:bg-slate-700 disabled:opacity-60"
                    >
                      + Thêm chương
                    </button>
                  </div>

                  {uploaded.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100 mb-2">Trang vừa tải lên</h4>
                      <div className="flex flex-col gap-2">
                        {uploaded.map(({ page, filename }) => {
                          const live = statuses[page.id];
                          return (
                            <div key={page.id} className="flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                              <span className="text-[11px] text-slate-700 dark:text-slate-200 truncate">{filename}</span>
                              <StatusPill status={live ? live.status : page.status} textReady={(live ? live.text_ready : page.text_ready) === true} />
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>

        <div className="px-6 py-4 bg-slate-50 dark:bg-[#0f172a] border-t border-slate-100 dark:border-slate-700 flex items-center justify-end gap-2.5">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            {creating ? 'Hủy bỏ' : 'Xong'}
          </button>
          {creating && (
            <button
              onClick={() => handleCreate(false)}
              disabled={busy}
              className="px-5 py-2 rounded-full text-xs font-bold text-white bg-gradient-to-r from-pink-500 to-[#a43073] hover:opacity-95 shadow-md transition-all disabled:opacity-60"
            >
              {busy ? 'Đang tạo...' : 'Tạo truyện'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
