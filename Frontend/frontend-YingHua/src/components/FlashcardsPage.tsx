import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiDeck, listDecks, listVocab } from '../api/vocab';
import { ReviewSummary, getReviewSummary } from '../api/review';
import { ReaderTarget } from '../types';
import { formatDateTime } from '../utils/format';
import { QuizSection } from './QuizSection';
import { ReviewRoom } from './ReviewRoom';
import { VocabNotebook } from './VocabNotebook';

interface FlashcardsPageProps {
  onNavigateToReader: () => void;
  onOpenReader: (target: ReaderTarget) => void;
  showToast: (message: string) => void;
  /** true khi nơi khác (nhiệm vụ ngày) muốn đưa người học tới khu Kiểm tra cá nhân hóa. */
  focusQuiz?: boolean;
  onFocusQuizHandled?: () => void;
}

interface NotebookCounts {
  total: number;
  learning: number;
  known: number;
  ignored: number;
  /** Số từ có thẻ đến hạn; null khi máy chủ chưa trả về. */
  dueWords: number | null;
}

type DeckKindFilter = 'all' | 'series' | 'starred';

const ALL_DECK_KEY = 'all';
const ALL_DECK_TITLE = 'Tất cả từ vựng';

const DECK_BADGE: Record<ApiDeck['kind'] | 'all', { label: string; color: string }> = {
  all: { label: 'Tất cả', color: 'bg-pink-100 text-[#85145a]' },
  starred: { label: 'Yêu thích ⭐', color: 'bg-amber-100 text-amber-900' },
  series: { label: 'Bộ truyện', color: 'bg-blue-100 text-blue-900' }
};

const percent = (part: number, whole: number): number => (whole > 0 ? Math.round((part / whole) * 100) : 0);

