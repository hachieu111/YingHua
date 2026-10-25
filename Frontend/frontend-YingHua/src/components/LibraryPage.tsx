import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { errorMessage } from '../api/client';
import { hskLabel } from '../api/dictionary';
import { retranslatePage } from '../api/imaging';
import {
  ApiPage,
  ApiSeries,
  LibraryTab,
  Paged,
  deletePage,
  getSeries,
  listLibrary,
  listQuickUploads,
  listSeries,
  pickReadTarget,
  setFavorite
} from '../api/library';
import { BookmarkItem, listBookmarks } from '../api/reader';
import { ApiSettings, getSettings } from '../api/settings';
import { countVocab } from '../api/vocab';
import { ReaderTarget } from '../types';
import { formatChapterNumber, timeAgo } from '../utils/format';
import { AuthImage } from './AuthImage';
import { ConfirmDialog } from './ConfirmDialog';
import { StatusPill } from './StatusPill';
import { usePageStatuses } from './usePageStatuses';

interface LibraryPageProps {
  isAdmin: boolean;
  /** Tăng lên khi có thay đổi ở nơi khác (vừa tải ảnh, vừa tạo truyện...) để trang tải lại. */
  refreshKey: number;
  onOpenUpload: () => void;
  onOpenReader: (target: ReaderTarget) => void;
  onOpenManager: (seriesId: number | null) => void;
  onNavigateToFlashcards: () => void;
  /** Mở Cài đặt tài khoản ở mục Học tập để chỉnh mục tiêu trang mỗi tuần (F02.02). */
  onOpenLearningSettings: () => void;
  showToast: (message: string) => void;
}

type TabKey = LibraryTab | 'uploads' | 'bookmarks';
type SortKey = 'recent' | 'hsk' | 'progress';

const SERIES_TABS: LibraryTab[] = ['all', 'reading', 'favorites', 'completed'];
const DEFAULT_GOAL_DISPLAY = { current: 3, target: 4 };

