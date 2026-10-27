import React, { useCallback, useEffect, useState } from 'react';
import { speakChinese } from '../utils/speech';
import { WordOfTheDay, getWordOfTheDay, hskLabel } from '../api/dictionary';
import { isAlreadySaved, saveResultMessage, saveWord } from '../api/vocab';
import { useInNotebook } from '../utils/useInNotebook';
import { useStreak } from '../utils/useStreak';
import { errorMessage, isAbortedError } from '../api/client';
import {
  ApiSeries,
  ContinueItem,
  Paged,
  SeriesDetail,
  addToLibrary,
  getSeries,
  listContinueReading,
  listSeries,
  pickReadTarget,
  removeFromLibrary
} from '../api/library';
import { ReaderTarget } from '../types';
import { formatChapterNumber, timeAgo } from '../utils/format';
import { AuthImage } from './AuthImage';
import { SeriesDetailModal } from './SeriesDetailModal';
import { TodayPanel } from './TodayPanel';

interface CatalogPageProps {
  isLoggedIn: boolean;
  onOpenReader: (target: ReaderTarget) => void;
  onRequireLogin: (message: string) => void;
  onNavigateToFlashcards: () => void;
  onLookupWord: (term: string) => void;
  showToast: (message: string) => void;
  /** Tăng lên khi dữ liệu ở nơi khác thay đổi (vd. vừa tải ảnh) để trang tải lại. */
  refreshKey?: number;
}

const PAGE_SIZE = 8;
const SEARCH_DEBOUNCE_MS = 400;
const HSK_FILTERS: { level: number; dot: string }[] = [
  { level: 1, dot: 'bg-emerald-500' },
  { level: 2, dot: 'bg-emerald-500' },
  { level: 3, dot: 'bg-blue-500' },
  { level: 4, dot: 'bg-blue-500' },
  { level: 5, dot: 'bg-pink-500' },
  { level: 6, dot: 'bg-pink-500' },
  { level: 7, dot: 'bg-amber-500' },
  { level: 8, dot: 'bg-amber-500' },
  { level: 9, dot: 'bg-amber-500' }
];

