import React, { useCallback, useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { hskLabel } from '../api/dictionary';
import {
  ApiChapter,
  SeriesDetail,
  addToLibrary,
  getSeries,
  pickReadTarget,
  rateSeries,
  removeFromLibrary,
  setFavorite
} from '../api/library';
import { ReaderTarget } from '../types';
import { AuthImage } from './AuthImage';
import { VipPill } from './AvatarFrame';
import { UnlockVipDialog } from './UnlockVipDialog';

interface SeriesDetailModalProps {
  seriesId: number | null;
  isLoggedIn: boolean;
  onClose: () => void;
  onOpenReader: (target: ReaderTarget) => void;
  onRequireLogin: (message: string) => void;
  showToast: (message: string) => void;
  /** Gọi khi dữ liệu thay đổi (lưu vào Thư viện, chấm sao...) để danh sách bên ngoài tải lại. */
  onChanged?: () => void;
  /** Mở trình quản lý truyện (chỉ hiện với truyện do người dùng sở hữu). */
  onManage?: (seriesId: number) => void;
}

const formatChapterNumber = (value: number) => (Number.isInteger(value) ? String(value) : value.toFixed(1));

export const SeriesDetailModal: React.FC<SeriesDetailModalProps> = ({
  seriesId,
  isLoggedIn,
  onClose,
  onOpenReader,
  onRequireLogin,
  showToast,
  onChanged,
  onManage
}) => {
  const [detail, setDetail] = useState<SeriesDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hoverStars, setHoverStars] = useState(0);
  // Mở hộp mở khóa bằng vé khi người học chạm vào chương khóa của truyện VIP (F17.06).
  const [unlockOpen, setUnlockOpen] = useState(false);

  const load = useCallback(
    (signal?: AbortSignal) => {
      if (seriesId === null) return Promise.resolve();
      return getSeries(seriesId, signal)
        .then(data => {
          setDetail(data);
          setError(null);
        })
        .catch(err => {
          if (!isAbortedError(err)) setError(errorMessage(err));
        });
    },
    [seriesId]
  );

  useEffect(() => {
    setDetail(null);
    setError(null);
    if (seriesId === null) return;
    const controller = new AbortController();
    setLoading(true);
    load(controller.signal).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [seriesId, load]);

  if (seriesId === null) return null;

  const series = detail?.series;

  const openChapter = (chapter: ApiChapter) => {
    if (chapter.page_count === 0) return;
    if (!isLoggedIn && !chapter.is_trial) {
      onRequireLogin('Vui lòng đăng nhập để đọc chương này. Khách chỉ đọc thử được các chương dùng thử.');
      return;
    }
    if (chapter.is_locked) {
      setUnlockOpen(true);
      return;
    }
    const resume = detail?.progress;
    const sameChapter = resume && resume.chapter_id === chapter.id;
    onOpenReader({
      chapterId: chapter.id,
      pageNo: sameChapter ? resume.page_no : undefined,
      pageId: sameChapter ? (resume.page_id ?? undefined) : undefined
    });
    onClose();
  };

  const handleStart = () => {
    if (!detail) return;
    const target = pickReadTarget(detail, { guest: !isLoggedIn, restart: Boolean(detail.series.progress?.completed) });
    if (!target) {
      if (isLoggedIn && detail.series.is_vip && detail.chapters.some(chapter => chapter.page_count > 0 && chapter.is_locked)) {
        setUnlockOpen(true);
        return;
      }
      showToast(isLoggedIn ?'Truyện này chưa có chương nào có trang để đọc.' : 'Truyện này chưa có chương dùng thử cho Khách.');
      return;
    }
    onOpenReader(target);
    onClose();
  };

  const runAction = async (action: () => Promise<unknown>, success?: string) => {
    setBusy(true);
    try {
      await action();
      await load();
      onChanged?.();
      if (success) showToast(success);
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleLibrary = () => {
    if (!series) return;
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để lưu truyện vào Thư viện của bạn!');
      return;
    }
    void runAction(
      () => (series.in_library ? removeFromLibrary(series.id) : addToLibrary(series.id)),
      series.in_library ? 'Đã bỏ truyện khỏi Thư viện.' : 'Đã lưu truyện vào Thư viện của bạn!'
    );
  };

  const toggleFavorite = () => {
    if (!series || !series.in_library) return;
    void runAction(() => setFavorite(series.id, !series.is_favorite));
  };

  const rate = (stars: number) => {
    if (!series) return;
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để chấm sao cho truyện!');
      return;
    }
    void runAction(() => rateSeries(series.id, stars), `Cảm ơn bạn đã đánh giá ${stars} sao!`);
  };

  const shownStars = hoverStars || detail?.my_rating || 0;

  return (
    <>
    <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-[#0f172a] w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-3xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 transition-colors duration-300"
        onClick={event => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Chi tiết truyện"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 dark:border-slate-700 bg-gradient-to-r from-pink-50/70 via-white to-pink-50/40 dark:from-pink-900/20 dark:via-[#0f172a] dark:to-pink-900/10 sticky top-0 z-10">
          <h3 className="text-sm font-bold text-slate-800 dark:text-white">Chi tiết truyện</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 flex items-center justify-center transition-colors"
            aria-label="Đóng"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {loading && !detail && (
          <div className="p-10 flex justify-center">
            <span className="w-6 h-6 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
          </div>
        )}

        {error && !detail && (
          <div className="p-8 text-center text-sm text-red-600 dark:text-red-400">
            <p>{error}</p>
            <button onClick={() => void load()} className="mt-3 px-4 py-2 rounded-full bg-pink-50 dark:bg-pink-900/20 text-[#a43073] dark:text-pink-400 text-xs font-bold hover:bg-pink-100 dark:hover:bg-pink-900/40">
              Thử lại
            </button>
          </div>
        )}

        {detail && series && (
          <div className="p-6 flex flex-col gap-6">
            <div className="flex flex-col sm:flex-row gap-5">
              <AuthImage
                src={series.cover_url}
                alt={series.title_vi}
                className="w-full sm:w-44 h-60 object-cover rounded-2xl shrink-0 border border-pink-100 dark:border-slate-700"
                fallback={<span className="material-symbols-outlined text-[40px]">auto_stories</span>}
              />
              <div className="flex flex-col gap-2 min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-400 text-xs font-bold">
                    {hskLabel(series.est_hsk_level)}
                  </span>
                  {series.genres.map(genre => (
                    <span key={genre} className="px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-300 text-xs font-medium">
                      {genre}
                    </span>
                  ))}
                  <span className="px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-medium">
                    {series.status === 'completed' ? 'Đã hoàn thành' : 'Đang ra'}
                  </span>
                  {series.is_vip && <VipPill label={series.vip_access === 'unlocked' ? 'VIP · đã mở khóa' : 'VIP'} />}
                  {series.visibility === 'private' && (
                    <span className="px-2.5 py-0.5 rounded-full bg-pink-50 dark:bg-pink-900/20 text-[#a43073] dark:text-pink-400 text-xs font-bold flex items-center gap-1">
                      <span className="material-symbols-outlined text-[13px]">lock</span>Riêng tư
                    </span>
                  )}
                </div>
                <h2 className="text-2xl font-extrabold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">{series.title_vi}</h2>
                {(series.title_zh || series.author) && (
                  <span className="text-xs font-['Noto_Serif_SC'] text-pink-600 dark:text-pink-400">
                    {[series.title_zh, series.author].filter(Boolean).join(' • ')}
                  </span>
                )}
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                  {series.description || 'Truyện chưa có mô tả.'}
                </p>

                <div className="flex items-center gap-2 mt-1">
                  <div className="flex items-center" onMouseLeave={() => setHoverStars(0)}>
                    {[1, 2, 3, 4, 5].map(value => (
                      <button
                        key={value}
                        disabled={busy}
                        onMouseEnter={() => setHoverStars(value)}
                        onClick={() => rate(value)}
                        className={`text-xl leading-none px-0.5 transition-colors ${value <= shownStars ? 'text-amber-500' : 'text-slate-300 dark:text-slate-600 hover:text-amber-300'}`}
                        aria-label={`Chấm ${value} sao`}
                      >
                        ★
                      </button>
                    ))}
                  </div>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {series.rating_avg !== null
                      ? `${series.rating_avg.toFixed(1)} (${series.rating_count} đánh giá)`
                      : 'Chưa có đánh giá'}
                    {detail.my_rating ? ` · Bạn chấm ${detail.my_rating} sao` : ''}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2.5 pt-2">
                  <button
                    onClick={handleStart}
                    className="px-5 py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs flex items-center gap-2 shadow-md shadow-pink-300/30 transition-all"
                  >
                    <span className="material-symbols-outlined text-[18px]">menu_book</span>
                    {detail.series.progress?.completed ? 'Đọc lại' : detail.progress ? `Đọc tiếp Chương ${formatChapterNumber(detail.progress.chapter_number)}` : 'Bắt đầu đọc'}
                  </button>
                  <button
                    onClick={toggleLibrary}
                    disabled={busy}
                    className="px-4 py-2.5 rounded-full bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs border border-slate-200 flex items-center gap-2 transition-colors disabled:opacity-60 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-100 dark:border-slate-700"
                  >
                    <span className="material-symbols-outlined text-[18px]">{series.in_library ? 'bookmark_remove' : 'bookmark_add'}</span>
                    {series.in_library ? 'Bỏ khỏi Thư viện' : 'Lưu vào Thư viện'}
                  </button>
                  {series.in_library && (
                    <button
                      onClick={toggleFavorite}
                      disabled={busy}
                      className={`px-4 py-2.5 rounded-full font-semibold text-xs border flex items-center gap-2 transition-colors disabled:opacity-60 ${
                        series.is_favorite ? 'bg-pink-100 text-[#a43073] border-pink-200 dark:bg-pink-900/30 dark:text-pink-400 dark:border-pink-900/40' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 dark:hover:bg-slate-700'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[18px]" style={series.is_favorite ? { fontVariationSettings: "'FILL' 1" } : undefined}>
                        favorite
                      </span>
                      {series.is_favorite ? 'Đã yêu thích' : 'Yêu thích'}
                    </button>
                  )}
                  {series.can_edit && onManage && (
                    <button
                      onClick={() => {
                        onManage(series.id);
                        onClose();
                      }}
                      className="px-4 py-2.5 rounded-full bg-blue-50 hover:bg-blue-100 text-blue-800 font-semibold text-xs flex items-center gap-2 transition-colors dark:bg-blue-900/30 dark:hover:bg-blue-900/40 dark:text-blue-300"
                    >
                      <span className="material-symbols-outlined text-[18px]">edit_note</span>
                      Quản lý chương và trang
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-bold text-slate-800 mb-2 dark:text-slate-100">Danh sách chương ({detail.chapters.length})</h4>
              {detail.chapters.length === 0 ? (
                <p className="text-xs text-slate-500 bg-slate-50 rounded-2xl p-4 text-center dark:text-slate-400 dark:bg-[#1e293b]">Truyện chưa có chương nào.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {detail.chapters.map(chapter => {
                    const locked = (!isLoggedIn && !chapter.is_trial) || chapter.is_locked;
                    const current = detail.progress?.chapter_id === chapter.id;
                    return (
                      <button
                        key={chapter.id}
                        onClick={() => openChapter(chapter)}
                        disabled={chapter.page_count === 0}
                        className="flex items-center justify-between gap-3 text-left px-4 py-2.5 rounded-2xl bg-slate-50 hover:bg-pink-50/70 border border-slate-100 hover:border-pink-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-[#1e293b] dark:border-slate-700"
                      >
                        <span className="min-w-0">
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-100">Chương {formatChapterNumber(chapter.number)}</span>
                          {chapter.title && <span className="text-xs text-slate-500 dark:text-slate-400"> · {chapter.title}</span>}
                          <span className="block text-[10px] text-slate-400">
                            {chapter.page_count > 0 ? `${chapter.page_count} trang` : 'Chưa có trang'}
                            {current && detail.progress ? ` · đang đọc đến trang ${detail.progress.page_no}` : ''}
                          </span>
                        </span>
                        <span className="flex items-center gap-2 shrink-0">
                          {chapter.is_trial && (
                            <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-bold border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-900/40">Đọc thử</span>
                          )}
                          {chapter.is_locked && <VipPill label="Cần VIP / vé" />}
                          <span className="material-symbols-outlined text-[18px] text-slate-400">{locked ? 'lock' : 'chevron_right'}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
              {!isLoggedIn && (
                <p className="mt-3 text-[11px] text-slate-500 dark:text-slate-400">Khách chỉ đọc thử được các chương có nhãn “Đọc thử”. Đăng nhập để đọc toàn bộ truyện.</p>
              )}
              {isLoggedIn && series.is_vip && series.vip_access === 'trial_only' && (
                <p className="mt-3 text-[11px] text-slate-500 dark:text-slate-400">Truyện VIP: bạn đọc thử được các chương “Đọc thử”. Dùng vé hoặc kích hoạt VIP để đọc toàn bộ.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
    {unlockOpen && series && (
      <UnlockVipDialog
        seriesId={series.id}
        seriesTitle={series.title_vi}
        onClose={() => setUnlockOpen(false)}
        onUnlocked={() => {
          void load();
          onChanged?.();
        }}
        showToast={showToast}
      />
    )}
    </>
  );
};