export const LibraryPage: React.FC<LibraryPageProps> = ({
  isAdmin,
  refreshKey,
  onOpenUpload,
  onOpenReader,
  onOpenManager,
  onNavigateToFlashcards,
  onOpenLearningSettings,
  showToast
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('all');
  const [viewStyle, setViewStyle] = useState<'grid' | 'list'>('grid');
  const [sortOption, setSortOption] = useState<SortKey>('recent');
  const [lists, setLists] = useState<Record<LibraryTab, Paged<ApiSeries> | null>>({ all: null, reading: null, favorites: null, completed: null });
  const [uploads, setUploads] = useState<Paged<ApiPage> | null>(null);
  const [bookmarks, setBookmarks] = useState<Paged<BookmarkItem> | null>(null);
  const [mine, setMine] = useState<ApiSeries[]>([]);
  const [settings, setSettings] = useState<ApiSettings | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState<number>(0);
  const [busySeries, setBusySeries] = useState<number | null>(null);
  const [retrying, setRetrying] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ApiPage | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [vocabTotal, setVocabTotal] = useState<number | null>(null);

  const reload = useCallback(() => setReloadTick(value => value + 1), []);

  // Số từ trong Sổ tay lấy từ máy chủ (M07).
  useEffect(() => {
    let cancelled = false;
    countVocab()
      .then(total => {
        if (!cancelled) setVocabTotal(total);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      const [all, reading, favorites, completed, up, marks, own, config] = await Promise.allSettled([
        listLibrary('all'),
        listLibrary('reading'),
        listLibrary('favorites'),
        listLibrary('completed'),
        listQuickUploads(1, 24),
        listBookmarks(1, 50),
        listSeries({ scope: 'mine', size: 50 }),
        getSettings()
      ]);
      if (cancelled) return;
      if (all.status === 'rejected') {
        setError(errorMessage(all.reason));
      } else {
        setError(null);
        setLists({
          all: all.value,
          reading: reading.status === 'fulfilled' ? reading.value : null,
          favorites: favorites.status === 'fulfilled' ? favorites.value : null,
          completed: completed.status === 'fulfilled' ? completed.value : null
        });
      }
      if (up.status === 'fulfilled') setUploads(up.value);
      if (marks.status === 'fulfilled') setBookmarks(marks.value);
      if (own.status === 'fulfilled') setMine(own.value.items);
      if (config.status === 'fulfilled') setSettings(config.value);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadTick, refreshKey]);

  const pendingUploadIds = (uploads?.items ?? []).filter(page => page.status === 'queued' || page.status === 'running').map(page => page.id);
  const { statuses: liveStatuses, restart } = usePageStatuses(pendingUploadIds, true);

  const percentOf = (series: ApiSeries): number => Math.min(100, Math.max(0, series.progress?.percent ?? 0));
  const isFinished = (series: ApiSeries): boolean => Boolean(series.progress?.completed) || percentOf(series) >= 100;

  const seriesTab: LibraryTab = SERIES_TABS.includes(activeTab as LibraryTab) ? (activeTab as LibraryTab) : 'all';
  const shownSeries = useMemo(() => {
    const items = [...(lists[seriesTab]?.items ?? [])];
    const lastTouched = (series: ApiSeries) => series.progress?.updated_at ?? series.updated_at;
    if (sortOption === 'recent') items.sort((a, b) => lastTouched(b).localeCompare(lastTouched(a)));
    if (sortOption === 'hsk') items.sort((a, b) => (a.est_hsk_level ?? 99) - (b.est_hsk_level ?? 99));
    if (sortOption === 'progress') items.sort((a, b) => percentOf(b) - percentOf(a));
    return items;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lists, seriesTab, sortOption]);

  const handleRead = async (series: ApiSeries, restart: boolean) => {
    const resume = series.progress;
    if (resume?.chapter_id != null && resume.page_no != null && !restart) {
      onOpenReader({ chapterId: resume.chapter_id, pageNo: resume.page_no, pageId: resume.page_id ?? undefined });
      return;
    }
    setBusySeries(series.id);
    try {
      const target = pickReadTarget(await getSeries(series.id), { restart });
      if (target) onOpenReader(target);
      else showToast('Truyện này chưa có trang nào để đọc.');
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusySeries(null);
    }
  };

  const handleFavorite = async (series: ApiSeries) => {
    try {
      await setFavorite(series.id, !series.is_favorite);
      showToast(series.is_favorite ? 'Đã bỏ khỏi Yêu thích.' : 'Đã thêm vào Yêu thích!');
      reload();
    } catch (err) {
      showToast(errorMessage(err));
    }
  };

  const handleRetranslate = async (pageId: number) => {
    setRetrying(pageId);
    try {
      await retranslatePage(pageId);
      restart(pageId);
      showToast('Đã gửi yêu cầu dịch lại, ảnh đang xếp hàng.');
      reload();
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setRetrying(null);
    }
  };

  // Xóa ảnh tải nhanh (F03.09): máy chủ xóa cả ảnh gốc và bản dịch.
  const handleDeleteUpload = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deletePage(pendingDelete.id);
      setUploads(current =>
        current ? { ...current, items: current.items.filter(item => item.id !== pendingDelete.id), total: Math.max(0, current.total - 1) } : current
      );
      showToast('Đã xóa ảnh tải lên.');
      setPendingDelete(null);
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  const openUploadedPage = (page: ApiPage) => onOpenReader({ chapterId: page.chapter_id, pageId: page.id, pageNo: page.page_no });

  const count = (tab: LibraryTab) => lists[tab]?.total ?? 0;
  const weeklyGoal = settings?.weekly_page_goal ?? null;
  const goalDisplay = weeklyGoal === null ? DEFAULT_GOAL_DISPLAY : { current: 0, target: weeklyGoal };
  const goalPercent = Math.min(100, Math.round((goalDisplay.current / Math.max(1, goalDisplay.target)) * 100));

  const tabButton = (key: TabKey, label: string) => (
    <button
      key={key}
      onClick={() => setActiveTab(key)}
      className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
        activeTab === key
          ? 'bg-[#f472b6] text-white shadow-xs'
          : 'text-slate-600 hover:text-slate-900'
      }`}
    >
      {label}
    </button>
  );

  const renderUploadCard = (page: ApiPage) => {
    const live = liveStatuses[page.id];
    const status = live ? live.status : page.status;
    const failure = live?.error_message ?? page.error_message;
    return (
      <div key={page.id} className="group relative rounded-2xl bg-white p-3 shadow-xs border border-pink-100 hover:shadow-md transition-all flex flex-col">
        <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-slate-100">
          <AuthImage
            src={page.original_url}
            alt={`Ảnh tải lên ${page.id}`}
            className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-300"
          />
          <div className="absolute inset-0 bg-[#a43073]/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <button
              onClick={() => openUploadedPage(page)}
              className="px-4 py-1.5 rounded-full bg-white text-[#a43073] font-bold text-xs shadow-md flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[16px]">visibility</span>
              <span>{status === 'done' ? 'Mở bản dịch' : 'Xem ảnh'}</span>
            </button>
          </div>
          {page.can_edit && (
            <button
              onClick={() => setPendingDelete(page)}
              className="absolute top-1.5 right-1.5 w-7 h-7 rounded-full bg-white/90 text-red-600 hover:bg-red-50 shadow-md flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
              aria-label="Xóa ảnh tải lên"
              title="Xóa ảnh tải lên"
            >
              <span className="material-symbols-outlined text-[16px]">delete</span>
            </button>
          )}
        </div>
        <div className="flex flex-col mt-2 gap-1">
          <span className="font-bold text-xs text-slate-800 truncate">Ảnh tải lên · {timeAgo(page.created_at)}</span>
          <StatusPill status={status} />
          {status === 'failed' && (
            <>
              <span className="text-[10px] text-red-600 line-clamp-2">{failure ?? 'Xử lý ảnh không thành công.'}</span>
              <button
                onClick={() => handleRetranslate(page.id)}
                disabled={retrying === page.id}
                className="self-start px-2.5 py-1 rounded-full bg-white border border-red-200 text-red-700 text-[10px] font-bold hover:bg-red-50 disabled:opacity-60"
              >
                {retrying === page.id ? 'Đang gửi...' : 'Dịch lại'}
              </button>
            </>
          )}
          {page.expires_at && (
            <span className="text-[10px] text-slate-400">Lưu đến {new Date(page.expires_at).toLocaleDateString('vi-VN')}</span>
          )}
        </div>
      </div>
    );
  };

  const dropzoneTile = (
    <div
      onClick={onOpenUpload}
      className="group relative rounded-2xl bg-[#eff4ff] p-5 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-[#dce9ff] transition-all border-2 border-dashed border-pink-200 min-h-[12rem]"
    >
      <div className="w-14 h-14 rounded-2xl bg-white shadow-xs flex items-center justify-center text-[#a43073] group-hover:scale-110 transition-transform mb-2">
        <span className="material-symbols-outlined text-[28px]">add_photo_alternate</span>
      </div>
      <span className="font-bold text-sm text-slate-800">Thêm ảnh trang mới</span>
      <p className="text-[11px] text-slate-500 mt-1 max-w-[180px]">
        Kéo thả hoặc bấm để tải lên ảnh manhua cần dịch
      </p>
      <span className="mt-3 px-2.5 py-0.5 rounded-full bg-white text-slate-500 text-[10px] font-medium border border-slate-200">
        PNG, JPG, WEBP tối đa 10MB
      </span>
    </div>
  );

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-10">

      {/* HERO HEADER & STATS BENTO */}
      <section className="relative overflow-hidden rounded-3xl bg-[#eff4ff] p-6 sm:p-10 shadow-soft border border-pink-100">
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-pink-100/50 blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full bg-blue-100/50 blur-3xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex flex-col max-w-2xl">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] font-bold text-xs tracking-wide flex items-center gap-1 shadow-xs">
                🌸 KHÔNG GIAN HỌC TẬP CÁ NHÂN
              </span>
              <span className="text-slate-500 text-xs hidden sm:inline">HSK 1 - HSK 4</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans']">
              Thư Viện Học Tập Của Bạn
            </h1>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Mỗi trang truyện là một bước tiến mới. Khám phá kho manhua có chú âm Pinyin, tích lũy từ vựng tự nhiên và tiếp tục hành trình chinh phục tiếng Trung hôm nay!
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <button
              onClick={() => onOpenManager(null)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-white text-[#a43073] font-bold text-xs sm:text-sm border border-pink-200 shadow-xs hover:bg-pink-50 transition-all"
            >
              <span className="material-symbols-outlined text-[18px]">library_add</span>
              <span>Tạo truyện mới</span>
            </button>
            <button
              onClick={onOpenUpload}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-pink-500 to-rose-400 text-white font-bold text-xs sm:text-sm shadow-md shadow-pink-300/30 hover:scale-105 transition-all"
            >
              <span className="material-symbols-outlined text-[18px]">add_photo_alternate</span>
              <span>+ Tải lên trang truyện mới</span>
            </button>
          </div>
        </div>

        {/* Quick Stats Metrics Bento */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 bg-white/90 backdrop-blur-md rounded-2xl p-4 shadow-sm border border-pink-100/60">
          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-pink-100 flex items-center justify-center text-[#a43073]">
              <span className="material-symbols-outlined text-[24px]">collections_bookmark</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">{count('all')}</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Bộ truyện đã lưu</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center text-[#0060ac]">
              <span className="material-symbols-outlined text-[24px]">auto_stories</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">{count('reading')}</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Bộ đang đọc dở</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center text-amber-800">
              <span className="material-symbols-outlined text-[24px]">style</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">{vocabTotal ?? '–'}</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Từ vựng đã lưu</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-700">
              <span className="material-symbols-outlined text-[24px]">task_alt</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">{count('completed')}</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Bộ đã hoàn thành</span>
            </div>
          </div>
        </div>
      </section>

      {/* FILTER & SORT CONTROLS */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">

        {/* Tabs Filter */}
        <div className="flex items-center gap-1 overflow-x-auto p-1 bg-[#eff4ff] rounded-full custom-scrollbar">
          {tabButton('all', `Tất cả (${count('all')})`)}
          {tabButton('reading', `Đang đọc dở (${count('reading')})`)}
          {tabButton('favorites', `Yêu thích (${count('favorites')})`)}
          {tabButton('completed', `Đã xong (${count('completed')})`)}
          {tabButton('uploads', `Tải lên của tôi (${uploads?.total ?? 0})`)}
          {tabButton('bookmarks', `Trang đã lưu (${bookmarks?.total ?? 0})`)}
        </div>

        {/* Sort & Grid/List View Controls */}
        <div className="flex items-center gap-3 self-end md:self-auto">
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full shadow-xs border border-pink-100">
            <span className="material-symbols-outlined text-[16px] text-slate-400">sort</span>
            <label className="text-xs text-slate-500" htmlFor="library-sort">
              Sắp xếp:
            </label>
            <select
              id="library-sort"
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value as SortKey)}
              className="bg-transparent text-xs font-semibold text-slate-700 outline-none cursor-pointer"
            >
              <option value="recent">Gần đây nhất</option>
              <option value="hsk">HSK tăng dần</option>
              <option value="progress">Tiến độ cao nhất</option>
            </select>
          </div>

          <div className="hidden sm:flex items-center bg-white p-1 rounded-full shadow-xs border border-pink-100">
            <button
              onClick={() => setViewStyle('grid')}
              className={`p-1 rounded-full transition-colors ${
                viewStyle === 'grid' ? 'bg-pink-100 text-[#a43073]' : 'text-slate-400 hover:text-slate-700'
              }`}
              title="Dạng lưới"
            >
              <span className="material-symbols-outlined text-[18px]">grid_view</span>
            </button>
            <button
              onClick={() => setViewStyle('list')}
              className={`p-1 rounded-full transition-colors ${
                viewStyle === 'list' ? 'bg-pink-100 text-[#a43073]' : 'text-slate-400 hover:text-slate-700'
              }`}
              title="Dạng danh sách"
            >
              <span className="material-symbols-outlined text-[18px]">view_list</span>
            </button>
          </div>
        </div>

      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center text-sm text-red-700">
          <p>{error}</p>
          <button onClick={reload} className="mt-3 px-4 py-2 rounded-full bg-white text-red-700 text-xs font-bold border border-red-200 hover:bg-red-100">
            Thử lại
          </button>
        </div>
      )}

      {/* MAIN AREA: danh sách theo tab */}
      {activeTab === 'uploads' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {(uploads?.items ?? []).map(renderUploadCard)}
          {dropzoneTile}
        </div>
      ) : activeTab === 'bookmarks' ? (
        (bookmarks?.items.length ?? 0) === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-pink-200 p-10 text-center flex flex-col items-center gap-2">
            <span className="material-symbols-outlined text-[40px] text-pink-300">bookmark</span>
            <p className="text-sm font-bold text-slate-700">Bạn chưa lưu trang nào</p>
            <p className="text-xs text-slate-500">Khi đọc truyện, bấm biểu tượng dấu trang để lưu lại những trang yêu thích.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {bookmarks?.items.map(item => (
              <button
                key={item.page_id}
                onClick={() => onOpenReader({ chapterId: item.chapter_id, pageId: item.page_id, pageNo: item.page_no })}
                className="text-left rounded-2xl bg-white p-3 shadow-xs border border-pink-100 hover:shadow-md transition-all flex flex-col"
              >
                <AuthImage src={item.original_url} alt={`Trang ${item.page_no}`} className="w-full aspect-[3/4] object-cover object-top rounded-xl" />
                <span className="font-bold text-xs text-slate-800 truncate mt-2">{item.series_title ?? 'Ảnh tải lên'}</span>
                <span className="text-[11px] text-slate-500">
                  {item.chapter_number !== null ? `Chương ${formatChapterNumber(item.chapter_number)} · ` : ''}Trang {item.page_no}
                </span>
                <span className="text-[10px] text-slate-400">Lưu {timeAgo(item.bookmarked_at).toLowerCase()}</span>
              </button>
            ))}
          </div>
        )
      ) : loading && !lists.all ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[0, 1, 2].map(index => (
            <div key={index} className="rounded-2xl bg-white border border-pink-100 animate-pulse h-96"></div>
          ))}
        </div>
      ) : shownSeries.length === 0 ? (
        <div className="bg-white rounded-2xl border border-dashed border-pink-200 p-10 text-center flex flex-col items-center gap-2">
          <span className="material-symbols-outlined text-[40px] text-pink-300">collections_bookmark</span>
          <p className="text-sm font-bold text-slate-700">
            {seriesTab === 'all' ? 'Thư viện của bạn còn trống' : 'Chưa có truyện nào trong mục này'}
          </p>
          <p className="text-xs text-slate-500">
            {seriesTab === 'all'
              ? 'Vào Trang Chủ và bấm “Lưu vào Thư viện” ở truyện bạn thích, hoặc tạo truyện riêng của bạn.'
              : 'Truyện sẽ tự xuất hiện ở đây khi bạn đọc, yêu thích hoặc đọc xong.'}
          </p>
        </div>
      ) : (
        <div className={viewStyle === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'flex flex-col gap-4'}>
          {shownSeries.map((comic) => {
            const resume = comic.progress;
            const percent = percentOf(comic);
            const finished = isFinished(comic);
            const started = (resume?.pages_read ?? 0) > 0;
            return (
              <div
                key={comic.id}
                className="group relative flex flex-col rounded-2xl bg-white p-4 shadow-soft border border-pink-100 hover:shadow-md transition-all duration-300"
              >
                {/* Card Cover */}
                <div className="relative w-full h-52 rounded-xl overflow-hidden bg-slate-100">
                  <AuthImage
                    src={comic.cover_url}
                    alt={comic.title_vi}
                    className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
                    fallback={<span className="material-symbols-outlined text-[40px]">auto_stories</span>}
                  />
                  <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
                    <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 text-xs font-bold shadow-xs">
                      {hskLabel(comic.est_hsk_level)}
                    </span>
                    {comic.genres[0] && (
                      <span className="px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-900 text-xs font-medium shadow-xs">
                        {comic.genres[0]}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleFavorite(comic)}
                    className="absolute top-2.5 right-2.5 w-8 h-8 rounded-full bg-white/85 backdrop-blur-md text-[#a43073] hover:bg-white flex items-center justify-center shadow-xs transition-transform hover:scale-110"
                    title={comic.is_favorite ? 'Bỏ yêu thích' : 'Yêu thích'}
                    aria-pressed={comic.is_favorite}
                  >
                    <span className="material-symbols-outlined text-[18px]" style={comic.is_favorite ? { fontVariationSettings: "'FILL' 1" } : undefined}>
                      favorite
                    </span>
                  </button>
                  <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-900/85 via-slate-900/30 to-transparent p-3 flex items-end justify-between">
                    <span className="text-white text-xs font-bold flex items-center gap-1">
                      <span className="material-symbols-outlined text-[16px]">menu_book</span>
                      {finished ? 'Đã đọc xong' : started ? (resume?.page_no != null ? `Trang ${resume.page_no}/${resume.total_pages ?? '?'} (${percent}%)` : `${resume?.pages_read}/${resume?.pages_total} trang (${percent}%)`) : 'Chưa bắt đầu'}
                    </span>
                    <span className="text-white/90 text-[11px]">
                      {started && resume?.updated_at ? `Đọc ${timeAgo(resume.updated_at).toLowerCase()}` : ''}
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${finished ? 'bg-emerald-500' : 'bg-[#a43073]'}`}
                    style={{ width: `${percent}%` }}
                  ></div>
                </div>

                {/* Card Info */}
                <div className="flex flex-col mt-3 flex-1 justify-between">
                  <div>
                    <h3 className="font-bold text-base text-slate-800 group-hover:text-[#a43073] transition-colors">
                      {comic.title_vi}{comic.title_zh ? ` (${comic.title_zh})` : ''}
                    </h3>
                    <p className="text-xs text-slate-500 line-clamp-2 mt-1 leading-relaxed">
                      {comic.description || 'Truyện chưa có mô tả.'}
                    </p>
                  </div>

                  {/* Vocab Tag */}
                  <div className="flex items-center gap-3 mt-3 py-1.5 px-3 rounded-xl bg-slate-50">
                    <div className="flex items-center gap-1 text-[#a43073] text-xs font-bold">
                      <span className="material-symbols-outlined text-[15px]">translate</span>
                      <span>{comic.chapter_count} chương</span>
                    </div>
                    <div className="text-slate-500 text-[11px] truncate">
                      {started && resume?.chapter_number != null
                        ? `Chương ${formatChapterNumber(resume.chapter_number)}`
                        : comic.visibility === 'private' ? 'Truyện riêng tư' : 'Truyện công khai'}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 gap-2.5 mt-4 pt-1">
                    <button
                      onClick={() => handleRead(comic, finished)}
                      disabled={busySeries === comic.id}
                      className="flex items-center justify-center gap-1 py-2 px-3 rounded-full bg-[#a43073] text-white text-xs font-bold shadow-xs hover:bg-[#85145a] transition-all disabled:opacity-60"
                    >
                      <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                      <span>{finished ? 'Đọc lại' : started ? 'Đọc tiếp' : 'Bắt đầu đọc'}</span>
                    </button>
                    <button
                      onClick={onNavigateToFlashcards}
                      className="flex items-center justify-center gap-1 py-2 px-3 rounded-full bg-blue-100 text-blue-900 text-xs font-bold hover:bg-blue-200 transition-all"
                    >
                      <span className="material-symbols-outlined text-[16px]">style</span>
                      <span>Ôn thẻ</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* SECTION: TRUYỆN DO TÔI TẠO */}
      {activeTab !== 'uploads' && activeTab !== 'bookmarks' && (
        <section className="flex flex-col gap-4 -mt-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">Truyện Do Bạn Tạo</h2>
              <p className="text-xs text-slate-500 mt-1 max-w-2xl">
                Tạo truyện riêng, thêm chương và tải ảnh từng trang để hệ thống dịch.{isAdmin ? ' Quản trị viên có thể đăng truyện công khai.' : ''}
              </p>
            </div>
            <button
              onClick={() => onOpenManager(null)}
              className="flex items-center gap-2 self-start sm:self-auto px-4 py-2 rounded-full bg-white text-[#a43073] text-xs font-bold shadow-xs border border-pink-100 hover:bg-pink-50 transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">library_add</span>
              <span>Tạo truyện mới</span>
            </button>
          </div>
          {mine.length === 0 ? (
            <p className="text-xs text-slate-500 bg-white rounded-2xl border border-dashed border-pink-200 p-5 text-center">Bạn chưa tạo truyện nào.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {mine.map(series => (
                <div key={series.id} className="rounded-2xl bg-white p-3 shadow-xs border border-pink-100 flex flex-col gap-2">
                  <AuthImage src={series.cover_url} alt={series.title_vi} className="w-full h-32 object-cover rounded-xl" fallback={<span className="material-symbols-outlined text-[32px]">auto_stories</span>} />
                  <span className="font-bold text-xs text-slate-800 truncate">{series.title_vi}</span>
                  <span className="text-[11px] text-slate-500">
                    {series.chapter_count} chương · {series.visibility === 'public' ? 'Công khai' : 'Riêng tư'}
                  </span>
                  <button
                    onClick={() => onOpenManager(series.id)}
                    className="self-start px-3 py-1 rounded-full bg-blue-50 text-blue-800 text-[11px] font-bold hover:bg-blue-100"
                  >
                    Quản lý chương
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* SECTION: UPLOADED MANHUA & OCR AI TRANSLATION WORKSPACE */}
      {activeTab !== 'uploads' && (
        <section className="flex flex-col gap-4 mt-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
                  Trang Ảnh Bạn Đã Tải Lên Dịch
                </h2>
                <span className="px-2.5 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-xs font-bold">
                  OCR AI
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1 max-w-2xl">
                Tự do chụp hoặc tải lên bất kỳ trang manhua Trung Quốc nào từ Pinterest, Weibo. Hệ thống tự động nhận diện chữ Hán, phiên âm Pinyin và dịch tiếng Việt khi đến lượt xử lý.
              </p>
            </div>

            <button
              onClick={onOpenUpload}
              className="flex items-center gap-2 self-start sm:self-auto px-4 py-2 rounded-full bg-white text-[#a43073] text-xs font-bold shadow-xs border border-pink-100 hover:bg-pink-50 transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">cloud_upload</span>
              <span>Tải file ảnh (.jpg, .png)</span>
            </button>
          </div>

          {/* Uploads Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {(uploads?.items ?? []).slice(0, 3).map(renderUploadCard)}
            {dropzoneTile}
          </div>
        </section>
      )}

      {/* READING HABIT & WEEKLY GOAL WIDGET */}
      <section className="rounded-3xl bg-gradient-to-r from-white via-[#eff4ff] to-white p-6 sm:p-8 shadow-soft border border-pink-100 flex flex-col lg:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-5">

          {/* Circular Progress Ring */}
          <div className="relative w-20 h-20 shrink-0 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-slate-200"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="3.5"
              />
              <path
                className="text-[#a43073]"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeDasharray={`${goalPercent}, 100`}
                strokeLinecap="round"
                strokeWidth="3.5"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-sm font-extrabold text-slate-800 leading-none">{goalPercent}%</span>
              <span className="text-[9px] text-slate-500 font-medium">Mục tiêu</span>
            </div>
          </div>

          <div className="flex flex-col">
            <h3 className="text-base sm:text-lg font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
              {weeklyGoal === null
                ? 'Mục Tiêu Đọc Tuần Này: 3 / 4 Chương Manhua'
                : `Mục Tiêu Đọc Tuần Này: ${goalDisplay.current} / ${goalDisplay.target} Trang`}
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              {weeklyGoal === null
                ? 'Bạn đã ôn tập 85 từ vựng mới trong tuần qua! Hãy hoàn thành 1 chương nữa để nhận huy hiệu "Mọt Truyện Siêng Năng" 🌸 (số liệu minh họa)'
                : 'Mục tiêu lấy từ Cài đặt của bạn. Số trang đã đọc trong tuần sẽ được thống kê ở bản cập nhật tới.'}
            </p>
            <button
              onClick={onOpenLearningSettings}
              className="mt-1.5 self-start text-[11px] font-bold text-[#a43073] hover:underline flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[14px]">tune</span>
              Chỉnh mục tiêu học tập
            </button>
          </div>
        </div>

        <button
          onClick={onNavigateToFlashcards}
          className="shrink-0 px-6 py-2.5 rounded-full bg-[#0060ac] hover:bg-[#004883] text-white font-bold text-xs sm:text-sm shadow-md transition-all flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-[18px]">school</span>
          <span>Vào phòng ôn tập từ vựng</span>
        </button>
      </section>

      {pendingDelete && (
        <ConfirmDialog
          title="Xóa ảnh tải lên?"
          message="Ảnh gốc và bản dịch của trang này sẽ bị xóa vĩnh viễn. Thao tác không thể hoàn tác."
          confirmLabel="Xóa ảnh"
          busy={deleting}
          onConfirm={handleDeleteUpload}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
};