export const FlashcardsPage: React.FC<FlashcardsPageProps> = ({ onNavigateToReader, onOpenReader, showToast, focusQuiz = false, onFocusQuizHandled }) => {
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [decks, setDecks] = useState<ApiDeck[]>([]);
  const [counts, setCounts] = useState<NotebookCounts | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [statsTick, setStatsTick] = useState(0);
  const [selectedDeck, setSelectedDeck] = useState<string>(ALL_DECK_KEY);
  const [deckKindFilter, setDeckKindFilter] = useState<DeckKindFilter>('all');
  const [startTick, setStartTick] = useState(0);
  const [shuffleTick, setShuffleTick] = useState(0);
  const roomRef = useRef<HTMLDivElement | null>(null);
  const [quizFocusTick, setQuizFocusTick] = useState(0);

  useEffect(() => {
    if (!focusQuiz) return;
    setQuizFocusTick(value => value + 1);
    onFocusQuizHandled?.();
  }, [focusQuiz, onFocusQuizHandled]);

  // Số liệu đầu trang, bộ thẻ và tổng kết ôn tập đều lấy từ máy chủ; một phần lỗi không chặn phần còn lại.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [sum, deckList, total] = await Promise.allSettled([getReviewSummary(), listDecks(), listVocab({ size: 1 })]);
      if (cancelled) return;
      if (sum.status === 'fulfilled') setSummary(sum.value);
      if (deckList.status === 'fulfilled') setDecks(deckList.value);
      if (total.status === 'fulfilled') {
        // Ưu tiên số liệu theo trạng thái từ /review/summary; máy chủ cũ chưa có thì đếm bằng danh sách.
        const byStatus = sum.status === 'fulfilled' ? sum.value.status_counts : undefined;
        let statusCounts = byStatus;
        if (!statusCounts) {
          const [learning, known, ignored] = await Promise.allSettled([
            listVocab({ status: 'learning', size: 1 }),
            listVocab({ status: 'known', size: 1 }),
            listVocab({ status: 'ignored', size: 1 })
          ]);
          if (cancelled) return;
          statusCounts = {
            learning: learning.status === 'fulfilled' ? learning.value.total : 0,
            known: known.status === 'fulfilled' ? known.value.total : 0,
            ignored: ignored.status === 'fulfilled' ? ignored.value.total : 0
          };
        }
        setCounts({
          total: total.value.total,
          ...statusCounts,
          dueWords: sum.status === 'fulfilled' ? (sum.value.due_words ?? null) : null
        });
        setStatsError(null);
      } else {
        setStatsError('Không tải được số liệu Sổ tay.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [statsTick]);

  const refreshStats = useCallback(() => setStatsTick(value => value + 1), []);

  // Bộ thẻ đang chọn không còn tồn tại (vd. xóa hết từ của truyện): quay về "Tất cả".
  useEffect(() => {
    if (selectedDeck !== ALL_DECK_KEY && decks.length > 0 && !decks.some(deck => deck.key === selectedDeck)) {
      setSelectedDeck(ALL_DECK_KEY);
    }
  }, [decks, selectedDeck]);

  const deckTitle = selectedDeck === ALL_DECK_KEY ? ALL_DECK_TITLE : (decks.find(deck => deck.key === selectedDeck)?.title ?? ALL_DECK_TITLE);

  const startReview = (deckKey: string) => {
    setSelectedDeck(deckKey);
    setStartTick(value => value + 1);
    roomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const visibleDecks = useMemo(
    () => decks.filter(deck => deckKindFilter === 'all' || deck.kind === deckKindFilter),
    [decks, deckKindFilter]
  );

  const busiestDeck = useMemo(
    () => [...decks].filter(deck => deck.due_count > 0).sort((a, b) => b.due_count - a.due_count)[0] ?? null,
    [decks]
  );

  const total = counts?.total ?? 0;
  const dueNow = summary?.due_now ?? 0;

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-10">
      {/* TOP PROGRESS & SUMMARY BENTO */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 shadow-soft border border-pink-100 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full bg-pink-100/50 blur-2xl pointer-events-none"></div>
          <div className="absolute right-1/3 bottom-0 w-32 h-32 rounded-full bg-blue-100/40 blur-xl pointer-events-none"></div>

          <div className="flex flex-col gap-2 relative z-10">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] font-bold text-xs shadow-xs">
                <span>🌸</span> SRS Spaced Repetition Hệ Thống
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {summary ? `Hôm nay bạn đã ôn ${summary.reviewed_today} lượt` : 'Đang tải số liệu ôn tập...'}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans']">Từ Vựng & Flashcard Theo Manhua</h1>
            <p className="text-xs sm:text-sm text-slate-600 max-w-xl leading-relaxed">
              Tập trung học sâu từ vựng bản xứ trích xuất trực tiếp qua từng khung tranh truyện. Ôn tập đúng nhịp độ khoa học, biến kiến thức thụ động thành phản xạ giao tiếp tự nhiên.
            </p>
          </div>

          <div className="mt-6 pt-4 flex flex-col gap-3 relative z-10">
            <div className="flex items-baseline justify-between gap-2 flex-wrap">
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-[#a43073] font-['Plus_Jakarta_Sans']">{counts ? total : '–'}</span>
                <span className="text-xs text-slate-500 font-semibold">tổng từ vựng trong Sổ tay</span>
              </div>
              <span className="text-xs text-[#0060ac] font-bold bg-blue-100 px-3 py-1 rounded-full">
                {counts && total > 0 ? `${percent(counts.known, total)}% đã thuộc` : 'Chưa có từ nào'}
              </span>
            </div>

            <div className="w-full h-3 rounded-full bg-slate-100 flex overflow-hidden p-0.5">
              <div className="h-full bg-[#a43073] rounded-full" style={{ width: `${percent(counts?.known ?? 0, total)}%` }} title={`Đã thuộc: ${counts?.known ?? 0}`}></div>
              <div className="h-full bg-[#64a8fe] rounded-full mx-0.5" style={{ width: `${percent(counts?.learning ?? 0, total)}%` }} title={`Đang học: ${counts?.learning ?? 0}`}></div>
              <div className="h-full bg-amber-400 rounded-full" style={{ width: `${percent(counts?.ignored ?? 0, total)}%` }} title={`Tạm bỏ qua: ${counts?.ignored ?? 0}`}></div>
            </div>

            <div className={`grid gap-3 pt-1 ${counts?.dueWords != null ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-3'}`}>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#a43073]"></span>
                <div className="flex flex-col">
                  <span className="text-xs text-slate-800 font-bold">{counts?.known ?? 0} từ</span>
                  <span className="text-[10px] text-slate-500">Đã thuộc</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#64a8fe]"></span>
                <div className="flex flex-col">
                  <span className="text-xs text-slate-800 font-bold">{counts?.learning ?? 0} từ</span>
                  <span className="text-[10px] text-slate-500">Đang học</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                <div className="flex flex-col">
                  <span className="text-xs text-slate-800 font-bold">{counts?.ignored ?? 0} từ</span>
                  <span className="text-[10px] text-slate-500">Tạm bỏ qua</span>
                </div>
              </div>
              {counts?.dueWords != null && (
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-400"></span>
                  <div className="flex flex-col">
                    <span className="text-xs text-slate-800 font-bold">{counts.dueWords} từ</span>
                    <span className="text-[10px] text-slate-500">Cần xem lại</span>
                  </div>
                </div>
              )}
            </div>
            {statsError && (
              <button onClick={refreshStats} className="self-start text-xs font-bold text-rose-600 hover:underline">{statsError} Bấm để thử lại.</button>
            )}
          </div>
        </div>

        <div className="lg:col-span-5 bg-gradient-to-br from-[#eff4ff] to-white rounded-3xl p-6 sm:p-8 shadow-soft border border-pink-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-bold text-[#a43073] uppercase tracking-wider">Hôm Nay Cần Học</span>
              <div className="text-2xl font-bold text-slate-800 mt-1">{summary ? `${dueNow} Thẻ Đến Hạn` : 'Đang tải...'}</div>
              {summary && dueNow === 0 && summary.next_due_at && (
                <div className="text-xs text-slate-500 mt-1">Thẻ kế tiếp đến hạn lúc {formatDateTime(summary.next_due_at)}</div>
              )}
              {summary && dueNow > 0 && summary.due_later_today > 0 && (
                <div className="text-xs text-slate-500 mt-1">Còn {summary.due_later_today} thẻ nữa sẽ đến hạn trong hôm nay</div>
              )}
            </div>
            <div className="w-12 h-12 rounded-2xl bg-pink-100 flex items-center justify-center text-[#a43073] shadow-xs">
              <span className="material-symbols-outlined text-[26px]">psychology</span>
            </div>
          </div>

          <div className="my-4 p-3.5 bg-white rounded-2xl shadow-xs border border-pink-100/60 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center text-blue-700">
              <span className="material-symbols-outlined text-[22px]">auto_stories</span>
            </div>
            <div className="flex flex-col min-w-0 flex-1">
              {busiestDeck ? (
                <>
                  <span className="text-xs font-bold text-slate-800 truncate">{busiestDeck.title}</span>
                  <span className="text-[11px] text-slate-500">Có {busiestDeck.due_count} thẻ đến hạn trong bộ này</span>
                </>
              ) : (
                <>
                  <span className="text-xs font-bold text-slate-800">Lưu thêm từ khi đọc truyện</span>
                  <span className="text-[11px] text-slate-500">Mỗi từ lưu sẽ có ảnh ngữ cảnh và 3 thẻ ôn</span>
                </>
              )}
            </div>
            {busiestDeck ? (
              <button onClick={() => startReview(busiestDeck.key)} className="text-xs font-bold text-[#a43073] hover:underline">Ôn bộ này</button>
            ) : (
              <button onClick={onNavigateToReader} className="text-xs font-bold text-[#a43073] hover:underline">Đọc truyện</button>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => startReview(selectedDeck)}
              className="flex-1 py-3 px-4 bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs sm:text-sm rounded-full shadow-md transition-all flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">play_circle</span>
              <span>Ôn Tập Ngay{summary ? ` (${dueNow} thẻ)` : ''}</span>
            </button>
            <button
              onClick={() => setShuffleTick(value => value + 1)}
              className="w-11 h-11 rounded-full bg-white hover:bg-slate-100 text-slate-600 flex items-center justify-center shadow-xs border border-slate-200 transition-colors"
              title="Xáo trộn thứ tự từ trong bảng Sổ tay bên dưới"
            >
              <span className="material-symbols-outlined text-[20px]">shuffle</span>
            </button>
          </div>
        </div>
      </div>

      {/* PHÒNG ÔN FLASHCARD 3D */}
      <div ref={roomRef} className="scroll-mt-24">
        <ReviewRoom
          deck={selectedDeck}
          deckTitle={deckTitle}
          startTick={startTick}
          summary={summary}
          onProgress={refreshStats}
          onNavigateToReader={onNavigateToReader}
          onOpenReader={onOpenReader}
        />
      </div>

      {/* KIỂM TRA CÁ NHÂN HÓA (M09) */}
      <QuizSection
        focusTick={quizFocusTick}
        onNavigateToReader={onNavigateToReader}
        onGoReview={() => roomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
        onChanged={refreshStats}
        showToast={showToast}
      />

      {/* FLASHCARD DECKS / CATEGORIES GRID */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <span className="text-xs font-bold text-[#a43073] uppercase tracking-wider">Thư Viện Bộ Thẻ</span>
            <h3 className="text-2xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">Chọn Bộ Flashcard Để Ôn Tập</h3>
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-full text-xs font-semibold">
            {([
              ['all', 'Tất cả'],
              ['series', 'Theo Bộ Truyện'],
              ['starred', 'Yêu Thích ⭐']
            ] as [DeckKindFilter, string][]).map(([kind, label]) => (
              <button
                key={kind}
                onClick={() => setDeckKindFilter(kind)}
                className={`px-3.5 py-1.5 rounded-full transition-all ${deckKindFilter === kind ? 'bg-[#a43073] text-white shadow-xs' : 'text-slate-600'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {deckKindFilter === 'all' && (
            <DeckTile
              active={selectedDeck === ALL_DECK_KEY}
              badge={DECK_BADGE.all}
              title={ALL_DECK_TITLE}
              wordCount={total}
              reviewedCount={null}
              dueCount={dueNow}
              description="Ôn mọi thẻ đến hạn của Sổ tay, không phân biệt truyện."
              onSelect={() => startReview(ALL_DECK_KEY)}
            />
          )}
          {visibleDecks.map(deck => (
            <DeckTile
              key={deck.key}
              active={selectedDeck === deck.key}
              badge={DECK_BADGE[deck.kind]}
              title={deck.title}
              wordCount={deck.word_count}
              reviewedCount={deck.reviewed_count}
              dueCount={deck.due_count}
              description={deck.kind === 'starred' ? 'Những từ bạn đã đánh dấu sao để ưu tiên ôn.' : 'Từ vựng bạn đã lưu khi đọc bộ truyện này.'}
              onSelect={() => startReview(deck.key)}
            />
          ))}
        </div>
        {visibleDecks.length === 0 && deckKindFilter !== 'all' && (
          <p className="text-sm text-slate-500 text-center py-4">
            {deckKindFilter === 'starred' ? 'Bạn chưa đánh dấu sao từ nào.' : 'Chưa có bộ truyện nào có từ đã lưu.'}
          </p>
        )}
      </div>

      <VocabNotebook
        refreshKey={statsTick}
        shuffleTick={shuffleTick}
        onChanged={refreshStats}
        onOpenReader={onOpenReader}
        onNavigateToReader={onNavigateToReader}
        showToast={showToast}
      />
    </div>
  );
};

interface DeckTileProps {
  active: boolean;
  badge: { label: string; color: string };
  title: string;
  wordCount: number;
  reviewedCount: number | null;
  dueCount: number;
  description: string;
  onSelect: () => void;
}

const DeckTile: React.FC<DeckTileProps> = ({ active, badge, title, wordCount, reviewedCount, dueCount, description, onSelect }) => (
  <div
    onClick={onSelect}
    role="button"
    tabIndex={0}
    onKeyDown={e => {
      if (e.key === 'Enter') onSelect();
    }}
    className={`bg-white rounded-2xl p-4 shadow-xs border hover:shadow-md transition-all flex flex-col justify-between cursor-pointer group ${
      active ? 'border-[#a43073] ring-2 ring-pink-200' : 'border-pink-100'
    }`}
  >
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${badge.color}`}>{badge.label}</span>
        <span className="text-xs font-bold text-slate-500">{wordCount} từ vựng</span>
      </div>
      <h4 className="text-sm font-bold text-slate-800 group-hover:text-[#a43073] transition-colors">{title}</h4>
      <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">{description}</p>
    </div>
    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
      {reviewedCount !== null ? (
        <>
          <div className="w-24 bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="bg-[#a43073] h-full rounded-full" style={{ width: `${percent(reviewedCount, wordCount)}%` }}></div>
          </div>
          <span className="text-xs font-bold text-[#a43073]">Ôn {reviewedCount}/{wordCount}</span>
        </>
      ) : (
        <span className="text-xs font-bold text-[#a43073]">Bấm để ôn</span>
      )}
      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${dueCount > 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-500'}`}>
        {dueCount} đến hạn
      </span>
    </div>
  </div>
);
