import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Bookmark, BookmarkCheck, Download, Eraser, Highlighter, Palette, PenLine, Pencil, Undo2 } from 'lucide-react';
import { ApiError, errorMessage, isAbortedError } from '../api/client';
import { WordLookup, hskLabel } from '../api/dictionary';
import { downloadPageImage, retranslatePage } from '../api/imaging';
import { ApiChapter, ApiPage, getChapter, getPage, saveProgress } from '../api/library';
import {
  ApiStroke,
  ReadingBubble,
  ReadingData,
  clearAnnotations,
  deleteBubbleEdit,
  getReading,
  lookupBubbleWord,
  saveAnnotations,
  saveBubbleEdit,
  setBookmark
} from '../api/reader';
import { getSavedStatus, isAlreadySaved, saveResultMessage, saveWord } from '../api/vocab';
import {
  isPageWithoutWords,
  isSentenceAlreadySaved,
  saveAllMessage,
  saveAllPageWords,
  saveSentence
} from '../api/sentences';
import {
  BUBBLE_FONT_SCALE_DEFAULT,
  BUBBLE_FONT_SCALE_MAX,
  BUBBLE_FONT_SCALE_MIN,
  BUBBLE_FONT_SCALE_STEP,
  getSettings,
  updateSettings
} from '../api/settings';
import { ReaderTarget } from '../types';
import { formatChapterNumber } from '../utils/format';
import { speakChinese } from '../utils/speech';
import { LoadedPages, findLoadedIndex, targetOfPage } from '../utils/readerPages';
import { notifyActivity, useStreak } from '../utils/useStreak';
import { useReaderSources, useSeriesChapters } from '../utils/useReaderSources';
import { AuthImage } from './AuthImage';
import { ChapterCoverageBar } from './ChapterCoverageBar';
import { ChapterSuggestions } from './ChapterSuggestions';
import { GrammarPanel } from './GrammarPanel';
import { ReaderChapterSelect } from './ReaderChapterSelect';
import { ReaderEmptyState } from './ReaderEmptyState';
import { ReaderPageSidebar } from './ReaderPageSidebar';
import { ReaderSourcePicker } from './ReaderSourcePicker';
import { useTourPage } from '../tour/TourProvider';
import { TourReplayButton } from '../tour/TourReplayButton';
import { ReportErrorDialog, ReportTarget } from './ReportErrorDialog';
import { StatusPill } from './StatusPill';
import { UnlockVipDialog } from './UnlockVipDialog';
import { usePageStatuses } from './usePageStatuses';

interface ComicReaderProps {
  /** Chương/trang cần mở; null khi vào trình đọc mà chưa chọn truyện. */
  target: ReaderTarget | null;
  isLoggedIn: boolean;
  onOpenUpload: () => void;
  onBrowse: () => void;
  onOpenReader: (target: ReaderTarget) => void;
  /** Cập nhật URL (thay thế mục lịch sử) khi đổi trang trong cùng chương/bộ ảnh, để F5 và chia sẻ link đúng trang. */
  onSyncUrl: (target: ReaderTarget) => void;
  /** Tăng lên khi người dùng vừa tải ảnh, để đọc lại danh sách nguồn đọc. */
  refreshKey?: number;
  onRequireLogin: (message: string) => void;
  onLookupWord: (term: string) => void;
  /** Mở cài đặt Học tập để khai báo trình độ (gợi ý từ). */
  onOpenLearningSettings?: () => void;
}

type ViewMode = 'bubble' | 'inpainted' | 'rendered';

interface ReaderMeta {
  title: string;
  chapterId: number | null;
  chapterNumber: number | null;
  chapterTitle: string | null;
  seriesId: number | null;
}

interface VocabEntry {
  word: string;
  pinyin: string | null;
  bubbleId: number;
}

interface LookupCard {
  word: string;
  bubbleId: number;
  status: 'loading' | 'ok' | 'error' | 'limit';
  data?: WordLookup;
  message?: string;
}

const ANNOTATION_SAVE_DELAY_MS = 800;
const PROGRESS_SAVE_DELAY_MS = 1500;
const FONT_SCALE_SAVE_DELAY_MS = 600;
const BUBBLE_BASE_FONT_PX = 11;
const MAX_VOCAB_PER_PAGE = 40;
const HAS_CJK = /[一-鿿]/;
// Khớp giới hạn của máy chủ cho một lần hỏi trạng thái đã lưu.
const MAX_STATUS_ITEMS = 200;
/** Chu kỳ hỏi lại dữ liệu đọc khi trang chưa xử lý xong, và thời gian chờ tối đa trước khi báo người học. */
const READING_POLL_INTERVAL_MS = 2000;
const READING_POLL_TIMEOUT_MS = 10 * 60 * 1000;

const VARIANT_OF_MODE: Record<ViewMode, 'original' | 'inpainted' | 'rendered'> = {
  bubble: 'original',
  inpainted: 'inpainted',
  rendered: 'rendered'
};

const meaningOf = (data: WordLookup | undefined): string =>
  data?.readings[0]?.definitions[0]?.gloss ?? data?.readings[0]?.english[0] ?? '';

const isNarration = (bubble: ReadingBubble): boolean => /narr|caption|text/i.test(bubble.class_name);