export const CatalogPage: React.FC<CatalogPageProps> = ({
  isLoggedIn,
  onOpenReader,
  onRequireLogin,
  onNavigateToFlashcards,
  onLookupWord,
  showToast,
  refreshKey = 0
}) => {
  const { streak } = useStreak();
  const [selectedHsk, setSelectedHsk] = useState<number | null>(null);
  const [genre, setGenre] = useState<string>('');
  const [knownGenres, setKnownGenres] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedQuery, setDebouncedQuery] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [result, setResult] = useState<Paged<ApiSeries> | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState<number>(0);
  const [continueItems, setContinueItems] = useState<ContinueItem[]>([]);
  const [featured, setFeatured] = useState<SeriesDetail | null>(null);
  const [featuredLoading, setFeaturedLoading] = useState<boolean>(true);
  const [heroBusy, setHeroBusy] = useState<boolean>(false);
  const [openSeriesId, setOpenSeriesId] = useState<number | null>(null);
  // Từ vựng trong ngày lấy từ API (M06); lỗi hoặc đang tải thì giữ nội dung mặc định.
  const [dailyWord, setDailyWord] = useState<WordOfTheDay | null>(null);
  const [dailyInNotebook, markDailySaved] = useInNotebook(dailyWord?.term ?? null, isLoggedIn);
  const [savingDaily, setSavingDaily] = useState<boolean>(false);

  useEffect(() => {
    let cancelled = false;
    getWordOfTheDay()
      .then(word => {
        if (!cancelled) setDailyWord(word);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // Tìm kiếm có độ trễ để không gọi API sau mỗi phím gõ.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listSeries({ scope: 'public', q: debouncedQuery, hsk: selectedHsk, genre, page, size: PAGE_SIZE }, controller.signal)
      .then(data => {
        setResult(data);
        setError(null);
        setKnownGenres(current => Array.from(new Set([...current, ...data.items.flatMap(item => item.genres)])).sort());
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [debouncedQuery, selectedHsk, genre, page, reloadTick, refreshKey]);

  // "Tiếp tục đọc dở" và truyện nổi bật ở đầu trang: ưu tiên truyện người dùng đang đọc.
  const loadFeatured = useCallback(async (signal?: AbortSignal) => {
    setFeaturedLoading(true);
    try {
      const items = isLoggedIn ? await listContinueReading(6) : [];
      if (signal?.aborted) return;
      setContinueItems(items);
      const featuredId = items[0]?.series_id ?? (await listSeries({ scope: 'public', size: 1 }, signal)).items[0]?.id;
      if (featuredId === undefined) {
        setFeatured(null);
        return;
      }
      const detail = await getSeries(featuredId, signal);
      if (!signal?.aborted) setFeatured(detail);
    } catch (err) {
      if (!isAbortedError(err)) setFeatured(null);
    } finally {
      if (!signal?.aborted) setFeaturedLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    const controller = new AbortController();
    void loadFeatured(controller.signal);
    return () => controller.abort();
  }, [loadFeatured, refreshKey]);

  const handlePlayWord = (text: string) => {
    speakChinese(text, 0.9);
  };

  const dailyTerm = dailyWord?.term ?? '临近';
  const totalPages = result ? Math.max(1, Math.ceil(result.total / PAGE_SIZE)) : 1;
  const hasFilter = debouncedQuery.trim() !== '' || selectedHsk !== null || genre !== '';

  const heroSeries = featured?.series ?? null;
  const heroFinished = Boolean(featured?.series.progress?.completed);
  const heroTarget = featured ? pickReadTarget(featured, { guest: !isLoggedIn, restart: heroFinished }) : null;

  const handleHeroRead = () => {
    if (!featured) return;
    if (!heroTarget) {
      showToast(isLoggedIn ? 'Truyện này chưa có trang nào để đọc.' : 'Truyện này chưa có chương dùng thử cho Khách.');
      return;
    }
    onOpenReader(heroTarget);
  };

  // Từ trong ngày lưu vào Sổ tay như một lượt tra cứu, không có ảnh ngữ cảnh (F07.01).
  const handleSaveDailyWord = async () => {
    if (!dailyWord) return;
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để lưu từ vào Sổ tay của bạn!');
      return;
    }
    setSavingDaily(true);
    try {
      showToast(saveResultMessage(dailyWord.term, await saveWord({ term: dailyWord.term, source: 'lookup' })));
      markDailySaved();
    } catch (err) {
      if (isAlreadySaved(err)) markDailySaved();
      showToast(isAlreadySaved(err) ? 'Từ này đã có với ngữ cảnh này' : errorMessage(err));
    } finally {
      setSavingDaily(false);
    }
  };

  const handleHeroLibrary = async () => {
    if (!heroSeries) return;
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để lưu truyện vào Thư viện của bạn!');
      return;
    }
    setHeroBusy(true);
    try {
      if (heroSeries.in_library) {
        await removeFromLibrary(heroSeries.id);
        showToast('Đã bỏ truyện khỏi Thư viện.');
      } else {
        await addToLibrary(heroSeries.id);
        showToast('Đã lưu truyện vào Thư viện của bạn!');
      }
      const detail = await getSeries(heroSeries.id);
      setFeatured(detail);
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setHeroBusy(false);
    }
  };

  const continueTarget = (item: ContinueItem): ReaderTarget => ({
    chapterId: item.chapter_id,
    pageNo: item.page_no,
    pageId: item.page_id ?? undefined
  });

  const chapterLabel = heroFinished
    ? 'Đọc lại'
    : featured?.progress
    ? `Đọc tiếp Chương ${formatChapterNumber(featured.progress.chapter_number)}`
    : 'Bắt đầu đọc';

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6">

      {/* HERO BANNER SECTION: truyện đang đọc dở, hoặc truyện công khai đầu tiên */}
      <section className="relative overflow-hidden rounded-3xl bg-white p-6 sm:p-10 shadow-soft border border-pink-100 mb-10">
        <div className="absolute -top-24 -left-20 w-80 h-80 bg-pink-100/60 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-10 right-1/3 w-72 h-72 bg-blue-100/50 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">

          {/* Left Hero Content */}
          <div className="lg:col-span-7 flex flex-col gap-4">

            {/* Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-semibold text-xs flex items-center gap-1 shadow-xs">
                <span>⭐</span> {heroSeries ? hskLabel(heroSeries.est_hsk_level) : 'Học qua truyện tranh'}
              </span>
              <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-800 font-semibold text-xs flex items-center gap-1 shadow-xs">
                <span className="material-symbols-outlined text-[15px]">translate</span>
                Pinyin + Dịch Tương Tác
              </span>
              <span className="px-3 py-1 rounded-full bg-pink-100 text-[#a43073] font-semibold text-xs flex items-center gap-1 shadow-xs">
                <span className="material-symbols-outlined text-[15px]">record_voice_over</span>
                Giọng Đọc Bản Xứ
              </span>
            </div>

            {featuredLoading ? (
              <div className="flex flex-col gap-3 animate-pulse" aria-label="Đang tải truyện nổi bật">
                <div className="h-4 w-40 rounded bg-slate-100"></div>
                <div className="h-9 w-3/4 rounded bg-slate-100"></div>
                <div className="h-16 w-full max-w-xl rounded bg-slate-100"></div>
              </div>
            ) : heroSeries ? (
              <>
                {/* Title */}
                <div>
                  <div className="text-sm font-['Noto_Serif_SC'] font-bold text-pink-600 mb-1 flex items-center gap-2">
                    {heroSeries.title_zh && <span>{heroSeries.title_zh}</span>}
                    {heroSeries.est_hsk_level !== null && (
                      <span className="px-2 py-0.5 rounded text-[11px] bg-pink-50 text-[#a43073] border border-pink-200">
                        {hskLabel(heroSeries.est_hsk_level)}
                      </span>
                    )}
                  </div>
                  <h1 className="text-3xl sm:text-4xl font-extrabold text-[#a43073] tracking-tight font-['Plus_Jakarta_Sans']">
                    {heroSeries.title_vi}
                  </h1>
                </div>

                <p className="text-sm text-slate-600 leading-relaxed max-w-xl line-clamp-4">
                  {heroSeries.description || 'Chọn một chương để bắt đầu đọc, rê chuột vào bóng thoại để xem Pinyin, nghĩa tiếng Việt và tra từ.'}
                </p>

                {/* CTAs */}
                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <button
                    onClick={handleHeroRead}
                    className="px-6 py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs sm:text-sm flex items-center gap-2 shadow-md shadow-pink-300/30 hover:scale-105 transition-all"
                  >
                    <span className="material-symbols-outlined text-[18px]">menu_book</span>
                    <span>{chapterLabel}</span>
                  </button>

                  <button
                    onClick={handleHeroLibrary}
                    disabled={heroBusy}
                    className="px-5 py-2.5 rounded-full bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm border border-slate-200 flex items-center gap-2 shadow-xs transition-colors disabled:opacity-60"
                  >
                    <span className="material-symbols-outlined text-[18px]">{heroSeries.in_library ? 'bookmark_added' : 'bookmark_add'}</span>
                    <span>{heroSeries.in_library ? 'Đã lưu trong Thư viện' : 'Lưu vào Thư viện'}</span>
                  </button>

                  <span className="text-xs font-semibold text-slate-500 flex items-center gap-1 ml-1">
                    <span className="text-amber-500">★</span>{' '}
                    {heroSeries.rating_avg !== null
                      ? `${heroSeries.rating_avg.toFixed(1)} (${heroSeries.rating_count} đánh giá)`
                      : 'Chưa có đánh giá'}
                  </span>
                </div>
              </>
            ) : (
              <div className="flex flex-col gap-3">
                <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans']">
                  Học tiếng Trung qua <span className="text-[#a43073]">truyện tranh</span>
                </h1>
                <p className="text-sm text-slate-600 leading-relaxed max-w-xl">
                  Thư viện công khai chưa có truyện nào, quản trị viên sẽ sớm đăng truyện mới. Trong lúc chờ, bạn có thể tải lên ảnh trang truyện của riêng mình để hệ thống nhận diện chữ và dịch.
                </p>
              </div>
            )}

          </div>

          {/* Right Hero Comic Preview Card */}
          <div className="lg:col-span-5 flex justify-center">
            {heroSeries ? (
              <div
                onClick={() => setOpenSeriesId(heroSeries.id)}
                className="relative w-full max-w-sm rounded-2xl overflow-hidden shadow-floating border-2 border-pink-200 cursor-pointer group hover:scale-[1.02] transition-all"
              >
                <AuthImage
                  src={heroSeries.cover_url}
                  alt={heroSeries.title_vi}
                  className="w-full h-72 object-cover block"
                  fallback={<span className="material-symbols-outlined text-[56px]">auto_stories</span>}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent flex items-end justify-between p-4 text-white">
                  <div>
                    <span className="text-xs font-bold block">Chạm vào bóng thoại</span>
                    <span className="text-[10px] text-pink-200">Tra từ tức thì & nghe phát âm</span>
                  </div>
                  <span className="px-3 py-1 rounded-full bg-[#f472b6] text-white text-xs font-bold shadow-sm">
                    Xem truyện
                  </span>
                </div>
              </div>
            ) : (
              <div className="w-full max-w-sm h-72 rounded-2xl border-2 border-dashed border-pink-200 bg-pink-50/40 flex flex-col items-center justify-center text-center text-[#a43073] gap-2 p-6">
                <span className="material-symbols-outlined text-[48px]">auto_stories</span>
                <span className="text-sm font-bold">Chưa có truyện công khai</span>
                <span className="text-[11px] text-slate-500">Truyện do quản trị viên đăng sẽ hiện ở đây.</span>
              </div>
            )}
          </div>

        </div>
      </section>

      {/* Việc nên làm hôm nay (F12.04) */}
      <TodayPanel isLoggedIn={isLoggedIn} onRequireLogin={onRequireLogin} />

      {/* ROADMAP HEADER: grouped title and search, distinct from catalog content */}
      <section className="mb-6 rounded-3xl border border-blue-100 bg-gradient-to-r from-white via-white to-[#eff4ff] p-5 sm:p-7 shadow-soft">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="min-w-0">
          <span className="text-xs font-bold uppercase tracking-wider text-[#a43073]">
            Phân loại trình độ
          </span>
          <h2 className="text-2xl sm:text-[28px] font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
            Lộ Trình Đọc Theo Cấp Độ HSK
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-slate-500">
            Tìm truyện phù hợp với trình độ và mục tiêu học tập của bạn.
          </p>
          </div>

          {/* Search inside catalog */}
          <div className="relative w-full md:w-[min(100%,22rem)] shrink-0">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-[20px]">
            search
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên truyện hoặc từ khóa..."
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-white text-slate-800 text-sm shadow-xs border border-blue-100 outline-none focus:ring-2 focus:ring-[#f472b6] focus:border-pink-200 transition-all placeholder:text-slate-400"
          />
          </div>
        </div>
      </section>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 mb-4 custom-scrollbar">
        <button
          onClick={() => { setSelectedHsk(null); setPage(1); }}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
            selectedHsk === null
              ? 'bg-[#a43073] text-white shadow-sm'
              : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          Tất cả trình độ{selectedHsk === null && result && !hasFilter ? ` (${result.total})` : ''}
        </button>
        {HSK_FILTERS.map(({ level, dot }) => (
          <button
            key={level}
            onClick={() => { setSelectedHsk(level); setPage(1); }}
            title={level >= 7 ? 'HSK 3.0 cấp cao (nhóm 7–9)' : undefined}
            className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
              selectedHsk === level
                ? 'bg-[#a43073] text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${dot}`}></span>
            HSK {level}
          </button>
        ))}
      </div>

      {/* Genre filter */}
      {knownGenres.length > 0 && (
        <div className="flex items-center gap-2 mb-8 text-xs">
          <label htmlFor="catalog-genre" className="text-slate-500 font-medium">Thể loại:</label>
          <select
            id="catalog-genre"
            value={genre}
            onChange={(e) => { setGenre(e.target.value); setPage(1); }}
            className="bg-white border border-pink-100 rounded-full px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
          >
            <option value="">Tất cả thể loại</option>
            {knownGenres.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
      )}

      {/* MAIN TWO-COLUMN BODY: Catalog Left (8 cols), Widgets Right (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

        {/* LEFT COLUMN: LIST OF COMICS BY LEVEL (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-10">

          {/* SECTION: Tiếp tục đọc dở */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-pink-500">📖</span>
                <h3 className="text-lg font-bold text-slate-800">Tiếp Tục Đọc Dở</h3>
              </div>
              <span className="text-xs text-slate-400">Duy trì thói quen đọc 15 phút mỗi ngày</span>
            </div>

            {continueItems.length === 0 ? (
              <div className="bg-white p-6 rounded-2xl border border-dashed border-pink-200 text-center text-xs text-slate-500">
                {isLoggedIn
                  ? 'Bạn chưa đọc dở truyện nào. Chọn một truyện bên dưới để bắt đầu!'
                  : 'Đăng nhập để lưu tiến độ và tiếp tục đọc từ trang bạn đã dừng.'}
                {!isLoggedIn && (
                  <button
                    onClick={() => onRequireLogin('Vui lòng đăng nhập để lưu tiến độ đọc truyện!')}
                    className="ml-2 font-bold text-[#a43073] hover:underline"
                  >
                    Đăng nhập
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {continueItems.slice(0, 4).map(item => {
                  const percent = item.total_pages > 0 ? Math.min(100, Math.round((item.page_no / item.total_pages) * 100)) : 0;
                  return (
                    <div key={item.chapter_id} className="bg-white p-3.5 rounded-2xl shadow-xs border border-pink-100 flex gap-3 hover:shadow-md transition-all">
                      <AuthImage
                        src={item.cover_url}
                        alt={item.series_title}
                        className="w-20 h-28 object-cover rounded-xl shrink-0"
                        fallback={<span className="material-symbols-outlined text-[28px]">auto_stories</span>}
                      />
                      <div className="flex flex-col justify-between flex-1 min-w-0">
                        <div>
                          <div className="flex items-center justify-end gap-1">
                            <span className="text-[10px] text-slate-400">Đọc {timeAgo(item.updated_at).toLowerCase()}</span>
                          </div>
                          <h4 className="text-xs font-bold text-slate-800 truncate mt-1">{item.series_title}</h4>
                          <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                            Chương {formatChapterNumber(item.chapter_number)}
                            {item.chapter_title ? ` · ${item.chapter_title}` : ''}
                          </p>
                        </div>
                        <div>
                          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mb-1.5">
                            <div className="bg-[#a43073] h-full rounded-full" style={{ width: `${percent}%` }}></div>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-slate-400">Trang {item.page_no}/{item.total_pages}</span>
                            <button
                              onClick={() => onOpenReader(continueTarget(item))}
                              className="px-3 py-1 rounded-full bg-[#f472b6] text-white text-[11px] font-bold hover:bg-[#a43073] transition-colors"
                            >
                              Đọc ngay
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* SECTION: Catalog Cards Grid */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-500"></span>
                <h3 className="text-lg font-bold text-slate-800">Danh Mục Truyện Phù Hợp Trình Độ</h3>
              </div>
              <span className="text-xs text-slate-500">100% kèm Pinyin & dịch tương tác</span>
            </div>

            {error ? (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center text-sm text-red-700">
                <p>{error}</p>
                <button
                  onClick={() => setReloadTick(value => value + 1)}
                  className="mt-3 px-4 py-2 rounded-full bg-white text-red-700 text-xs font-bold border border-red-200 hover:bg-red-100"
                >
                  Thử lại
                </button>
              </div>
            ) : loading && !result ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {[0, 1, 2, 3].map(index => (
                  <div key={index} className="bg-white rounded-2xl p-4 border border-pink-100 animate-pulse h-80"></div>
                ))}
              </div>
            ) : result && result.items.length === 0 ? (
              <div className="bg-white rounded-2xl border border-dashed border-pink-200 p-10 text-center flex flex-col items-center gap-2">
                <span className="material-symbols-outlined text-[40px] text-pink-300">search_off</span>
                <p className="text-sm font-bold text-slate-700">
                  {hasFilter ? 'Không tìm thấy truyện phù hợp' : 'Chưa có truyện công khai nào'}
                </p>
                <p className="text-xs text-slate-500">
                  {hasFilter
                    ? 'Thử đổi từ khóa hoặc bỏ bớt bộ lọc trình độ, thể loại.'
                    : 'Quản trị viên chưa đăng truyện công khai. Bạn vẫn có thể tải ảnh của riêng mình để dịch.'}
                </p>
              </div>
            ) : (
              <>
                <div className={`grid grid-cols-1 sm:grid-cols-2 gap-6 transition-opacity ${loading ? 'opacity-60' : ''}`}>
                  {result?.items.map((comic) => (
                    <div
                      key={comic.id}
                      onClick={() => setOpenSeriesId(comic.id)}
                      className="bg-white rounded-2xl p-4 shadow-xs border border-pink-100 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between group"
                    >
                      <div>
                        <div className="relative w-full h-44 rounded-xl overflow-hidden mb-3 bg-slate-100">
                          <AuthImage
                            src={comic.cover_url}
                            alt={comic.title_vi}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            fallback={<span className="material-symbols-outlined text-[40px]">auto_stories</span>}
                          />
                          <span className="absolute top-2 left-2 px-2.5 py-0.5 rounded-full bg-white/90 backdrop-blur-md text-xs font-bold text-[#a43073] shadow-xs">
                            {hskLabel(comic.est_hsk_level)}
                          </span>
                          <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-slate-900/75 backdrop-blur-md text-[10px] font-medium text-white">
                            {comic.chapter_count} Chương
                          </span>
                        </div>

                        <h4 className="font-bold text-sm text-slate-800 group-hover:text-[#a43073] transition-colors">
                          {comic.title_vi}
                        </h4>
                        <span className="text-[11px] font-['Noto_Serif_SC'] text-pink-600 block mt-0.5">
                          {[comic.title_zh, comic.author].filter(Boolean).join(' • ') || 'Chưa rõ tác giả'}
                        </span>
                        <p className="text-xs text-slate-500 line-clamp-2 mt-2 leading-relaxed">
                          {comic.description || 'Truyện chưa có mô tả.'}
                        </p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <span className="text-[11px] text-slate-400 font-medium">
                          <span className="text-amber-500">★</span>{' '}
                          {comic.rating_avg !== null ? `${comic.rating_avg.toFixed(1)} (${comic.rating_count})` : 'Chưa có đánh giá'}
                        </span>
                        <span className="text-xs font-bold text-[#a43073] flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                          Khám phá <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-3 mt-6">
                    <button
                      onClick={() => setPage(value => Math.max(1, value - 1))}
                      disabled={page <= 1}
                      className="w-9 h-9 rounded-full bg-white border border-pink-100 text-slate-600 hover:text-[#a43073] disabled:opacity-40 flex items-center justify-center"
                      aria-label="Trang trước"
                    >
                      <span className="material-symbols-outlined text-[20px]">chevron_left</span>
                    </button>
                    <span className="text-xs font-semibold text-slate-600">Trang {page}/{totalPages}</span>
                    <button
                      onClick={() => setPage(value => Math.min(totalPages, value + 1))}
                      disabled={page >= totalPages}
                      className="w-9 h-9 rounded-full bg-white border border-pink-100 text-slate-600 hover:text-[#a43073] disabled:opacity-40 flex items-center justify-center"
                      aria-label="Trang sau"
                    >
                      <span className="material-symbols-outlined text-[20px]">chevron_right</span>
                    </button>
                  </div>
                )}
              </>
            )}
          </div>

        </div>

        {/* RIGHT SIDEBAR: Vocabulary of the Day & Study Tips (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">

          {/* Card: Từ vựng trong ngày */}
          <div className="bg-white rounded-3xl p-6 shadow-soft border border-pink-100 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                <span>💡</span> TỪ VỰNG TRONG NGÀY
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 font-bold text-xs">
                {dailyWord ? hskLabel(dailyWord.hsk_level) : 'HSK 4'}
              </span>
            </div>

            <div className="bg-gradient-to-b from-[#eff4ff] to-white p-5 rounded-2xl border border-blue-100 text-center flex flex-col items-center">
              <div className="flex items-center gap-2 mb-1">
                <button
                  onClick={() => onLookupWord(dailyTerm)}
                  className="text-3xl font-extrabold text-slate-800 font-['Noto_Serif_SC'] hover:text-[#a43073] transition-colors"
                  title="Tra từ này"
                >
                  {dailyTerm}
                </button>
                <button
                  onClick={() => handlePlayWord(dailyTerm)}
                  className="w-8 h-8 rounded-full bg-white hover:bg-blue-100 text-blue-600 flex items-center justify-center shadow-xs transition-colors"
                  title="Nghe phát âm"
                >
                  <span className="material-symbols-outlined text-[18px]">volume_up</span>
                </button>
              </div>
              <span className="text-xs font-mono font-semibold text-blue-600">
                {dailyWord ? dailyWord.pinyin : 'lín jìn'}
              </span>
              <div className="text-xs text-slate-600 font-medium mt-2">
                {dailyWord ? dailyWord.meaning : 'Đến gần · Cận kề (thời gian / địa điểm)'}
              </div>
            </div>

            {dailyWord ? (
              dailyWord.example && (
                <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100 leading-relaxed">
                  <span className="font-semibold text-slate-800">Ví dụ:</span><br />
                  <span className="italic font-['Noto_Serif_SC'] font-medium">{dailyWord.example.zh}</span>
                  {dailyWord.example.pinyin && (
                    <><br /><span className="font-mono text-[11px] text-blue-600">{dailyWord.example.pinyin}</span></>
                  )}
                  {dailyWord.example.vi && <><br />{dailyWord.example.vi}</>}
                  {dailyWord.example.source === 'tatoeba' && (
                    <><br /><span className="text-[10px] text-slate-400">Tatoeba</span></>
                  )}
                </div>
              )
            ) : (
              <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100 leading-relaxed">
                <span className="font-semibold text-slate-800">Ví dụ trích từ manhua:</span><br />
                <span className="italic font-['Noto_Serif_SC'] font-medium">"期末考试即将<strong>临近</strong>。"</span> (Kỳ thi cuối kỳ sắp sửa kéo đến.)
              </div>
            )}

            <button
              onClick={() => void handleSaveDailyWord()}
              disabled={savingDaily || !dailyWord || dailyInNotebook}
              className="w-full py-2.5 rounded-full text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-1.5 bg-gradient-to-r from-pink-500 to-rose-400 text-white hover:from-pink-600 hover:to-rose-500 disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-[16px]">{dailyInNotebook ? 'check' : 'bookmark_add'}</span>
              <span>{savingDaily ? 'Đang lưu...' : dailyInNotebook ? 'Đã có trong Sổ Từ Vựng' : 'Thêm vào Sổ Từ Vựng Yinghua'}</span>
            </button>
          </div>

          {/* Card: Mẹo đọc manhua tăng phản xạ */}
          <div className="bg-white rounded-3xl p-6 shadow-soft border border-pink-100 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <span className="text-pink-500 font-bold">🌸</span>
              <h3 className="text-sm font-bold text-slate-800">Mẹo Đọc Manhua Tăng Phản Xạ</h3>
            </div>

            <div className="space-y-3 text-xs text-slate-600">
              <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50">
                <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  1
                </span>
                <div>
                  <strong className="text-slate-800 block">Đọc ngữ cảnh hình ảnh trước</strong>
                  Quan sát biểu cảm nhân vật để dự đoán ý nghĩa câu trước khi bật Pinyin.
                </div>
              </div>

              <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50">
                <span className="w-5 h-5 rounded-full bg-pink-100 text-pink-700 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  2
                </span>
                <div>
                  <strong className="text-slate-800 block">Nghe lặp lại (Shadowing)</strong>
                  Chạm vào icon loa ở mỗi khung tranh và lặp lại theo ngữ điệu nhân vật.
                </div>
              </div>

              <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50">
                <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  3
                </span>
                <div>
                  <strong className="text-slate-800 block">Ôn lại 10 từ/ngày</strong>
                  Các từ đã lưu trong khi đọc truyện sẽ tự động chuyển vào bộ Flashcard SRS.
                </div>
              </div>
            </div>

            <button
              onClick={onNavigateToFlashcards}
              className="text-xs font-bold text-[#a43073] hover:underline flex items-center justify-center gap-1 pt-1"
            >
              <span>Mở bộ nhớ Flashcard Spaced-Repetition</span>
              <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>
          </div>

          {/* Streak Card */}
          <div className="p-4 rounded-3xl bg-gradient-to-r from-pink-50 to-amber-50 border border-pink-200/60 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔥</span>
              <div>
                <span className="text-xs font-bold text-slate-800 block">Chuỗi học tập</span>
                <span className="text-[11px] text-slate-500">
                  {!isLoggedIn
                    ? 'Đăng nhập để theo dõi chuỗi ngày học!'
                    : !streak
                      ? 'Đang tải chuỗi ngày học...'
                      : streak.current_streak > 0
                        ? `${streak.current_streak} ngày kiên trì liên tục!`
                        : 'Học hôm nay để bắt đầu chuỗi mới!'}
                </span>
              </div>
            </div>
            {/* TODO(M16): XP chưa có API (GĐ6.5); giữ hiển thị như thiết kế. */}
            <span className="px-3 py-1 rounded-full bg-[#a43073] text-white font-bold text-xs shadow-xs">
              +50 XP
            </span>
          </div>

        </div>

      </div>

      <SeriesDetailModal
        seriesId={openSeriesId}
        isLoggedIn={isLoggedIn}
        onClose={() => setOpenSeriesId(null)}
        onOpenReader={onOpenReader}
        onRequireLogin={onRequireLogin}
        showToast={showToast}
        onChanged={() => {
          setReloadTick(value => value + 1);
          void loadFeatured();
        }}
      />

    </div>
  );
};