export const ComicReader: React.FC<ComicReaderProps> = ({
  target,
  isLoggedIn,
  onOpenUpload,
  onBrowse,
  onOpenReader,
  onSyncUrl,
  refreshKey = 0,
  onRequireLogin,
  onLookupWord,
  onOpenLearningSettings
}) => {
  // Từ đã lưu từ trang này (khóa `trang|từ`). Lấy từ máy chủ mỗi khi mở trang / quay lại tab, nên vẫn đúng sau F5.
  const { streak } = useStreak();
  const [reportTarget, setReportTarget] = useState<ReportTarget | null>(null);
  const [savedKeys, setSavedKeys] = useState<Set<string>>(() => new Set());
  // Từ đã có trong Sổ tay nhưng có thể từ trang khác: vẫn bấm được để thêm ngữ cảnh của trang này (F07.02).
  const [notebookTerms, setNotebookTerms] = useState<Set<string>>(() => new Set());
  const [savedStatusTick, setSavedStatusTick] = useState(0);
  const [savingKeys, setSavingKeys] = useState<Set<string>>(() => new Set());
  const [pages, setPages] = useState<ApiPage[]>([]);
  const [meta, setMeta] = useState<ReaderMeta | null>(null);
  const [loadingChapter, setLoadingChapter] = useState<boolean>(false);
  const [chapterError, setChapterError] = useState<ApiError | null>(null);
  // Mở khóa truyện VIP bằng vé rồi nạp lại chương (F17.05, F17.06).
  const [vipDialogOpen, setVipDialogOpen] = useState<boolean>(false);
  const [chapterTick, setChapterTick] = useState<number>(0);
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0);
  const [reading, setReading] = useState<ReadingData | null>(null);
  const [bubbles, setBubbles] = useState<ReadingBubble[]>([]);
  const [readingLoading, setReadingLoading] = useState<boolean>(false);
  const [readingError, setReadingError] = useState<ApiError | null>(null);
  const [readingTick, setReadingTick] = useState<number>(0);
  const [viewMode, setViewMode] = useState<ViewMode>('bubble');
  const [overlaysVisible, setOverlaysVisible] = useState<boolean>(true);
  const [speechRate, setSpeechRate] = useState<number>(1.0);
  const [fontScale, setFontScale] = useState<number>(BUBBLE_FONT_SCALE_DEFAULT);
  const [savedSentenceIds, setSavedSentenceIds] = useState<Set<number>>(() => new Set());
  const [savingSentenceIds, setSavingSentenceIds] = useState<Set<number>>(() => new Set());
  const [remainingWords, setRemainingWords] = useState<{ pageId: number; count: number } | null>(null);
  const [savingAllWords, setSavingAllWords] = useState<boolean>(false);
  const [coverageTick, setCoverageTick] = useState<number>(0);
  const [isPlayingFullPage, setIsPlayingFullPage] = useState<boolean>(false);
  const [savedSuccessMsg, setSavedSuccessMsg] = useState<string | null>(null);
  const [isStudyMenuOpen, setIsStudyMenuOpen] = useState(false);
  const [annotationTool, setAnnotationTool] = useState<'none' | 'highlight' | 'draw'>('none');
  const [annotationColor, setAnnotationColor] = useState('#f472b6');
  const [pageHighlights, setPageHighlights] = useState<Record<string, string>>({});
  const [pageStrokes, setPageStrokes] = useState<ApiStroke[]>([]);
  const [isBookmarked, setIsBookmarked] = useState<boolean>(false);
  const [isDrawing, setIsDrawing] = useState(false);
  const [lookupCard, setLookupCard] = useState<LookupCard | null>(null);
  const [editing, setEditing] = useState<{ bubbleId: number; text: string } | null>(null);
  const [editBusy, setEditBusy] = useState<boolean>(false);
  const [retranslating, setRetranslating] = useState<boolean>(false);

  const sources = useReaderSources(isLoggedIn, refreshKey);
  const loadedRef = useRef<LoadedPages | null>(null);
  const drawingPointerId = useRef<number | null>(null);
  const highlightsRef = useRef<Record<string, string>>({});
  const strokesRef = useRef<ApiStroke[]>([]);
  const pendingSavePage = useRef<number | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lookupCache = useRef<Map<string, WordLookup>>(new Map());
  const fontScaleTouched = useRef<boolean>(false);
  const fontScaleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const activePage: ApiPage | undefined = pages[currentPageIndex];
  const activePageId = activePage?.id ?? null;
  const chapters = useSeriesChapters(meta?.seriesId ?? null, isLoggedIn, refreshKey);
  // Trang khác đang xếp hàng/xử lý trong bộ đang xem: hỏi trạng thái để nhãn trạng thái ở cột trái tự cập nhật.
  // Trang đang xem đã có vòng hỏi riêng bên dưới nên không đưa vào đây để khỏi hỏi trùng.
  const pendingOtherIds = pages.filter(page => page.id !== activePageId && (page.status === 'queued' || page.status === 'running')).map(page => page.id);
  const { statuses: otherStatuses } = usePageStatuses(pendingOtherIds, pendingOtherIds.length > 0);
  const pageStatus = reading?.page.status ?? null;
  const awaitingTranslation = pageStatus === 'queued' || pageStatus === 'running';
  const effectiveStatus = pageStatus;
  // Máy chủ cũ chưa gửi `text_ready`: coi như chỉ có chữ khi đã `done`.
  const textReady = reading ? (reading.page.text_ready ?? reading.page.status === 'done') : false;
  const [timedOut, setTimedOut] = useState<boolean>(false);

  // ---- Trang chưa xong: hỏi lại dữ liệu đọc mỗi ~3 s để hiện dần chữ rồi ảnh ----
  useEffect(() => {
    if (activePageId === null || !awaitingTranslation) return;
    const pageId = activePageId;
    const controller = new AbortController();
    const startedAt = Date.now();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let inFlight = false;
    setTimedOut(false);

    const schedule = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(tick, READING_POLL_INTERVAL_MS);
    };
    const tick = async () => {
      if (controller.signal.aborted || inFlight) return;
      if (document.hidden) return; // Tab ẩn: dừng, hỏi lại ngay khi quay lại tab.
      if (Date.now() - startedAt > READING_POLL_TIMEOUT_MS) {
        setTimedOut(true);
        return;
      }
      inFlight = true;
      let finished = false;
      try {
        const data = await getReading(pageId, controller.signal);
        if (controller.signal.aborted) return;
        setReading(data);
        // Chỉ nạp bong bóng khi vừa có chữ hoặc đã xong, để không ghi đè thao tác đang làm.
        setBubbles(current => (current.length === 0 || data.page.status === 'done' ? data.bubbles : current));
        finished = data.page.status === 'done' || data.page.status === 'failed';
      } catch {
        // Lỗi mạng tạm thời hoặc đã hủy: giữ dữ liệu cũ, lượt sau thử lại.
      } finally {
        inFlight = false;
      }
      if (!finished && !controller.signal.aborted) schedule();
    };
    const onVisibility = () => {
      if (document.hidden || inFlight) return;
      if (timer) clearTimeout(timer);
      void tick();
    };

    document.addEventListener('visibilitychange', onVisibility);
    schedule();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [activePageId, awaitingTranslation]);

  const showMessage = useCallback((message: string) => {
    setSavedSuccessMsg(message);
    setTimeout(() => setSavedSuccessMsg(null), 3000);
  }, []);

  // Báo lỗi cần đăng nhập (F14.01): Khách được mời đăng nhập thay vì bị từ chối sau khi gõ mô tả.
  const openReport = (bubbleId: number | null) => {
    if (!activePage) return;
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để báo lỗi bản dịch!');
      return;
    }
    setReportTarget({ pageId: activePage.id, bubbleId });
  };

  // Cỡ chữ lớp dịch lấy từ cài đặt của người học (F02.04); Khách chỉ dùng trạng thái cục bộ.
  useEffect(() => {
    if (!isLoggedIn) return;
    let cancelled = false;
    getSettings()
      .then(settings => {
        if (!cancelled && !fontScaleTouched.current) setFontScale(settings.bubble_font_scale);
      })
      .catch(() => {
        // Không tải được cài đặt thì dùng cỡ mặc định, không chặn việc đọc.
      });
    return () => {
      cancelled = true;
    };
  }, [isLoggedIn]);

  // ---- Ghi chú (tô màu, nét vẽ): lưu lên máy chủ sau một khoảng nghỉ, không lưu từng điểm vẽ ----
  const flushAnnotations = useCallback(async () => {
    const pageId = pendingSavePage.current;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = null;
    if (pageId === null) return;
    pendingSavePage.current = null;
    try {
      await saveAnnotations(pageId, { highlights: highlightsRef.current, strokes: strokesRef.current });
    } catch (err) {
      showMessage(errorMessage(err));
    }
  }, [showMessage]);

  const scheduleAnnotationSave = useCallback(() => {
    if (activePageId === null) return;
    pendingSavePage.current = activePageId;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => void flushAnnotations(), ANNOTATION_SAVE_DELAY_MS);
  }, [activePageId, flushAnnotations]);

  const applyHighlights = (next: Record<string, string>) => {
    highlightsRef.current = next;
    setPageHighlights(next);
  };

  const applyStrokes = (next: ApiStroke[]) => {
    strokesRef.current = next;
    setPageStrokes(next);
  };

  // Rời trang/đóng trình đọc: gửi nốt phần ghi chú chưa kịp lưu.
  useEffect(() => {
    return () => {
      void flushAnnotations();
    };
  }, [flushAnnotations]);

  const goToPage = (index: number) => {
    const page = pages[index];
    if (!page || !meta) return;
    void flushAnnotations();
    setCurrentPageIndex(index);
    onSyncUrl(targetOfPage(meta.chapterId, page));
  };

  // Bộ trang đang nạp, để biết đích mới (do đổi URL) có nằm trong đó không.
  useEffect(() => {
    loadedRef.current = meta ? { chapterId: meta.chapterId, pages } : null;
  }, [meta, pages]);

  // ---- Nạp chương hoặc ảnh lẻ theo `target` ----
  useEffect(() => {
    // Đổi trang trong cùng chương/bộ ảnh (URL đổi theo): chỉ chuyển trang, không nạp lại.
    const loadedIndex = findLoadedIndex(target, loadedRef.current);
    if (loadedIndex !== null) {
      setCurrentPageIndex(loadedIndex);
      return;
    }
    void flushAnnotations();
    setPages([]);
    setMeta(null);
    setChapterError(null);
    setReading(null);
    setCurrentPageIndex(0);
    if (!target) return;
    const controller = new AbortController();
    setLoadingChapter(true);
    const run = async () => {
      if (target.chapterId !== null) {
        const detail = await getChapter(target.chapterId, controller.signal);
        let index = 0;
        if (target.pageId !== undefined) index = detail.pages.findIndex(page => page.id === target.pageId);
        else if (target.pageNo !== undefined) index = detail.pages.findIndex(page => page.page_no === target.pageNo);
        else if (detail.progress) index = detail.pages.findIndex(page => page.page_no === detail.progress?.page_no);
        setPages(detail.pages);
        setMeta({
          title: detail.series_title,
          chapterId: detail.chapter.id,
          chapterNumber: detail.chapter.number,
          chapterTitle: detail.chapter.title,
          seriesId: detail.series_id
        });
        setCurrentPageIndex(Math.max(0, index));
      } else if (target.pageId !== undefined) {
        const page = await getPage(target.pageId, controller.signal);
        setPages([page]);
        setMeta({ title: 'Ảnh bạn tải lên', chapterId: null, chapterNumber: null, chapterTitle: null, seriesId: null });
      }
    };
    run()
      .catch(err => {
        if (!isAbortedError(err)) setChapterError(err instanceof ApiError ? err : null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingChapter(false);
      });
    return () => controller.abort();
  }, [target, chapterTick]);

  // ---- Ảnh tải nhanh: cột trái liệt kê cả bộ ảnh còn hạn của người dùng, ảnh đang mở được tô ----
  const quickUploads = sources.quick;
  useEffect(() => {
    if (!meta || meta.chapterId !== null || !quickUploads || target?.pageId === undefined) return;
    const index = quickUploads.findIndex(page => page.id === target.pageId);
    if (index < 0) return; // Ảnh hết hạn hoặc ngoài bộ: chỉ hiện riêng ảnh đó.
    setPages(quickUploads);
    setCurrentPageIndex(index);
  }, [meta, quickUploads, target]);

  // ---- Nạp dữ liệu đọc của trang đang xem ----
  useEffect(() => {
    if (activePageId === null) return;
    const controller = new AbortController();
    setReadingLoading(true);
    setReadingError(null);
    getReading(activePageId, controller.signal)
      .then(data => {
        setReading(data);
        setBubbles(data.bubbles);
        applyHighlights(data.annotation?.highlights ?? {});
        applyStrokes(data.annotation?.strokes ?? []);
        setIsBookmarked(data.annotation?.is_bookmarked ?? false);
        setLookupCard(null);
        setEditing(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) {
          setReading(null);
          setBubbles([]);
          setReadingError(err instanceof ApiError ? err : null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setReadingLoading(false);
      });
    return () => controller.abort();
  }, [activePageId, readingTick]);

  // ---- Lưu tiến độ đọc (chỉ chương, chỉ khi đã đăng nhập) ----
  useEffect(() => {
    if (!isLoggedIn || !meta || meta.chapterId === null || !activePage) return;
    const chapterId = meta.chapterId;
    const isLast = currentPageIndex === pages.length - 1;
    const timer = setTimeout(() => {
      saveProgress(chapterId, { page_no: activePage.page_no, mode: 'read', completed: isLast })
        .then(notifyActivity)
        .catch(() => undefined);
    }, PROGRESS_SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [isLoggedIn, meta, activePage, currentPageIndex, pages.length]);

  const vocabulary = useMemo<VocabEntry[]>(() => {
    const seen = new Set<string>();
    const entries: VocabEntry[] = [];
    bubbles.forEach(bubble => {
      bubble.tokens.forEach(token => {
        if (!HAS_CJK.test(token.word) || seen.has(token.word) || entries.length >= MAX_VOCAB_PER_PAGE) return;
        seen.add(token.word);
        entries.push({ word: token.word, pinyin: token.pinyin, bubbleId: bubble.id });
      });
    });
    return entries;
  }, [bubbles]);

  // Đồng bộ dấu "đã lưu" (từ và câu thoại) với máy chủ: khi đổi trang, khi quay lại tab (có thể vừa xóa từ ở Sổ tay).
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === 'visible') setSavedStatusTick(value => value + 1);
    };
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, []);

  // Khi vừa đổi trang, `bubbles` còn là của trang cũ tới khi dữ liệu đọc mới về: chỉ hỏi khi `reading` đã khớp trang đang xem.
  const readingPageId = reading?.page.id ?? null;
  useEffect(() => {
    if (!isLoggedIn || activePageId === null || readingPageId !== activePageId || bubbles.length === 0) return;
    const pageId = activePageId;
    const pageBubbleIds = bubbles.map(bubble => bubble.id);
    const terms = [...new Set(bubbles.flatMap(bubble => bubble.tokens.map(token => token.word)))]
      .filter(word => HAS_CJK.test(word))
      .slice(0, MAX_STATUS_ITEMS);
    const controller = new AbortController();
    getSavedStatus({ terms, bubbleIds: pageBubbleIds.slice(0, MAX_STATUS_ITEMS), pageId }, controller.signal)
      .then(status => {
        const prefix = `${pageId}|`;
        setSavedKeys(current => {
          const next = new Set([...current].filter(key => !key.startsWith(prefix)));
          status.page_terms.forEach(term => next.add(prefix + term));
          return next;
        });
        setNotebookTerms(new Set(status.terms));
        const onPage = new Set(pageBubbleIds);
        setSavedSentenceIds(current => {
          const next = new Set([...current].filter(id => !onPage.has(id)));
          status.bubble_ids.forEach(id => next.add(id));
          return next;
        });
      })
      .catch(() => {
        // Lỗi mạng: giữ trạng thái đang có, lần đổi trang/quay lại tab sau sẽ thử lại.
      });
    return () => controller.abort();
  }, [isLoggedIn, activePageId, readingPageId, bubbles, savedStatusTick]);

  const handlePlayVoice = (text: string) => {
    speakChinese(text, speechRate);
  };

  const handleReadEntirePage = async () => {
    if (isPlayingFullPage) return;
    setIsPlayingFullPage(true);
    const fullText = bubbles.map(b => b.text_zh).join(' ');
    await speakChinese(fullText, speechRate);
    setIsPlayingFullPage(false);
  };

  // ---- Tra từ trong bong bóng (F05.02, F05.04) ----
  const lookupWord = async (bubbleId: number, word: string, silent = false): Promise<WordLookup | null> => {
    const cached = lookupCache.current.get(word);
    if (cached) {
      if (!silent) setLookupCard({ word, bubbleId, status: 'ok', data: cached });
      return cached;
    }
    if (!silent) setLookupCard({ word, bubbleId, status: 'loading' });
    try {
      const result = await lookupBubbleWord(bubbleId, word, !isLoggedIn);
      lookupCache.current.set(word, result.lookup);
      if (!silent) setLookupCard({ word, bubbleId, status: 'ok', data: result.lookup });
      return result.lookup;
    } catch (err) {
      if (!silent) {
        const limited = err instanceof ApiError && err.code === 'GUEST_LOOKUP_LIMIT_REACHED';
        setLookupCard({ word, bubbleId, status: limited ? 'limit' : 'error', message: errorMessage(err) });
      }
      return null;
    }
  };

  const keyOf = (word: string) => `${activePageId}|${word}`;
  const isSaved = (word: string) => savedKeys.has(keyOf(word));
  const isSaving = (word: string) => savingKeys.has(keyOf(word));
  const isInNotebook = (word: string) => notebookTerms.has(word);

  type SaveOutcome = 'created' | 'context' | 'duplicate' | 'failed';

  // Lưu một từ kèm bong bóng và trang để máy chủ cắt ảnh ngữ cảnh (F07.01, F07.02).
  const saveVocabulary = async (word: string, bubbleId: number, announce = true): Promise<SaveOutcome> => {
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để lưu từ vào Sổ tay của bạn!');
      return 'failed';
    }
    if (activePageId === null || isSaving(word)) return 'failed';
    const key = keyOf(word);
    setSavingKeys(current => new Set(current).add(key));
    try {
      const result = await saveWord({ term: word, source: 'highlight', bubble_id: bubbleId, page_id: activePageId });
      setSavedKeys(current => new Set(current).add(key));
      setNotebookTerms(current => new Set(current).add(word));
      if (announce) showMessage(saveResultMessage(word, result));
      return result.created ? 'created' : 'context';
    } catch (err) {
      if (isAlreadySaved(err)) {
        setSavedKeys(current => new Set(current).add(key));
        if (announce) showMessage('Từ này đã có với ngữ cảnh này');
        return 'duplicate';
      }
      if (announce) showMessage(errorMessage(err));
      return 'failed';
    } finally {
      setSavingKeys(current => {
        const next = new Set(current);
        next.delete(key);
        return next;
      });
    }
  };

  const handleSaveAllVocab = async () => {
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để lưu từ vào Sổ tay của bạn!');
      return;
    }
    if (activePageId === null || savingAllWords) return;
    const pageId = activePageId;
    setSavingAllWords(true);
    try {
      const result = await saveAllPageWords(pageId);
      setSavedKeys(current => {
        const next = new Set(current);
        [...result.saved, ...result.existing].forEach(term => next.add(`${pageId}|${term}`));
        return next;
      });
      setNotebookTerms(current => new Set([...current, ...result.saved, ...result.existing]));
      setRemainingWords(result.remaining > 0 ? { pageId, count: result.remaining } : null);
      setCoverageTick(value => value + 1);
      showMessage(saveAllMessage(result));
    } catch (err) {
      showMessage(
        isPageWithoutWords(err)
          ? 'Trang này chưa có từ để lưu (có thể đang xử lý hoặc chưa nhận diện được chữ).'
          : errorMessage(err)
      );
    } finally {
      setSavingAllWords(false);
    }
  };

  // Lưu câu thoại (một bong bóng) kèm bản dịch và nguồn (F07.11).
  const handleSaveSentence = async (bubbleId: number) => {
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để lưu câu thoại!');
      return;
    }
    if (savingSentenceIds.has(bubbleId) || savedSentenceIds.has(bubbleId)) return;
    setSavingSentenceIds(current => new Set(current).add(bubbleId));
    try {
      await saveSentence(bubbleId, activePageId ?? undefined);
      setSavedSentenceIds(current => new Set(current).add(bubbleId));
      showMessage('Đã lưu câu thoại. Xem lại ở Hồ sơ > Câu thoại đã lưu.');
    } catch (err) {
      if (isSentenceAlreadySaved(err)) setSavedSentenceIds(current => new Set(current).add(bubbleId));
      showMessage(isSentenceAlreadySaved(err) ? 'Câu thoại này đã được lưu.' : errorMessage(err));
    } finally {
      setSavingSentenceIds(current => {
        const next = new Set(current);
        next.delete(bubbleId);
        return next;
      });
    }
  };

  const pendingMoreWords = remainingWords !== null && remainingWords.pageId === activePageId ? remainingWords.count : 0;

  const toggleSavePage = async () => {
    if (!activePage) return;
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để lưu trang truyện!');
      return;
    }
    try {
      const result = await setBookmark(activePage.id, !isBookmarked);
      setIsBookmarked(result.is_bookmarked);
      showMessage(result.is_bookmarked ? 'Đã lưu trang truyện vào Thư viện (mục Trang đã lưu).' : 'Đã bỏ lưu trang truyện.');
    } catch (err) {
      showMessage(errorMessage(err));
    }
  };

  // ---- Sửa và hoàn tác bản dịch riêng (F05.05, F05.06) ----
  const startEdit = (bubble: ReadingBubble) => {
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để sửa bản dịch theo ý bạn!');
      return;
    }
    setEditing({ bubbleId: bubble.id, text: bubble.text_vi_effective ?? bubble.text_vi ?? '' });
  };

  const patchBubble = (bubbleId: number, changes: Partial<ReadingBubble>) =>
    setBubbles(current => current.map(item => (item.id === bubbleId ? { ...item, ...changes } : item)));

  const submitEdit = async () => {
    if (!editing) return;
    const text = editing.text.trim();
    if (!text) {
      showMessage('Bản dịch không được để trống.');
      return;
    }
    setEditBusy(true);
    try {
      const result = await saveBubbleEdit(editing.bubbleId, text);
      patchBubble(editing.bubbleId, { text_vi_effective: result.text_vi_effective, has_edit: result.has_edit });
      setEditing(null);
      showMessage('Đã lưu bản dịch của bạn.');
    } catch (err) {
      showMessage(errorMessage(err));
    } finally {
      setEditBusy(false);
    }
  };

  const undoEdit = async (bubbleId: number) => {
    setEditBusy(true);
    try {
      await deleteBubbleEdit(bubbleId);
      const original = bubbles.find(item => item.id === bubbleId)?.text_vi ?? null;
      patchBubble(bubbleId, { text_vi_effective: original, has_edit: false });
      setEditing(null);
      showMessage('Đã hoàn tác về bản dịch gốc.');
    } catch (err) {
      showMessage(errorMessage(err));
    } finally {
      setEditBusy(false);
    }
  };

  // ---- Dịch lại và tải ảnh (F04.03, F04.04) ----
  const handleRetranslate = async () => {
    if (!activePage) return;
    setRetranslating(true);
    try {
      await retranslatePage(activePage.id);
      setReading(current => (current ? { ...current, page: { ...current.page, status: 'queued', error_message: null } } : current));
      showMessage('Đã gửi yêu cầu dịch lại, trang đang xếp hàng.');
    } catch (err) {
      showMessage(errorMessage(err));
    } finally {
      setRetranslating(false);
    }
  };

  const handleDownload = async () => {
    if (!activePage) return;
    const variant = VARIANT_OF_MODE[viewMode];
    try {
      await downloadPageImage(activePage.id, variant, `yinghua-trang-${activePage.page_no}-${variant}.png`);
    } catch (err) {
      showMessage(errorMessage(err));
    }
  };

  // ---- Công cụ ghi chú ----
  const requireAnnotationLogin = (): boolean => {
    if (isLoggedIn) return false;
    onRequireLogin('Vui lòng đăng nhập để tô màu và ghi chú lên trang truyện!');
    return true;
  };

  const chooseTool = (tool: 'highlight' | 'draw') => {
    if (requireAnnotationLogin()) return;
    setAnnotationTool(annotationTool === tool ? 'none' : tool);
  };

  const handleBubbleAnnotation = (bubbleId: number) => {
    if (annotationTool !== 'highlight') return;
    const key = String(bubbleId);
    const next = { ...highlightsRef.current };
    if (next[key]) delete next[key];
    else next[key] = annotationColor;
    applyHighlights(next);
    scheduleAnnotationSave();
  };

  const getDrawingPoint = (event: React.PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1000, ((event.clientX - rect.left) / rect.width) * 1000)),
      y: Math.max(0, Math.min(1000, ((event.clientY - rect.top) / rect.height) * 1000))
    };
  };

  const startDrawing = (event: React.PointerEvent<SVGSVGElement>) => {
    if (annotationTool !== 'draw') return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    drawingPointerId.current = event.pointerId;
    setIsDrawing(true);
    applyStrokes([...strokesRef.current, { color: annotationColor, points: [getDrawingPoint(event)] }]);
  };

  const continueDrawing = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!isDrawing || drawingPointerId.current !== event.pointerId) return;
    const strokes = [...strokesRef.current];
    const lastStroke = strokes[strokes.length - 1];
    if (!lastStroke) return;
    strokes[strokes.length - 1] = { ...lastStroke, points: [...lastStroke.points, getDrawingPoint(event)] };
    applyStrokes(strokes);
  };

  const stopDrawing = (event: React.PointerEvent<SVGSVGElement>) => {
    if (drawingPointerId.current !== event.pointerId) return;
    drawingPointerId.current = null;
    setIsDrawing(false);
    scheduleAnnotationSave();
  };

  const clearAllAnnotations = async () => {
    if (!activePage || requireAnnotationLogin()) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    pendingSavePage.current = null;
    applyHighlights({});
    applyStrokes([]);
    try {
      await clearAnnotations(activePage.id);
    } catch (err) {
      showMessage(errorMessage(err));
    }
  };

  const cycleSpeed = () => {
    if (speechRate === 1.0) setSpeechRate(1.2);
    else if (speechRate === 1.2) setSpeechRate(0.8);
    else setSpeechRate(1.0);
  };

  // Lưu cỡ chữ lên máy chủ sau một khoảng nghỉ để bấm A-/A+ liên tục chỉ gửi một lần.
  const changeFontSize = (delta: number) => {
    const next = Math.max(BUBBLE_FONT_SCALE_MIN, Math.min(BUBBLE_FONT_SCALE_MAX, fontScale + delta * BUBBLE_FONT_SCALE_STEP));
    if (next === fontScale) return;
    fontScaleTouched.current = true;
    setFontScale(next);
    if (!isLoggedIn) return;
    if (fontScaleTimer.current) clearTimeout(fontScaleTimer.current);
    fontScaleTimer.current = setTimeout(() => {
      fontScaleTimer.current = null;
      updateSettings({ bubble_font_scale: next }).catch(err => showMessage(`Chưa lưu được cỡ chữ: ${errorMessage(err)}`));
    }, FONT_SCALE_SAVE_DELAY_MS);
  };

  // Hết trang cuối chương thì bấm "kế tiếp" sang chương sau (không vòng về trang 1); trang đầu bấm lùi về cuối chương trước.
  const chapterIndex = meta?.chapterId != null ? chapters.findIndex(chapter => chapter.id === meta.chapterId) : -1;
  const prevChapter: ApiChapter | null = chapterIndex > 0 ? chapters[chapterIndex - 1] : null;
  const nextChapter: ApiChapter | null = chapterIndex >= 0 && chapterIndex < chapters.length - 1 ? chapters[chapterIndex + 1] : null;
  const canGoPrev = currentPageIndex > 0 || prevChapter !== null;
  const canGoNext = currentPageIndex < pages.length - 1 || nextChapter !== null;

  const prevPage = () => {
    if (currentPageIndex > 0) goToPage(currentPageIndex - 1);
    else if (prevChapter) {
      showMessage(`Về Chương ${formatChapterNumber(prevChapter.number)}`);
      onOpenReader({ chapterId: prevChapter.id, pageNo: prevChapter.page_count });
    }
  };
  const nextPage = () => {
    if (currentPageIndex < pages.length - 1) goToPage(currentPageIndex + 1);
    else if (nextChapter) {
      showMessage(`Sang Chương ${formatChapterNumber(nextChapter.number)}`);
      onOpenReader({ chapterId: nextChapter.id, pageNo: 1 });
    }
  };
  const liveStatus = (page: ApiPage) => {
    if (reading && reading.page.id === page.id) return reading.page.status;
    const base = page.status;
    return (base === 'queued' || base === 'running') && otherStatuses[page.id] ? otherStatuses[page.id].status : base;
  };

  useTourPage(target && !loadingChapter && !chapterError && activePage && reading && !readingLoading ? 'reader' : null);

  // ---- Trạng thái chưa có nội dung ----
  if (!target) {
    return <ReaderEmptyState isLoggedIn={isLoggedIn} sources={sources} onOpenReader={onOpenReader} onBrowse={onBrowse} onOpenUpload={onOpenUpload} />;
  }

  if (loadingChapter || chapterError || pages.length === 0 || !activePage) {
    const vipRequired = chapterError?.code === 'VIP_REQUIRED' && isLoggedIn;
    const needsLogin = chapterError !== null && !vipRequired && (chapterError.status === 401 || chapterError.status === 403);
    const vipSeriesId = typeof chapterError?.details.series_id === 'number' ? chapterError.details.series_id : null;
    return (
      <div className="w-full max-w-[700px] mx-auto px-4 py-20 flex flex-col items-center text-center gap-4">
        {loadingChapter ? (
          <>
            <span className="w-8 h-8 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
            <p className="text-sm text-slate-500 dark:text-slate-400">Đang tải truyện...</p>
          </>
        ) : (
          <>
            <span className="material-symbols-outlined text-[44px] text-pink-300">{chapterError ? 'error' : 'photo_library'}</span>
            <p className="text-sm font-bold text-slate-700 dark:text-slate-100">
              {chapterError ? chapterError.message : 'Chương này chưa có trang nào để đọc.'}
            </p>
            <div className="flex items-center gap-3">
              {vipRequired && vipSeriesId !== null && (
                <button onClick={() => setVipDialogOpen(true)} className="px-5 py-2.5 rounded-full bg-[#a43073] text-white text-xs font-bold">
                  Mở khóa truyện VIP
                </button>
              )}
              {needsLogin && (
                <button onClick={() => onRequireLogin('Vui lòng đăng nhập để đọc chương này!')} className="px-5 py-2.5 rounded-full bg-[#a43073] text-white text-xs font-bold">
                  Đăng nhập
                </button>
              )}
              <button onClick={onBrowse} className="px-5 py-2.5 rounded-full bg-white border border-pink-200 text-[#a43073] text-xs font-bold hover:bg-pink-50 dark:bg-slate-800 dark:border-pink-900/40 dark:text-pink-400 dark:hover:bg-pink-900/40">
                Về Trang Chủ
              </button>
            </div>
            {vipDialogOpen && vipSeriesId !== null && (
              <UnlockVipDialog
                seriesId={vipSeriesId}
                hasTicketsHint={chapterError?.details.has_tickets === true}
                onClose={() => setVipDialogOpen(false)}
                onUnlocked={() => setChapterTick(value => value + 1)}
              />
            )}
          </>
        )}
      </div>
    );
  }

  const variantUrl = reading
    ? viewMode === 'bubble'
      ? reading.variants.original
      : viewMode === 'inpainted'
        ? reading.variants.inpainted
        : reading.variants.rendered
    : null;
  const imageFallback = reading?.variants.original ?? null;
  const showingOriginalAsFallback = viewMode !== 'bubble' && !variantUrl && !!imageFallback;
  const stageHint = textReady ? 'Đang xóa chữ và đắp bản dịch…' : 'Đang nhận diện chữ…';
  const canEditPage = reading?.page.can_edit ?? false;
  const failureMessage = reading?.page.error_message ?? null;
  const inQuickSet = meta?.chapterId === null;
  const positionLabel = inQuickSet
    ? `Ảnh ${currentPageIndex + 1}/${pages.length}`
    : `${meta?.chapterNumber != null ? `Chương ${formatChapterNumber(meta.chapterNumber)} · ` : ''}Trang ${currentPageIndex + 1}/${pages.length}`;
  const sidebarHeading = inQuickSet
    ? `Ảnh tải lên · ${pages.length} ảnh`
    : `${meta?.chapterNumber != null ? `Chương ${formatChapterNumber(meta.chapterNumber)}` : 'Chương'} · ${pages.length} trang`;

  const studyToolsMenu = isStudyMenuOpen ? (
    <div className="mt-2 w-64 max-h-[min(70vh,34rem)] overflow-y-auto rounded-2xl border border-blue-100 bg-white/95 p-3 shadow-xl backdrop-blur dark:border-blue-900/40 dark:bg-slate-800">
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2 dark:border-slate-700">
        <div>
          <h3 className="text-xs font-extrabold text-slate-800 dark:text-slate-100">Công cụ học tập</h3>
          <p className="text-[10px] text-slate-500 dark:text-slate-400">Từ vựng và ghi chú trang truyện</p>
        </div>
        <button onClick={toggleSavePage} className="inline-flex shrink-0 items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1.5 text-[10px] font-bold text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/40">
          {isBookmarked ? <BookmarkCheck size={13}/> : <Bookmark size={13}/>}
          {isBookmarked ? 'Đã lưu trang' : 'Lưu trang'}
        </button>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold text-slate-600 dark:text-slate-300">Từ vựng · {vocabulary.length}</span>
        <button onClick={handleSaveAllVocab} disabled={vocabulary.length === 0 || savingAllWords} className="inline-flex items-center gap-1 rounded-full bg-pink-50 px-2.5 py-1.5 text-[10px] font-bold text-[#a43073] hover:bg-pink-100 disabled:opacity-50 dark:bg-pink-900/30 dark:text-pink-400 dark:hover:bg-pink-900/40">
          <span className="material-symbols-outlined text-[13px]">style</span>{savingAllWords ? 'Đang lưu...' : pendingMoreWords > 0 ? `Lưu tiếp (${pendingMoreWords})` : 'Lưu tất cả'}
        </button>
      </div>
      <div className="mt-2 space-y-1.5">
        {vocabulary.length === 0 && <p className="text-[10px] text-slate-400">Trang này chưa có từ vựng nhận diện được.</p>}
        {vocabulary.map(vocab => (
          <div key={vocab.word} className="flex items-center justify-between gap-2 rounded-xl bg-slate-50 px-2.5 py-2 dark:bg-[#1e293b]">
            <div className="min-w-0">
              <span className="font-['Noto_Serif_SC'] text-sm font-bold text-slate-800 dark:text-slate-100">{vocab.word}</span>
              <span className="ml-2 text-[10px] text-slate-500 dark:text-slate-400">{vocab.pinyin}</span>
            </div>
            <button onClick={() => void saveVocabulary(vocab.word, vocab.bubbleId)} disabled={isSaved(vocab.word) || isSaving(vocab.word)} className="shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold disabled:bg-emerald-50 disabled:text-emerald-700 enabled:bg-white enabled:text-blue-700 enabled:hover:bg-blue-100">
              {isSaved(vocab.word) ? 'Đã lưu' : isSaving(vocab.word) ? 'Đang lưu...' : isInNotebook(vocab.word) ? '+ Ngữ cảnh' : '+ Sổ tay'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-3 border-t border-slate-100 pt-3 dark:border-slate-700">
        <div className="mb-2 text-[10px] font-bold text-slate-600 dark:text-slate-300">Bút ghi chú</div>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => chooseTool('highlight')} className={`flex items-center justify-center gap-1.5 rounded-xl px-2 py-2 text-[10px] font-bold ${annotationTool === 'highlight' ? 'bg-pink-500 text-white' : 'bg-pink-50 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400'}`}><Highlighter size={14}/>Tô nền thoại</button>
          <button onClick={() => chooseTool('draw')} className={`flex items-center justify-center gap-1.5 rounded-xl px-2 py-2 text-[10px] font-bold ${annotationTool === 'draw' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'}`}><PenLine size={14}/>Bút vẽ</button>
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300"><Palette size={13}/>Màu bút</span>
          <label className="relative h-7 w-7 cursor-pointer overflow-hidden rounded-full border-2 border-white shadow ring-1 ring-slate-200" style={{ backgroundColor: annotationColor }} title="Chọn màu tùy chỉnh">
            <input type="color" value={annotationColor} onChange={event => setAnnotationColor(event.target.value)} aria-label="Chọn màu tùy chỉnh" className="absolute inset-0 h-full w-full cursor-pointer opacity-0" />
          </label>
        </div>
        <div className="mt-2 flex items-center gap-2">
          {['#f472b6', '#facc15', '#4ade80', '#38bdf8', '#a78bfa', '#fb7185', '#1e293b'].map(color => <button key={color} onClick={() => setAnnotationColor(color)} aria-label={`Chọn màu ${color}`} aria-pressed={annotationColor === color} className={`h-6 w-6 rounded-full border-2 ${annotationColor === color ? 'border-slate-700 ring-2 ring-slate-200' : 'border-white shadow'}`} style={{ backgroundColor: color }} />)}
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-[9px] text-slate-400">{annotationTool === 'highlight' ? 'Chạm khung thoại để tô màu' : annotationTool === 'draw' ? 'Vẽ trực tiếp lên ảnh truyện' : isLoggedIn ? 'Chọn loại bút để bắt đầu' : 'Đăng nhập để ghi chú'}</span>
          <button onClick={clearAllAnnotations} className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-[9px] font-semibold text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"><Eraser size={12}/>Xóa ghi chú</button>
        </div>
      </div>
    </div>
  ) : null;

  const modeButton = (mode: ViewMode, icon: string, label: string, available: boolean, hint: string) => (
    <button
      key={mode}
      onClick={() => setViewMode(mode)}
      disabled={!available}
      title={available ? undefined : hint}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
        viewMode === mode
          ? 'bg-white text-[#a43073] shadow-xs font-bold dark:bg-slate-800 dark:text-pink-400'
          : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white'
      }`}
    >
      <span className="material-symbols-outlined text-[16px] text-pink-400">{icon}</span>
      <span>{label}</span>
    </button>
  );

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6">

      {/* CHAPTER & SUB-NAV BAR */}
      {/* `relative z-30`: backdrop-blur tạo lớp chồng riêng, không nâng lên thì bảng "Đổi nguồn đọc" bị khung ảnh đè. */}
      <div className="relative z-30 flex flex-col sm:flex-row items-center justify-between gap-4 mb-6 bg-white/80 backdrop-blur-md p-3.5 px-6 rounded-2xl border border-pink-100 shadow-sm dark:bg-slate-800 dark:border-pink-900/40">

        {/* Breadcrumb / Title */}
        <div className="flex items-center gap-3">
          <button
            onClick={prevPage}
            disabled={!canGoPrev}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-[#a43073] hover:bg-pink-50 transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-slate-400 dark:hover:text-pink-300 dark:hover:bg-pink-900/40"
            title={currentPageIndex === 0 && prevChapter ? 'Về chương trước' : inQuickSet ? 'Ảnh trước' : 'Trang trước'}
            aria-label={currentPageIndex === 0 && prevChapter ? 'Về chương trước' : inQuickSet ? 'Ảnh trước' : 'Trang trước'}
          >
            <span className="material-symbols-outlined text-[20px]">chevron_left</span>
          </button>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
              {meta?.title}
            </span>
            {isLoggedIn && (
              <ReaderSourcePicker sources={sources} currentSeriesId={meta?.seriesId ?? null} inQuickSet={inQuickSet} onOpenReader={onOpenReader} />
            )}
            <ReaderChapterSelect chapters={chapters} currentChapterId={meta?.chapterId ?? null} onSelect={chapterId => onOpenReader({ chapterId })} />
            <span className="text-slate-300 hidden sm:inline">|</span>
            <span className="text-xs text-[#a43073] font-semibold bg-pink-50 px-2.5 py-0.5 rounded-md border border-pink-200/50 dark:text-pink-400 dark:bg-pink-900/30 dark:border-pink-900/40">
              {positionLabel}
            </span>
          </div>

          <button
            onClick={nextPage}
            disabled={!canGoNext}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-[#a43073] hover:bg-pink-50 transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-slate-400 dark:hover:text-pink-300 dark:hover:bg-pink-900/40"
            title={currentPageIndex === pages.length - 1 && nextChapter ? 'Sang chương kế' : inQuickSet ? 'Ảnh kế tiếp' : 'Trang kế tiếp'}
            aria-label={currentPageIndex === pages.length - 1 && nextChapter ? 'Sang chương kế' : inQuickSet ? 'Ảnh kế tiếp' : 'Trang kế tiếp'}
          >
            <span className="material-symbols-outlined text-[20px]">chevron_right</span>
          </button>
        </div>

        {/* View Mode & Actions */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-gradient-to-r from-pink-500 to-rose-400 text-white shadow-xs hover:shadow-md hover:from-pink-600 hover:to-rose-500 text-xs font-semibold transition-all"
          >
            <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
            <span>Tải ảnh dịch</span>
          </button>

          {/* Ba dạng hiển thị của trang */}
          <div data-tour="reader-modes" className="flex items-center bg-slate-100 p-1 rounded-2xl border border-slate-200/60 text-xs font-medium dark:bg-[#1e293b] dark:border-slate-700">
            {modeButton('bubble', 'chat_bubble', 'Bóng Thoại (Overlay)', true, '')}
            {modeButton('inpainted', 'ink_eraser', 'Đã xóa chữ', !!reading?.variants.inpainted, awaitingTranslation ? stageHint : 'Trang chưa được xử lý xong')}
            {modeButton('rendered', 'translate', 'Đã đắp chữ', !!reading?.variants.rendered, awaitingTranslation ? stageHint : 'Trang chưa được xử lý xong')}
          </div>

          <button
            onClick={handleDownload}
            disabled={!variantUrl}
            className="w-9 h-9 rounded-xl bg-white border border-pink-100 text-slate-500 hover:text-[#a43073] hover:border-pink-300 flex items-center justify-center shadow-xs transition-all disabled:opacity-40 dark:bg-slate-800 dark:border-pink-900/40 dark:text-slate-400 dark:hover:text-pink-300"
            title="Tải ảnh đang xem về máy"
          >
            <Download size={18}/>
          </button>

          <button
            onClick={() => openReport(null)}
            disabled={!activePage}
            className="w-9 h-9 rounded-xl bg-white border border-pink-100 text-slate-500 hover:text-[#a43073] hover:border-pink-300 flex items-center justify-center shadow-xs transition-all disabled:opacity-40 dark:bg-slate-800 dark:border-pink-900/40 dark:text-slate-400 dark:hover:text-pink-300"
            title="Báo lỗi trang này"
            aria-label="Báo lỗi trang này"
          >
            <span className="material-symbols-outlined text-[18px]">flag</span>
          </button>

          <button
            onClick={toggleSavePage}
            className="w-9 h-9 rounded-xl bg-white border border-pink-100 text-slate-500 hover:text-[#a43073] hover:border-pink-300 flex items-center justify-center shadow-xs transition-all dark:bg-slate-800 dark:border-pink-900/40 dark:text-slate-400 dark:hover:text-pink-300"
            title={isBookmarked ? 'Bỏ lưu trang này' : 'Lưu trang này'}
          >
            {isBookmarked ? <BookmarkCheck size={18} className="text-[#a43073] dark:text-pink-400"/> : <Bookmark size={18}/>}
          </button>

          <TourReplayButton className="flex" />
        </div>

      </div>

      {savedSuccessMsg && (
        <div className="mb-4 p-3 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold flex items-center gap-2 animate-bounce dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-900/40">
          <span className="material-symbols-outlined text-[18px] text-emerald-600 dark:text-emerald-400">check_circle</span>
          <span>{savedSuccessMsg}</span>
        </div>
      )}

      {/* MAIN LAYOUT GRID (2 cols sidebar, 7 cols canvas, 3 cols study panel) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pb-28">

        {/* LEFT PAGE LIST (2 Cols): trang của chương hoặc bộ ảnh tải lên */}
        <ReaderPageSidebar
          heading={sidebarHeading}
          subheading={inQuickSet ? null : meta?.chapterTitle}
          pages={pages}
          currentIndex={currentPageIndex}
          labelOf={(page, idx) => (inQuickSet ? `Ảnh ${idx + 1}` : `Trang ${page.page_no}`)}
          liveStatus={liveStatus}
          onSelect={goToPage}
          onOpenUpload={onOpenUpload}
        />

        {/* CENTRAL MANHUA CANVAS (7 Cols) */}
        {/* `relative z-0`: cô lập các lớp z-index bên trong khung ảnh để không đè lên bảng chọn ở thanh đầu trang. */}
        <section className="relative z-0 col-span-1 lg:col-span-7 flex flex-col items-center">
          <div className="relative w-full max-w-2xl bg-white p-3 sm:p-4 rounded-3xl shadow-soft border border-pink-100 transition-all dark:bg-slate-800 dark:border-pink-900/40">

            {/* Status Pill Top Right */}
            <div className="absolute top-6 right-6 z-20 flex items-center gap-2 bg-white/95 backdrop-blur-md px-3 py-1 rounded-full shadow-md border border-pink-100 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:border-pink-900/40 dark:text-slate-100">
              {effectiveStatus === 'done' ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                  <span>Dịch trực tiếp: Tiếng Việt</span>
                </>
              ) : (
                <StatusPill status={effectiveStatus} textReady={textReady} />
              )}
            </div>

            {/* Trạng thái xử lý: đang chờ, đang xử lý hoặc lỗi */}
            {(awaitingTranslation || effectiveStatus === 'failed') && reading && (
              <div className={`mb-3 p-3 rounded-2xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${effectiveStatus === 'failed' ? 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-900/40 dark:text-red-300' : 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-900/30 dark:border-amber-900/40 dark:text-amber-300'} dark:border-red-900/40`} role="status">
                <span>
                  {effectiveStatus === 'failed'
                    ? (failureMessage ?? 'Xử lý ảnh không thành công.')
                    : effectiveStatus === 'running' || textReady
                      ? (textReady
                        ? 'Đã có chữ và bản dịch, bạn có thể bắt đầu học. Đang xóa chữ và đắp bản dịch lên ảnh…'
                        : 'Đang nhận diện chữ…')
                      : 'Trang đang xếp hàng chờ xử lý. Đang hiển thị ảnh gốc, bản dịch sẽ tự hiện khi xong.'}
                  {showingOriginalAsFallback && ' Đang hiển thị ảnh gốc, ảnh đã xử lý sẽ tự hiện khi xong.'}
                  {timedOut && ' Đã chờ lâu, bộ xử lý ảnh có thể đang bận; bạn có thể quay lại sau.'}
                </span>
                {effectiveStatus === 'failed' && canEditPage && (
                  <button onClick={handleRetranslate} disabled={retranslating} className="shrink-0 px-4 py-1.5 rounded-full bg-white border border-red-200 text-red-700 font-bold hover:bg-red-100 disabled:opacity-60 dark:bg-slate-800 dark:border-red-900/40 dark:text-red-400 dark:hover:bg-red-900/40">
                    {retranslating ? 'Đang gửi...' : 'Dịch lại'}
                  </button>
                )}
              </div>
            )}

            {/* Comic Canvas Wrapper */}
            <div id="canvas-wrapper" data-tour="reader-canvas" className="relative scroll-mt-24 rounded-2xl border border-slate-100 shadow-inner bg-slate-50 min-h-[16rem] dark:border-slate-700 dark:bg-[#1e293b]">
              <div className="absolute left-3 top-3 z-50">
                <button type="button" onClick={() => setIsStudyMenuOpen(open => !open)} aria-expanded={isStudyMenuOpen} aria-label="Mở công cụ ghi chú" title="Công cụ học tập và ghi chú" className={`flex h-10 w-10 items-center justify-center rounded-full border shadow-lg transition ${annotationTool !== 'none' ? 'border-pink-300 bg-pink-500 text-white dark:border-pink-900/40' : 'border-white bg-white/95 text-slate-700 hover:text-pink-600 dark:bg-slate-800 dark:text-slate-100'} dark:bg-slate-800`}>
                  <PenLine size={18}/>
                </button>
                {studyToolsMenu}
              </div>

              {readingError ? (
                <div className="p-10 text-center text-sm text-red-700 flex flex-col items-center gap-3 dark:text-red-400">
                  <span className="material-symbols-outlined text-[36px] text-red-300">error</span>
                  <p>{readingError.message}</p>
                  <button onClick={() => setReadingTick(value => value + 1)} className="px-4 py-2 rounded-full bg-white border border-red-200 text-xs font-bold hover:bg-red-50 dark:bg-slate-800 dark:border-red-900/40 dark:hover:bg-red-900/40">Thử lại</button>
                </div>
              ) : (
                <AuthImage
                  src={variantUrl ?? (showingOriginalAsFallback ? imageFallback : null)}
                  alt={`Trang ${activePage.page_no}`}
                  className={`w-full h-auto block select-none rounded-2xl ${readingLoading ? 'opacity-60' : ''}`}
                />
              )}

              <svg
                className={`absolute inset-0 z-40 h-full w-full ${annotationTool === 'draw' ? 'touch-none cursor-crosshair pointer-events-auto' : 'pointer-events-none'}`}
                viewBox="0 0 1000 1000"
                preserveAspectRatio="none"
                onPointerDown={startDrawing}
                onPointerMove={continueDrawing}
                onPointerUp={stopDrawing}
                onPointerCancel={stopDrawing}
                aria-label="Lớp ghi chú trên trang truyện"
              >
                {pageStrokes.map((stroke, index) => (
                  <polyline key={`${activePage.id}-stroke-${index}`} points={stroke.points.map(point => `${point.x},${point.y}`).join(' ')} fill="none" stroke={stroke.color} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                ))}
              </svg>

              {/* Speech Bubble Interactive Pins */}
              {overlaysVisible && bubbles.map((bubble, bIdx) => {
                if (bubble.x_pct === null || bubble.y_pct === null || bubble.w_pct === null || bubble.h_pct === null) return null;
                const isPink = !isNarration(bubble);
                const borderColor = isPink ? 'border-pink-500' : 'border-blue-500';
                const bgColor = isPink ? 'bg-pink-400/10 hover:bg-pink-400/25' : 'bg-blue-400/10 hover:bg-blue-400/25';
                const badgeColor = isPink ? 'bg-pink-500' : 'bg-blue-500';
                const shadowGlow = isPink ? 'shadow-[0_0_20px_rgba(244,114,182,0.35)]' : 'shadow-[0_0_20px_rgba(96,165,250,0.35)]';
                const directTextColor = isPink ? 'text-pink-900 border-pink-200' : 'text-blue-900 border-blue-200';
                const translation = bubble.text_vi_effective ?? bubble.text_vi ?? '';
                const popoverSide = `${bubble.x_pct > 50 ? 'right-0' : 'left-0'} ${bubble.y_pct > 60 ? 'bottom-full mb-2' : 'top-full mt-2'}`;
                const highlight = pageHighlights[String(bubble.id)];

                return (
                  <div
                    key={bubble.id}
                    style={{
                      top: `${bubble.y_pct}%`,
                      left: `${bubble.x_pct}%`,
                      width: `${bubble.w_pct}%`,
                      height: `${bubble.h_pct}%`
                    }}
                    onClick={() => {
                      if (annotationTool === 'highlight') handleBubbleAnnotation(bubble.id);
                      else handlePlayVoice(bubble.text_zh);
                    }}
                    className={`bubble-pin group absolute cursor-pointer z-30`}
                  >
                    {/* Highlight Box inside bubble */}
                    <div style={highlight ? { backgroundColor: `${highlight}33`, borderColor: highlight } : undefined} className={`w-full h-full rounded-xl border-2 ${borderColor} ${bgColor} ${shadowGlow} transition-all flex flex-col justify-between p-1.5`}>
                      <div className="flex items-center justify-between">
                        <span className={`${badgeColor} text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-xs flex items-center gap-1`}>
                          <span className="material-symbols-outlined text-[12px]">translate</span>
                          <span>Thoại {bIdx + 1}</span>
                        </span>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePlayVoice(bubble.text_zh);
                          }}
                          className={`w-5 h-5 rounded-full bg-white/90 hover:scale-110 ${isPink ? 'text-pink-600' : 'text-blue-600'} flex items-center justify-center text-[10px] shadow-xs`}
                          title="Nghe phát âm"
                        >
                          <span className="material-symbols-outlined text-[13px]">volume_up</span>
                        </button>
                      </div>

                      {/* Direct translation subtitle overlay (ảnh đã đắp chữ đã có bản dịch nên không chồng thêm) */}
                      {viewMode !== 'rendered' && translation && (
                        <div
                          style={{ fontSize: `${(BUBBLE_BASE_FONT_PX * fontScale) / 100}px` }}
                          className={`bubble-direct-trans bg-white/95 backdrop-blur-xs px-1.5 py-0.5 rounded font-semibold ${directTextColor} border leading-tight line-clamp-2`}
                        >
                          {translation}
                        </div>
                      )}
                    </div>

                    {/* Rich Hover Popover Card */}
                    <div className={`opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-all duration-300 transform -translate-y-2 group-hover:translate-y-0 absolute ${popoverSide} w-80 bg-white/95 backdrop-blur-xl p-4 rounded-2xl shadow-floating border border-pink-200 z-50`}>
                      <div className="flex items-center justify-between border-b border-pink-100 pb-2 mb-2">
                        <span className="text-[11px] font-bold text-pink-500 uppercase tracking-wider flex items-center gap-1">
                          <span className="material-symbols-outlined text-[14px]">format_quote</span>
                          <span>Lời thoại {bIdx + 1}</span>
                        </span>
                        {bubble.has_edit && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-medium">
                            Bản dịch của bạn
                          </span>
                        )}
                      </div>

                      <div className="mb-2">
                        <div className="text-xs font-mono text-slate-500">
                          {bubble.pinyin}
                        </div>
                        <div className="text-base font-['Noto_Serif_SC'] font-bold text-slate-800 mt-0.5">
                          {bubble.text_zh}
                        </div>
                      </div>

                      <div className="p-2 rounded-xl bg-pink-50/80 border border-pink-200 text-pink-900 text-xs font-semibold leading-relaxed flex items-start gap-1.5">
                        <span className="material-symbols-outlined text-pink-500 text-[14px] mt-0.5">edit</span>
                        <span>{translation ? `"${translation}"` : 'Chưa có bản dịch'}</span>
                      </div>

                      <div className="mt-2 flex items-center gap-2">
                        <button
                          onClick={(e) => { e.stopPropagation(); startEdit(bubble); }}
                          className="inline-flex items-center gap-1 rounded-full bg-slate-100 hover:bg-pink-100 px-2.5 py-1 text-[10px] font-bold text-slate-600 hover:text-pink-700"
                        >
                          <Pencil size={11}/>Sửa bản dịch
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); void handleSaveSentence(bubble.id); }}
                          disabled={savedSentenceIds.has(bubble.id) || savingSentenceIds.has(bubble.id)}
                          className="inline-flex items-center gap-1 rounded-full bg-slate-100 hover:bg-blue-100 px-2.5 py-1 text-[10px] font-bold text-slate-600 hover:text-blue-700 disabled:bg-emerald-50 disabled:text-emerald-700"
                          title={savedSentenceIds.has(bubble.id) ? 'Câu thoại đã lưu' : 'Lưu câu thoại này'}
                        >
                          <span className="material-symbols-outlined text-[12px]">{savedSentenceIds.has(bubble.id) ? 'bookmark_added' : 'bookmark_add'}</span>
                          {savedSentenceIds.has(bubble.id) ? 'Đã lưu' : savingSentenceIds.has(bubble.id) ? 'Đang lưu...' : 'Lưu câu'}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); openReport(bubble.id); }}
                          className="inline-flex items-center gap-1 rounded-full bg-slate-100 hover:bg-rose-100 px-2.5 py-1 text-[10px] font-bold text-slate-600 hover:text-rose-700"
                          title="Báo lỗi nhận diện hoặc bản dịch của câu này"
                        >
                          <span className="material-symbols-outlined text-[12px]">flag</span>Báo lỗi
                        </button>
                        {bubble.has_edit && (
                          <button
                            onClick={(e) => { e.stopPropagation(); void undoEdit(bubble.id); }}
                            className="inline-flex items-center gap-1 rounded-full bg-slate-100 hover:bg-amber-100 px-2.5 py-1 text-[10px] font-bold text-slate-600 hover:text-amber-800"
                          >
                            <Undo2 size={11}/>Hoàn tác
                          </button>
                        )}
                      </div>

                      {/* Vocabulary Breakdown Chips */}
                      {bubble.tokens.some(token => HAS_CJK.test(token.word)) && (
                        <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-1.5 text-[10px]">
                          {bubble.tokens.filter(token => HAS_CJK.test(token.word)).map((token, cIdx) => (
                            <span
                              key={cIdx}
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePlayVoice(token.word);
                                void lookupWord(bubble.id, token.word);
                              }}
                              className="bg-slate-100 hover:bg-pink-100 hover:text-pink-600 px-2 py-0.5 rounded-md text-slate-600 font-medium cursor-pointer transition-colors"
                              title="Bấm để nghe và tra nghĩa"
                            >
                              {token.word}{token.pinyin ? ` (${token.pinyin})` : ''}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Hint bar at bottom of canvas */}
            <div className="mt-3 flex flex-wrap items-center justify-between text-xs text-slate-500 px-2 gap-2 dark:text-slate-400">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-pink-400"></span>
                  <span>Khung hồng: Hội thoại / Ngữ pháp</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-400"></span>
                  <span>Khung xanh: Dẫn truyện</span>
                </span>
              </div>
              <span className="text-slate-400 text-[11px] flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">touch_app</span>
                <span>Chạm vào khung để nghe đọc</span>
              </span>
            </div>

          </div>
        </section>

        {/* RIGHT STUDY PANEL (3 Cols) */}
        <aside className="col-span-1 lg:col-span-3 flex flex-col gap-5 sticky top-24">

          {/* Card: Sửa bản dịch */}
          {editing && (
            <div className="bg-white rounded-3xl p-5 shadow-soft border border-amber-200 dark:bg-slate-800 dark:border-amber-900/40">
              <div className="flex items-center gap-2 mb-2 text-xs font-bold text-amber-800 dark:text-amber-300">
                <Pencil size={14}/>Sửa bản dịch của bạn
              </div>
              <textarea
                value={editing.text}
                onChange={event => setEditing({ ...editing, text: event.target.value })}
                maxLength={1000}
                rows={4}
                className="w-full text-xs text-slate-700 p-2.5 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-[#f472b6] dark:text-slate-100 dark:border-slate-700"
                aria-label="Bản dịch tiếng Việt"
              />
              <div className="flex items-center justify-end gap-2 mt-2">
                <button onClick={() => setEditing(null)} className="px-3 py-1.5 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700">Hủy</button>
                <button onClick={submitEdit} disabled={editBusy} className="px-4 py-1.5 rounded-full bg-[#a43073] text-white text-xs font-bold hover:bg-[#85145a] disabled:opacity-60">
                  {editBusy ? 'Đang lưu...' : 'Lưu bản dịch'}
                </button>
              </div>
              <p className="text-[10px] text-slate-400 mt-2">Bản sửa chỉ hiện với riêng bạn; có thể hoàn tác bất cứ lúc nào.</p>
            </div>
          )}

          {/* Card: Tra nhanh từ trong bong bóng */}
          {lookupCard && (
            <div className="bg-white rounded-3xl p-5 shadow-soft border border-blue-100 dark:bg-slate-800 dark:border-blue-900/40">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-blue-700 uppercase tracking-wide dark:text-blue-400">Tra nhanh</span>
                <button onClick={() => setLookupCard(null)} className="text-slate-400 hover:text-slate-700 dark:hover:text-white" aria-label="Đóng"><span className="material-symbols-outlined text-[16px]">close</span></button>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-['Noto_Serif_SC'] text-xl font-bold text-slate-800 dark:text-slate-100">{lookupCard.word}</span>
                <button onClick={() => handlePlayVoice(lookupCard.word)} className="w-7 h-7 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center dark:bg-blue-900/30 dark:text-blue-400" title="Phát âm"><span className="material-symbols-outlined text-[16px]">volume_up</span></button>
              </div>
              {lookupCard.status === 'loading' && <p className="text-xs text-slate-500 mt-2 dark:text-slate-400">Đang tra từ...</p>}
              {lookupCard.status === 'error' && <p className="text-xs text-red-600 mt-2 dark:text-red-400">{lookupCard.message}</p>}
              {lookupCard.status === 'limit' && (
                <div className="mt-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-3 dark:text-amber-300 dark:bg-amber-900/30 dark:border-amber-900/40">
                  <p>{lookupCard.message}</p>
                  <button onClick={() => onRequireLogin('Bạn đã dùng hết lượt tra thử. Đăng nhập để tra từ không giới hạn!')} className="mt-2 px-3 py-1.5 rounded-full bg-[#a43073] text-white font-bold">Đăng nhập để tra tiếp</button>
                </div>
              )}
              {lookupCard.status === 'ok' && lookupCard.data && (
                <div className="mt-1 text-xs text-slate-600 space-y-1.5 dark:text-slate-300">
                  <div className="flex flex-wrap items-center gap-2">
                    {lookupCard.data.pinyin && <span className="font-mono text-blue-600 dark:text-blue-400">{lookupCard.data.pinyin}</span>}
                    {lookupCard.data.han_viet && <span className="text-slate-500 dark:text-slate-400">· {lookupCard.data.han_viet}</span>}
                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] font-bold dark:bg-amber-900/30 dark:text-amber-300">{hskLabel(lookupCard.data.hsk.level)}</span>
                  </div>
                  {!lookupCard.data.found && <p>Chưa có trong từ điển.</p>}
                  {lookupCard.data.readings.slice(0, 1).flatMap(reading => reading.definitions.slice(0, 3)).map((definition, index) => (
                    <p key={index}>• {definition.gloss}</p>
                  ))}
                  {lookupCard.data.limited && (
                    <p className="text-[11px] text-amber-700 dark:text-amber-400">Khách chỉ xem phần cơ bản. Đăng nhập để xem đầy đủ nghĩa, ví dụ và phân rã chữ Hán.</p>
                  )}
                  <div className="flex flex-wrap items-center gap-3 pt-1">
                    <button
                      onClick={() => void saveVocabulary(lookupCard.word, lookupCard.bubbleId)}
                      disabled={isSaved(lookupCard.word) || isSaving(lookupCard.word)}
                      className="inline-flex items-center gap-1 rounded-full bg-pink-50 px-3 py-1.5 text-[11px] font-bold text-[#a43073] hover:bg-pink-100 disabled:bg-emerald-50 disabled:text-emerald-700 dark:bg-pink-900/30 dark:text-pink-400 dark:hover:bg-pink-900/40"
                    >
                      <span className="material-symbols-outlined text-[14px]">{isSaved(lookupCard.word) ? 'check' : 'bookmark_add'}</span>
                      {isSaved(lookupCard.word)
                        ? 'Đã lưu vào Sổ tay'
                        : isSaving(lookupCard.word)
                          ? 'Đang lưu...'
                          : isInNotebook(lookupCard.word)
                            ? 'Đã có · thêm ngữ cảnh trang này'
                            : 'Lưu vào Sổ tay'}
                    </button>
                    <button onClick={() => onLookupWord(lookupCard.word)} className="text-[11px] font-bold text-[#a43073] hover:underline dark:text-pink-400">Xem chi tiết đầy đủ</button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Card: Vocabulary on this page */}
          <div data-tour="reader-vocab" className="bg-white rounded-3xl p-5 shadow-soft border border-pink-100 dark:bg-slate-800 dark:border-pink-900/40">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-xl bg-pink-100 flex items-center justify-center text-pink-600 text-xs font-bold dark:bg-pink-900/30 dark:text-pink-400">
                  <span className="material-symbols-outlined text-[16px]">school</span>
                </div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">Từ vựng trang này</h3>
              </div>
              <span className="text-xs font-semibold text-[#a43073] bg-pink-50 px-2 py-0.5 rounded-full dark:text-pink-400 dark:bg-pink-900/30">
                {vocabulary.length} từ
              </span>
            </div>

            <div className="space-y-2.5 max-h-[22rem] overflow-y-auto custom-scrollbar pr-1">
              {vocabulary.length === 0 && (
                <p className="text-xs text-slate-400 text-center py-4">
                  {awaitingTranslation ? 'Từ vựng sẽ hiện khi trang được xử lý xong.' : 'Trang này chưa có từ vựng nhận diện được.'}
                </p>
              )}
              {vocabulary.map(vocab => (
                <div
                  key={vocab.word}
                  onClick={() => { handlePlayVoice(vocab.word); void lookupWord(vocab.bubbleId, vocab.word); }}
                  className="p-2.5 rounded-2xl bg-slate-50 hover:bg-pink-50/60 border border-slate-100 hover:border-pink-200 transition-all cursor-pointer group dark:bg-[#1e293b] dark:border-slate-700"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-['Noto_Serif_SC'] font-bold text-base text-slate-800 group-hover:text-[#a43073] dark:text-slate-100">
                          {vocab.word}
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono dark:text-slate-400">
                          {vocab.pinyin}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600 font-medium dark:text-slate-300">
                        {meaningOf(lookupCache.current.get(vocab.word)) || 'Bấm để xem nghĩa'}
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePlayVoice(vocab.word);
                        }}
                        className="w-7 h-7 rounded-lg bg-white group-hover:bg-pink-200/60 text-slate-400 group-hover:text-pink-600 flex items-center justify-center text-xs transition-colors dark:bg-slate-800"
                        title="Phát âm"
                      >
                        <span className="material-symbols-outlined text-[16px]">volume_up</span>
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); void saveVocabulary(vocab.word, vocab.bubbleId); }}
                        disabled={isSaved(vocab.word) || isSaving(vocab.word)}
                        className="w-7 h-7 rounded-lg bg-white text-slate-400 hover:bg-blue-100 hover:text-blue-700 disabled:text-emerald-600 disabled:bg-emerald-50 flex items-center justify-center transition-colors dark:bg-slate-800 dark:hover:bg-blue-900/40"
                        title={isSaved(vocab.word) ? 'Đã lưu vào Sổ tay' : isInNotebook(vocab.word) ? 'Đã có trong Sổ tay — bấm để thêm ngữ cảnh từ trang này' : 'Lưu từ vào Sổ tay'}
                      >
                        <span className={`material-symbols-outlined text-[16px] ${!isSaved(vocab.word) && isInNotebook(vocab.word) ? 'text-blue-600 dark:text-blue-400' : ''}`}>
                          {isSaved(vocab.word) ? 'check' : isInNotebook(vocab.word) ? 'bookmark_added' : 'style'}
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={handleSaveAllVocab}
              disabled={vocabulary.length === 0 || savingAllWords}
              className="w-full mt-3 py-2 bg-pink-50 hover:bg-pink-100 text-[#a43073] text-xs font-bold rounded-2xl border border-pink-200 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 dark:bg-pink-900/30 dark:hover:bg-pink-900/40 dark:text-pink-400 dark:border-pink-900/40"
            >
              <span className="material-symbols-outlined text-[14px]">add</span>
              <span>{savingAllWords ? 'Đang lưu...' : pendingMoreWords > 0 ? `Lưu tiếp ${pendingMoreWords} từ còn lại` : 'Lưu toàn bộ vào Sổ tay'}</span>
            </button>
          </div>

          {/* Card: Độ phủ từ vựng của chương (F10.05) */}
          <ChapterCoverageBar
            chapterId={meta?.chapterId ?? null}
            isLoggedIn={isLoggedIn}
            refreshKey={coverageTick}
            onOpenLearningSettings={onOpenLearningSettings}
          />

          {/* Card: Từ nên học trong chương (M10) */}
          <ChapterSuggestions
            chapterId={meta?.chapterId ?? null}
            isLoggedIn={isLoggedIn}
            onRequireLogin={onRequireLogin}
            onGoToPage={pageNo => {
              const index = pages.findIndex(page => page.page_no === pageNo);
              if (index >= 0) goToPage(index);
            }}
            onOpenLearningSettings={onOpenLearningSettings}
          />

          {/* Card: Cấu trúc trọng điểm — phân tích ngữ pháp bằng AI (F05.09) */}
          <GrammarPanel
            bubbles={bubbles}
            preferredBubbleId={lookupCard?.bubbleId ?? null}
            pageId={activePageId}
            isLoggedIn={isLoggedIn}
            onRequireLogin={onRequireLogin}
          />

          {/* Card: Streak */}
          <div className="bg-white rounded-3xl p-4 shadow-soft border border-amber-100 flex items-center justify-between dark:bg-slate-800 dark:border-amber-900/40">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-100 flex items-center justify-center text-amber-500 text-lg dark:bg-amber-900/30">
                🔥
              </div>
              <div>
                <div className="text-xs font-bold text-slate-800 dark:text-slate-100">
                  {streak ? `Chuỗi học ${streak.current_streak} ngày` : 'Chuỗi ngày học'}
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  {streak
                    ? `Đã đọc ${streak.week[streak.week.length - 1]?.pages_read ?? 0} trang hôm nay`
                    : isLoggedIn ? 'Đang tải...' : 'Đăng nhập để theo dõi chuỗi học'}
                </div>
              </div>
            </div>
            {/* TODO(M16): XP chưa có API (GĐ6.5); giữ hiển thị như thiết kế. */}
            <span className="text-xs font-bold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-xl border border-amber-200 dark:text-amber-400 dark:bg-amber-900/30 dark:border-amber-900/40">
              +50 XP
            </span>
          </div>

        </aside>

      </div>

      {/* FLOATING GLASS DOCK (Bottom Controls) */}
      <div className="fixed bottom-5 inset-x-0 mx-auto w-fit z-40 transition-all">
        <div className="glass-dock rounded-full px-5 py-2.5 flex items-center gap-4 border border-white/80">

          {/* Navigation */}
          <div className="flex items-center gap-1.5 border-r border-slate-200/80 pr-3 dark:border-slate-700">
            <button
              onClick={prevPage}
              className="w-9 h-9 rounded-full bg-slate-100/80 hover:bg-pink-100 text-slate-600 hover:text-pink-600 flex items-center justify-center transition-all shadow-xs dark:bg-[#1e293b] dark:hover:bg-pink-900/40 dark:text-slate-300"
              title="Trang trước"
            >
              <span className="material-symbols-outlined text-[18px]">skip_previous</span>
            </button>
            <div className="text-center px-2">
              <span className="text-xs font-bold text-slate-700 block leading-tight dark:text-slate-100">
                Trang {currentPageIndex + 1}
              </span>
              <span className="text-[10px] text-slate-400 block font-medium">{pages.length} trang</span>
            </div>
            <button
              onClick={nextPage}
              className="w-9 h-9 rounded-full bg-slate-100/80 hover:bg-pink-100 text-slate-600 hover:text-pink-600 flex items-center justify-center transition-all shadow-xs dark:bg-[#1e293b] dark:hover:bg-pink-900/40 dark:text-slate-300"
              title="Trang tiếp"
            >
              <span className="material-symbols-outlined text-[18px]">skip_next</span>
            </button>
          </div>

          {/* Full Page Read Button */}
          <div data-tour="reader-listen" className="flex items-center gap-2 border-r border-slate-200/80 pr-3 dark:border-slate-700">
            <button
              onClick={handleReadEntirePage}
              disabled={isPlayingFullPage || bubbles.length === 0}
              className={`px-4 py-2 rounded-full text-white font-semibold text-xs flex items-center gap-2 shadow-md shadow-pink-300/40 hover:scale-105 transition-all disabled:opacity-60 ${
                isPlayingFullPage
                  ? 'bg-pink-400 animate-pulse'
                  : 'bg-gradient-to-r from-pink-500 to-rose-400 hover:from-pink-600 hover:to-rose-500'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">
                {isPlayingFullPage ? 'volume_up' : 'play_circle'}
              </span>
              <span>{isPlayingFullPage ? 'Đang đọc...' : 'Đọc thoại toàn trang'}</span>
            </button>

            <button
              onClick={cycleSpeed}
              className="w-8 h-8 rounded-full bg-slate-100/80 hover:bg-slate-200 text-slate-600 text-xs font-bold transition-colors dark:bg-[#1e293b] dark:hover:bg-slate-700 dark:text-slate-300"
              title="Tốc độ đọc"
            >
              {speechRate}x
            </button>
          </div>

          {/* Font Resize */}
          <div className="flex items-center gap-1 border-r border-slate-200/80 pr-3 dark:border-slate-700">
            <button
              onClick={() => changeFontSize(-1)}
              className="w-7 h-7 rounded-full hover:bg-slate-100 text-slate-600 flex items-center justify-center text-xs dark:hover:bg-slate-700 dark:text-slate-300"
              title="Giảm cỡ chữ"
            >
              A-
            </button>
            <span className="text-xs font-mono font-semibold text-slate-600 px-1 min-w-[2.75rem] text-center dark:text-slate-300" title="Cỡ chữ bản dịch">{fontScale}%</span>
            <button
              onClick={() => changeFontSize(1)}
              className="w-7 h-7 rounded-full hover:bg-slate-100 text-slate-600 flex items-center justify-center text-xs dark:hover:bg-slate-700 dark:text-slate-300"
              title="Tăng cỡ chữ"
            >
              A+
            </button>
          </div>

          {/* Overlay Toggle */}
          <button
            onClick={() => setOverlaysVisible(!overlaysVisible)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              overlaysVisible
                ? 'bg-pink-100 text-[#a43073] hover:bg-pink-200 dark:bg-pink-900/30 dark:text-pink-400 dark:hover:bg-pink-900/40'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-[#1e293b] dark:text-slate-300 dark:hover:bg-slate-700'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">
              {overlaysVisible ? 'visibility' : 'visibility_off'}
            </span>
            <span>{overlaysVisible ? 'Ẩn bản dịch' : 'Hiện bản dịch'}</span>
          </button>

        </div>
      </div>

      {reportTarget && (
        <ReportErrorDialog target={reportTarget} onClose={() => setReportTarget(null)} onDone={showMessage} />
      )}

    </div>
  );
};
