import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, errorMessage, isAbortedError } from '../api/client';
import { hskLabel } from '../api/dictionary';
import {
  ApiCardSide,
  ApiDueCard,
  CARD_TYPE_LABEL,
  HintSource,
  RATING_LABEL,
  ReviewSummary,
  getDueCards,
  gradeCard
} from '../api/review';
import { getVocab, updateVocab } from '../api/vocab';
import { ReaderTarget } from '../types';
import { formatDateTime, formatInterval } from '../utils/format';
import { speakChinese } from '../utils/speech';
import { notifyActivity } from '../utils/useStreak';
import { AiNotePanel } from './AiNotePanel';
import { AuthImage } from './AuthImage';

interface ReviewRoomProps {
  /** Khóa bộ thẻ: all | starred | series:<id>. */
  deck: string;
  deckTitle: string;
  /** Đổi giá trị để bắt đầu lại phiên ôn (nút "Ôn tập ngay"). */
  startTick: number;
  summary: ReviewSummary | null;
  /** Gọi sau mỗi lần chấm hoặc đổi sao để trang cập nhật số liệu, bộ thẻ. */
  onProgress: () => void;
  onNavigateToReader: () => void;
  onOpenReader: (target: ReaderTarget) => void;
}

type Phase = 'loading' | 'error' | 'card' | 'empty';

// Đủ lớn để vẫn còn thẻ của từ khác sau khi bỏ qua các thẻ cùng từ đã hỏi trong phiên.
const BATCH_SIZE = 50;
/** Thời gian xoay thẻ (khớp `duration-500`) cộng chút dư, trước khi thay nội dung mặt sau. */
const FLIP_MS = 550;
/** Chấm dưới mức này ("Quên", "Khó") thì chính thẻ đó được hỏi lại khi FSRS cho đến hạn trong phiên. */
const RELEARN_BELOW_RATING = 3;
const FEEDBACK_MS = 2600;
const SPEECH_RATE = 0.85;

const RATINGS: { value: 1 | 2 | 3 | 4; label: string; caption: string; dot: string; text: string; hover: string }[] = [
  { value: 1, label: 'Quên', caption: 'Lặp lại ngay', dot: 'bg-rose-500', text: 'text-rose-600 dark:text-rose-400', hover: 'hover:bg-rose-50 hover:text-rose-700 dark:hover:bg-rose-900/20 dark:hover:text-rose-300' },
  { value: 2, label: 'Khó', caption: 'Cần củng cố', dot: 'bg-amber-500', text: 'text-amber-600 dark:text-amber-400', hover: 'hover:bg-amber-50 hover:text-amber-800 dark:hover:bg-amber-900/20 dark:hover:text-amber-300' },
  { value: 3, label: 'Được', caption: 'Nhớ rõ', dot: 'bg-blue-500', text: 'text-blue-600 dark:text-blue-400', hover: 'hover:bg-blue-50 hover:text-blue-800 dark:hover:bg-blue-900/20 dark:hover:text-blue-300' },
  { value: 4, label: 'Dễ', caption: 'Đã thuộc lòng', dot: 'bg-[#a43073]', text: 'text-[#a43073] dark:text-pink-400', hover: 'hover:bg-pink-50 hover:text-[#a43073] dark:hover:bg-pink-900/20 dark:hover:text-pink-300' }
];

/** UUID cho mỗi lần hiển thị thẻ; có dự phòng khi trình duyệt chưa hỗ trợ randomUUID. */
const newPresentationId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
};

const HINT_LABEL: Record<Exclude<HintSource, 'meaning'>, string> = {
  context_sentence: 'Gợi ý từ câu trong truyện',
  sino_vietnamese: 'Âm Hán Việt',
  pinyin: 'Pinyin'
};

const FRONT_MEANING_MAX = 140;
const SHORT_MEANING_LENGTH = 40;
const HAN_RUN_RE = /[㐀-鿿豈-﫿]+/g;
const DICT_SEPARATOR_RE = /\s*-{5,}\s*/g;

/** Nghĩa cho mặt trước thẻ recall: chỉ nghĩa đầu tiên, che chữ Hán để mục từ điển không lộ đáp án. */
const frontMeaning = (meaning: string): string => {
  let text = meaning.split(DICT_SEPARATOR_RE)[0];
  text = text.replace(/^\s*\[[^\]]*\]\s*/, '');
  const second = text.indexOf('②');
  if (second > 0) text = text.slice(0, second);
  // Bỏ ký hiệu thô của CVDICT ("LT: 個|个[ge4]", "一塊|一块[yi1 kuai4]") trước khi che chữ Hán.
  text = text
    .replace(/[;,]?\s*(LT|Lượng từ)\s*:[^;]*/g, '')
    .replace(/[^\s;,]+\|[^\s;,]+\[[^\]]*\]/g, '')
    .replace(/\[[^\]]*\d[^\]]*\]/g, '');
  text = text.replace('①', '').replace(HAN_RUN_RE, '～').replace(/\s+/g, ' ').replace(/[\s;,]+$/, '').trim();
  if (text.length <= FRONT_MEANING_MAX) return text;
  const cut = text.lastIndexOf(' ', FRONT_MEANING_MAX);
  return `${text.slice(0, cut > 0 ? cut : FRONT_MEANING_MAX)}…`;
};

/** Nghĩa đầy đủ ở mặt sau: mỗi mục từ điển (ngăn bằng dải gạch) xuống một dòng. */
const fullMeaning = (meaning: string): string => meaning.replace(DICT_SEPARATOR_RE, '\n').trim();

const SideBody: React.FC<{ side: ApiCardSide; isFront: boolean; onSpeak: (text: string) => void; contextHint?: string | null }> = ({ side, isFront, onSpeak, contextHint }) => {
  const spoken = side.term ?? side.audio_text;
  const meaning = side.meaning_vi ? (isFront && !side.term ? frontMeaning(side.meaning_vi) : fullMeaning(side.meaning_vi)) : null;
  const hintSource = isFront ? side.hint_source ?? null : null;
  const hintLabel = hintSource && hintSource !== 'meaning' ? HINT_LABEL[hintSource] : null;
  const extraContextHint = hintSource === 'context_sentence' && !side.meaning_vi ? contextHint : null;
  const isEmpty = !side.term && !side.pinyin && !side.meaning_vi && !side.audio_text && !extraContextHint;
  return (
    <div className="flex flex-col items-center text-center gap-2 my-auto min-h-0 max-h-full overflow-y-auto custom-scrollbar px-2">
      {hintLabel && <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">{hintLabel}</span>}
      {extraContextHint && <span className="text-base text-slate-700 dark:text-slate-200 font-semibold italic leading-snug">“{extraContextHint}”</span>}
      {side.pinyin && (
        <div className="text-xl font-bold text-[#0060ac] dark:text-blue-300 tracking-wide flex items-center gap-2">
          <span>{side.pinyin}</span>
          {side.term && (
            <button
              onClick={e => {
                e.stopPropagation();
                onSpeak(side.term ?? '');
              }}
              className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300 flex items-center justify-center shadow-xs dark:shadow-none transition-transform hover:scale-110"
              title="Phát âm chuẩn"
            >
              <span className="material-symbols-outlined text-[18px]">volume_up</span>
            </button>
          )}
        </div>
      )}
      {side.term && (
        <h2 className="text-6xl sm:text-7xl font-extrabold text-slate-800 dark:text-white tracking-normal font-['Noto_Serif_SC'] my-2 break-all">{side.term}</h2>
      )}
      {!side.term && side.audio_text && isFront && (
        <>
          <button
            onClick={e => {
              e.stopPropagation();
              onSpeak(side.audio_text ?? '');
            }}
            className="w-24 h-24 rounded-full bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300 flex items-center justify-center shadow-md transition-transform hover:scale-105"
            title="Nghe lại"
          >
            <span className="material-symbols-outlined text-[48px]">volume_up</span>
          </button>
          <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">Nghe và nhớ lại từ này</span>
        </>
      )}
      {meaning && (
        <span
          className={`${
            side.term
              ? 'text-base text-slate-700 dark:text-slate-200 font-semibold'
              : meaning.length <= SHORT_MEANING_LENGTH
                ? 'text-3xl text-slate-800 dark:text-white font-extrabold'
                : 'text-xl text-slate-800 dark:text-slate-100 font-bold'
          } leading-snug break-words whitespace-pre-line max-w-full`}
        >
          {meaning}
        </span>
      )}
      {isEmpty && <span className="text-base font-semibold text-slate-500 dark:text-slate-400">Từ này chưa có nghĩa trong từ điển, hãy tự nhớ lại rồi lật thẻ.</span>}
      {side.sino_vietnamese && (
        <span className="text-xs text-slate-500 dark:text-slate-300 mt-1 px-3.5 py-1 rounded-full bg-slate-100 dark:bg-slate-700 font-medium">
          Âm Hán Việt: <strong className="text-slate-800 dark:text-white">{side.sino_vietnamese}</strong>
        </span>
      )}
      {!isFront && !side.term && spoken && (
        <button
          onClick={e => {
            e.stopPropagation();
            onSpeak(spoken);
          }}
          className="text-xs font-bold text-blue-700 dark:text-blue-300 hover:underline"
        >
          Nghe lại
        </button>
      )}
    </div>
  );
};

export const ReviewRoom: React.FC<ReviewRoomProps> = ({
  deck,
  deckTitle,
  startTick,
  summary,
  onProgress,
  onNavigateToReader,
  onOpenReader
}) => {
  const [phase, setPhase] = useState<Phase>('loading');
  const [error, setError] = useState<string | null>(null);
  const [card, setCard] = useState<ApiDueCard | null>(null);
  const [remaining, setRemaining] = useState<number>(0);
  const [flipped, setFlipped] = useState<boolean>(false);
  const [grading, setGrading] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Cả TTS máy chủ lẫn giọng trình duyệt đều không phát được cho thẻ nghe hiện tại.
  const [audioFailed, setAudioFailed] = useState<boolean>(false);
  const [sessionReviewed, setSessionReviewed] = useState<number>(0);

  const presentationId = useRef<string>('');
  const shownAt = useRef<number>(0);
  const skipped = useRef<Set<number>>(new Set());
  // Mỗi từ chỉ hỏi một lần trong phiên: mục từ đã chấm → id thẻ còn được hỏi lại (thẻ vừa "Quên"/"Khó",
  // khi FSRS cho đến hạn) hoặc null. Các thẻ khác của từ vẫn giữ lịch, ôn ở phiên sau.
  const buriedEntries = useRef<Map<number, number | null>>(new Map());
  const feedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadToken = useRef<number>(0);

  // Thẻ đang rời đi khi lật về mặt trước: mặt sau giữ đáp án của thẻ cũ cho tới khi xoay xong, mặt trước hiện ngay câu
  // hỏi mới — vẫn có hiệu ứng lật mà không lộ đáp án của thẻ mới.
  const [backCard, setBackCard] = useState<ApiDueCard | null>(null);
  const backTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cardRef = useRef<ApiDueCard | null>(null);
  const flippedRef = useRef(false);
  useEffect(() => {
    cardRef.current = card;
    flippedRef.current = flipped;
  }, [card, flipped]);
  useEffect(
    () => () => {
      if (backTimer.current) clearTimeout(backTimer.current);
    },
    []
  );

  const showCard = useCallback((next: ApiDueCard, total: number) => {
    presentationId.current = newPresentationId();
    shownAt.current = Date.now();
    const leaving = flippedRef.current ? cardRef.current : null;
    if (backTimer.current) clearTimeout(backTimer.current);
    setBackCard(leaving);
    if (leaving) backTimer.current = setTimeout(() => setBackCard(null), FLIP_MS);
    setCard(next);
    setRemaining(total);
    setFlipped(false);
    setPhase('card');
  }, []);

  // Lật thẻ: muốn xem mặt sau thì mặt sau phải là thẻ hiện tại, kể cả khi hiệu ứng chuyển thẻ chưa xong.
  const toggleFlip = () => {
    if (backTimer.current) clearTimeout(backTimer.current);
    setBackCard(null);
    setFlipped(value => !value);
  };

  const flashFeedback = useCallback((message: string) => {
    setFeedback(message);
    if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    feedbackTimer.current = setTimeout(() => setFeedback(null), FEEDBACK_MS);
  }, []);

  // Ba thẻ của một từ nằm liền nhau trong danh sách đến hạn; hiện liền nhau thì trông như thẻ cũ bị lật lại.
  // Nên ưu tiên thẻ của từ khác với từ vừa chấm, và không hỏi thẻ khác của từ đã chấm trong phiên.
  const isAvailable = (item: ApiDueCard): boolean => {
    if (skipped.current.has(item.id)) return false;
    const buried = buriedEntries.current;
    return !buried.has(item.vocab_entry_id) || buried.get(item.vocab_entry_id) === item.id;
  };

  const pickNext = (items: ApiDueCard[], avoidEntryId: number | null): ApiDueCard | undefined =>
    items.find(item => isAvailable(item) && item.vocab_entry_id !== avoidEntryId) ?? items.find(isAvailable);

  // Nạp một đợt thẻ đến hạn của bộ thẻ, bỏ qua các thẻ nghe người học đã chọn bỏ qua.
  const loadBatch = useCallback(async (avoidEntryId: number | null = null): Promise<void> => {
    const token = ++loadToken.current;
    setPhase('loading');
    setError(null);
    try {
      const batch = await getDueCards(deck, BATCH_SIZE);
      if (token !== loadToken.current) return;
      const pick = pickNext(batch.items, avoidEntryId);
      if (pick) showCard(pick, batch.total);
      else {
        setCard(null);
        setPhase('empty');
      }
    } catch (err) {
      if (token !== loadToken.current || isAbortedError(err)) return;
      setError(errorMessage(err));
      setPhase('error');
    }
  }, [deck, showCard]);

  useEffect(() => {
    skipped.current = new Set();
    buriedEntries.current = new Map();
    setSessionReviewed(0);
    setNotice(null);
    void loadBatch();
    return () => {
      loadToken.current += 1;
    };
  }, [loadBatch, startTick]);

  useEffect(
    () => () => {
      if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    },
    []
  );

  const speak = (text: string) => {
    void speakChinese(text, SPEECH_RATE).then(ok => setAudioFailed(!ok));
  };

  const handleGrade = async (rating: 1 | 2 | 3 | 4) => {
    if (!card || grading || !flipped) return;
    setGrading(true);
    setNotice(null);
    try {
      const result = await gradeCard(card.id, {
        rating,
        presentation_id: presentationId.current,
        duration_ms: Math.min(Date.now() - shownAt.current, 3_600_000),
        deck
      });
      if (!result.duplicate) setSessionReviewed(count => count + 1);
      const gradedEntryId = card.vocab_entry_id;
      const relearn = rating < RELEARN_BELOW_RATING;
      buriedEntries.current.set(gradedEntryId, relearn ? card.id : null);
      flashFeedback(
        relearn
          ? `Đã ghi nhận “${RATING_LABEL[rating]}”. Thẻ này sẽ hỏi lại sau ${formatInterval(result.interval_seconds)}`
          : `Đã ghi nhận “${RATING_LABEL[rating]}”. Lần ôn kế tiếp: sau ${formatInterval(result.interval_seconds)}`
      );
      onProgress();
      notifyActivity();
      const next = result.next_card;
      if (next && isAvailable(next) && next.vocab_entry_id !== gradedEntryId) showCard(next, result.remaining_due);
      else if (result.remaining_due > 0) await loadBatch(gradedEntryId);
      else {
        setCard(null);
        setPhase('empty');
      }
    } catch (err) {
      if (err instanceof ApiError && (err.code === 'CARD_SUSPENDED' || err.code === 'CARD_NOT_FOUND')) {
        setNotice(`${err.message}. Đang nạp thẻ khác...`);
        await loadBatch();
      } else if (err instanceof ApiError && err.code === 'PRESENTATION_ID_TAKEN') {
        presentationId.current = newPresentationId();
        setNotice('Lượt hiển thị này đã được dùng, vui lòng chấm lại.');
      } else {
        setNotice(errorMessage(err));
      }
    } finally {
      setGrading(false);
    }
  };

  // Thẻ nghe không phát được: bỏ qua mà KHÔNG gửi chấm điểm, thẻ vẫn đến hạn ở lần sau (F08.03).
  const handleSkip = async () => {
    if (!card) return;
    skipped.current.add(card.id);
    setNotice('Đã bỏ qua thẻ nghe, thẻ vẫn giữ nguyên lịch ôn.');
    await loadBatch();
  };

  const handleToggleStar = async () => {
    if (!card) return;
    try {
      const updated = await updateVocab(card.vocab_entry_id, { is_starred: !card.is_starred });
      setCard(current => (current ? { ...current, is_starred: updated.is_starred } : current));
      onProgress();
    } catch (err) {
      setNotice(errorMessage(err));
    }
  };

  // Mở lại đúng trang truyện của ngữ cảnh đang hiển thị; không có thì về trình đọc chung.
  const handleOpenSource = async () => {
    if (!card) return;
    try {
      const detail = await getVocab(card.vocab_entry_id);
      const context = detail.contexts.find(item => item.id === card.context?.id) ?? detail.contexts[0];
      const source = context?.source;
      if (source && source.chapter_id !== null) {
        onOpenReader({ chapterId: source.chapter_id, pageNo: source.page_no, pageId: source.page_id });
        return;
      }
      setNotice('Không tìm thấy trang truyện gốc (có thể đã bị xóa).');
    } catch (err) {
      setNotice(errorMessage(err));
    }
  };

  // Phím tắt: Space lật thẻ, 1–4 chấm điểm. Không bắt phím khi đang nhập liệu hoặc có hộp thoại mở.
  const keyHandler = useRef<(e: KeyboardEvent) => void>(() => undefined);
  keyHandler.current = (e: KeyboardEvent) => {
    const target = e.target;
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return;
    if (document.querySelector('[aria-modal="true"]')) return;
    if (phase !== 'card' || !card) return;
    if (e.code === 'Space') {
      e.preventDefault();
      toggleFlip();
    } else if (['1', '2', '3', '4'].includes(e.key)) {
      void handleGrade(Number(e.key) as 1 | 2 | 3 | 4);
    }
  };
  useEffect(() => {
    const listener = (e: KeyboardEvent) => keyHandler.current(e);
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);

  useEffect(() => {
    setAudioFailed(false);
  }, [card?.id]);

  const renderEmpty = () => {
    const nextDue = summary?.next_due_at ? formatDateTime(summary.next_due_at) : null;
    let icon = 'inventory_2';
    let title = 'Chưa có thẻ nào để ôn';
    let body = 'Hãy lưu từ khi đọc truyện hoặc tra từ; mỗi từ được lưu sẽ tạo sẵn 3 thẻ ôn.';
    if (sessionReviewed > 0 || summary?.status === 'completed') {
      icon = 'celebration';
      title = 'Hoàn thành phiên ôn!';
      body = sessionReviewed > 0
        ? `Bạn vừa ôn ${sessionReviewed} thẻ${summary ? `, hôm nay tổng cộng ${summary.reviewed_today} lượt` : ''}.`
        : `Hôm nay bạn đã ôn ${summary?.reviewed_today ?? 0} lượt và không còn thẻ đến hạn.`;
    } else if (summary && summary.total_cards > 0) {
      icon = 'schedule';
      title = deck === 'all' ? 'Chưa có thẻ đến hạn' : `Bộ “${deckTitle}” chưa có thẻ đến hạn`;
      body = 'Bạn không còn thẻ nào cần ôn lúc này.';
    }
    const showNext = nextDue && !(summary?.status === 'no_cards');
    return (
      <div className="w-full min-h-[360px] rounded-3xl bg-white dark:bg-[#0f172a] border-2 border-pink-100 dark:border-slate-800 shadow-soft dark:shadow-none transition-colors duration-300 flex flex-col items-center justify-center gap-3 p-8 text-center">
        <div className="w-16 h-16 rounded-3xl bg-pink-100 dark:bg-pink-900/30 text-[#a43073] dark:text-pink-400 flex items-center justify-center">
          <span className="material-symbols-outlined text-[36px]">{icon}</span>
        </div>
        <h4 className="text-xl font-extrabold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">{title}</h4>
        <p className="text-sm text-slate-600 dark:text-slate-300 max-w-md leading-relaxed">{body}</p>
        {showNext && (
          <p className="text-sm font-semibold text-[#0060ac] dark:text-blue-300">
            Thẻ kế tiếp đến hạn lúc {nextDue}
          </p>
        )}
        <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
          {summary?.status === 'no_cards' && (
            <button onClick={onNavigateToReader} className="px-5 py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white text-xs font-bold">
              Đọc truyện để lưu từ
            </button>
          )}
          <button onClick={() => void loadBatch()} className="px-5 py-2.5 rounded-full bg-white dark:bg-[#1e293b] border border-pink-200 dark:border-pink-900/40 text-[#a43073] dark:text-pink-400 text-xs font-bold hover:bg-pink-50 dark:hover:bg-pink-900/20">
            Kiểm tra lại thẻ đến hạn
          </button>
        </div>
      </div>
    );
  };

  const backSide: ApiDueCard | null = backCard ?? card;
  const unsupportedListening = card?.card_type === 'listening' && audioFailed;

  return (
    <div className="w-full flex flex-col items-center gap-6">
      <div className="w-full flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="w-2.5 h-6 bg-[#a43073] rounded-full"></span>
          <h3 className="text-xl font-bold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">Phòng Luyện Flashcard 3D</h3>
          <span className="text-xs bg-pink-50 dark:bg-pink-900/20 text-[#a43073] dark:text-pink-400 px-3 py-1 rounded-full font-bold">{deckTitle}</span>
          {phase === 'card' && (
            <span className="text-xs bg-slate-100 dark:bg-slate-700 px-3 py-1 rounded-full text-slate-600 dark:text-slate-300 font-bold">
              Còn {remaining} thẻ đến hạn · đã ôn {sessionReviewed}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-xs bg-white dark:bg-slate-800 px-4 py-2 rounded-full shadow-xs dark:shadow-none border border-pink-100 dark:border-slate-700">
          <span className="material-symbols-outlined text-[16px] text-[#a43073] dark:text-pink-400">keyboard</span>
          <span>
            Mẹo: Nhấn <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-slate-800 dark:text-slate-100 font-bold font-mono text-[10px]">Space</kbd> để lật thẻ, phím <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-slate-800 dark:text-slate-100 font-bold font-mono text-[10px]">1-4</kbd> để đánh giá
          </span>
        </div>
      </div>

      <div className="h-8 flex items-center">
        {feedback && <div className="px-4 py-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-300 font-bold text-xs shadow-xs dark:shadow-none">{feedback}</div>}
        {!feedback && notice && <div className="px-4 py-1.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-300 font-bold text-xs shadow-xs dark:shadow-none">{notice}</div>}
      </div>

      <div className="w-full max-w-3xl flex flex-col items-center">
        {phase === 'loading' && (
          <div className="w-full min-h-[360px] rounded-3xl bg-white dark:bg-[#0f172a] border-2 border-pink-100 dark:border-slate-800 shadow-soft dark:shadow-none transition-colors duration-300 flex items-center justify-center gap-3 text-sm text-slate-500 dark:text-slate-400">
            <span className="w-5 h-5 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
            Đang nạp thẻ đến hạn...
          </div>
        )}

        {phase === 'error' && (
          <div className="w-full min-h-[360px] rounded-3xl bg-white dark:bg-[#0f172a] border-2 border-rose-100 dark:border-rose-900/40 shadow-soft dark:shadow-none transition-colors duration-300 flex flex-col items-center justify-center gap-3 p-8 text-center">
            <span className="material-symbols-outlined text-[40px] text-rose-400">error</span>
            <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>
            <button onClick={() => void loadBatch()} className="px-5 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold">Thử lại</button>
          </div>
        )}

        {phase === 'empty' && renderEmpty()}

        {phase === 'card' && card && backSide && (
          <>
            <div
              onClick={toggleFlip}
              className="w-full h-[520px] cursor-pointer select-none perspective-1200"
            >
              <div
                className={`relative w-full h-full transition-transform duration-500 rounded-3xl shadow-floating transform-style-3d ${flipped ? 'rotate-y-180' : ''}`}
              >
                {/* MẶT TRƯỚC */}
                <div className="absolute inset-0 w-full h-full rounded-3xl bg-white dark:bg-[#0f172a] p-8 flex flex-col justify-between gap-4 overflow-hidden backface-hidden border-2 border-pink-100 dark:border-slate-700 shadow-soft dark:shadow-none">
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-300 font-bold text-xs flex items-center gap-1">
                        <span>⭐</span> {hskLabel(card.hsk_level)}
                      </span>
                      <span className="px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-300 font-semibold text-xs">{CARD_TYPE_LABEL[card.card_type]}</span>
                    </div>
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        void handleToggleStar();
                      }}
                      className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                        card.is_starred ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-500' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-300 hover:text-amber-500 dark:hover:text-amber-400'
                      }`}
                      title="Đánh dấu sao"
                    >
                      <span className="material-symbols-outlined text-[20px]">{card.is_starred ? 'star' : 'star_border'}</span>
                    </button>
                  </div>

                  <SideBody side={card.front} isFront onSpeak={speak} contextHint={card.context?.sentence_vi ?? null} />

                  <div className="flex items-center justify-between w-full pt-4 border-t border-slate-100 dark:border-slate-700">
                    {unsupportedListening ? (
                      <span className="text-xs text-amber-700 dark:text-amber-400">Không phát được âm thanh. Hãy thử lại hoặc bỏ qua thẻ.</span>
                    ) : (
                      <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 text-xs min-w-0">
                        <span className="material-symbols-outlined text-[#a43073] dark:text-pink-400 text-[18px]">auto_stories</span>
                        <span className="truncate">
                          {card.context?.source_label ? <>Xuất hiện ở: <strong className="text-slate-700 dark:text-slate-200">{card.context.source_label}</strong></> : 'Từ lưu từ khung tra cứu'}
                        </span>
                      </div>
                    )}
                    <span className="text-xs font-bold text-[#a43073] dark:text-pink-400 flex items-center gap-1 animate-pulse shrink-0">
                      <span>Chạm để lật mặt sau</span>
                      <span className="material-symbols-outlined text-[18px]">sync</span>
                    </span>
                  </div>
                </div>

                {/* MẶT SAU */}
                <div className="absolute inset-0 w-full h-full rounded-3xl bg-gradient-to-b from-white to-[#eff4ff] dark:from-[#0f172a] dark:to-[#0f172a] p-6 flex flex-col gap-3 backface-hidden rotate-y-180 border-2 border-pink-200 dark:border-slate-700 shadow-soft dark:shadow-none overflow-y-auto custom-scrollbar">
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-bold text-[#a43073] dark:text-pink-400 font-['Noto_Serif_SC']">{backSide.term}</span>
                      {backSide.back.pinyin && <span className="text-base text-blue-600 dark:text-blue-300 font-semibold font-mono">({backSide.back.pinyin})</span>}
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          speak(backSide.term);
                        }}
                        className="w-7 h-7 rounded-full bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300 flex items-center justify-center"
                        title="Phát âm chuẩn"
                      >
                        <span className="material-symbols-outlined text-[16px]">volume_up</span>
                      </button>
                    </div>
                    <span className="text-xs px-3 py-1 rounded-full bg-[#ffd8e7] dark:bg-pink-900/30 text-[#85145a] dark:text-pink-300 font-bold">Ý nghĩa & Ngữ cảnh</span>
                  </div>

                  <div className="p-4 rounded-2xl bg-white dark:bg-slate-800 shadow-xs dark:shadow-none border border-pink-100 dark:border-slate-700 flex flex-col gap-1">
                    <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Định nghĩa tiếng Việt</span>
                    <span className="text-base font-bold text-slate-800 dark:text-slate-100 leading-snug break-words whitespace-pre-line">
                      {backSide.back.meaning_vi ? fullMeaning(backSide.back.meaning_vi) : 'Chưa có nghĩa trong từ điển'}
                    </span>
                    {backSide.back.sino_vietnamese && (
                      <span className="text-xs text-slate-500 dark:text-slate-400">Âm Hán Việt: <strong className="text-slate-800 dark:text-white">{backSide.back.sino_vietnamese}</strong></span>
                    )}
                  </div>

                  {backSide.context && (
                    <div className="p-4 rounded-2xl bg-[#ffd8e7]/30 dark:bg-pink-900/20 border border-pink-200 dark:border-pink-900/40 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#a43073] dark:text-pink-400 flex items-center gap-1">
                          <span className="material-symbols-outlined text-[16px]">menu_book</span>
                          {backSide.context.source_label ?? 'Câu thoại gốc trong Manhua'}
                        </span>
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            speak(backSide.context?.sentence_zh ?? '');
                          }}
                          className="text-blue-700 dark:text-blue-300 hover:text-blue-900 dark:hover:text-blue-200 flex items-center gap-1 text-[11px] font-bold"
                        >
                          <span className="material-symbols-outlined text-[16px]">volume_up</span>
                          Nghe câu
                        </button>
                      </div>
                      {backSide.context.snippet_url && (
                        <AuthImage
                          src={backSide.context.snippet_url}
                          alt={`Ngữ cảnh của ${backSide.term}`}
                          className="w-full max-h-40 object-contain rounded-xl bg-white dark:bg-slate-900"
                        />
                      )}
                      <p className="text-sm font-['Noto_Serif_SC'] font-bold text-slate-800 dark:text-slate-100 mt-0.5">“{backSide.context.sentence_zh}”</p>
                      {backSide.context.sentence_vi && <p className="text-xs text-slate-600 dark:text-slate-300 italic">“{backSide.context.sentence_vi}”</p>}
                      {backSide.contexts_count > 1 && <p className="text-[10px] text-slate-400 dark:text-slate-500">Từ này còn {backSide.contexts_count - 1} ngữ cảnh khác trong Sổ tay.</p>}
                    </div>
                  )}

                  {backSide.note && (
                    <div className="p-3 rounded-2xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900/50 text-xs text-amber-900 dark:text-amber-300 whitespace-pre-wrap break-words">
                      <span className="font-bold">Ghi chú của bạn: </span>
                      {backSide.note}
                    </div>
                  )}

                  {/* Chỉ tải khi lật thẻ lần đầu; khối tự cuộn cùng mặt sau nên thẻ không tràn chữ. */}
                  <AiNotePanel vocabEntryId={backSide.vocab_entry_id} active={flipped} onSpeak={speak} />

                  <div className="flex items-center justify-between pt-2 mt-auto border-t border-slate-100 dark:border-slate-700">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        void handleOpenSource();
                      }}
                      className="inline-flex items-center gap-1 text-xs font-bold text-[#0060ac] dark:text-blue-300 hover:underline"
                    >
                      <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                      <span>Xem lại trang truyện gốc nơi từ xuất hiện</span>
                    </button>
                    <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                      <span className="material-symbols-outlined text-[16px]">touch_app</span>
                      Chạm để quay lại
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="w-full mt-6 flex flex-col gap-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full">
                {RATINGS.map(rating => (
                  <button
                    key={rating.value}
                    onClick={() => void handleGrade(rating.value)}
                    disabled={!flipped || grading}
                    className={`flex flex-col items-center justify-center p-3 rounded-2xl bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 shadow-xs dark:shadow-none border border-slate-200 dark:border-slate-700 transition-all text-center disabled:opacity-50 disabled:cursor-not-allowed enabled:hover:shadow-md ${rating.hover}`}
                  >
                    <span className={`text-xs font-bold flex items-center gap-1 ${rating.text}`}>
                      <span className={`w-2 h-2 rounded-full ${rating.dot}`}></span> {rating.label}
                    </span>
                    <span className="text-sm font-bold mt-1">{rating.caption}</span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono mt-0.5">Phím {rating.value}</span>
                  </button>
                ))}
              </div>
              {!flipped && <p className="text-center text-xs text-slate-500 dark:text-slate-400">Lật thẻ để xem đáp án rồi chọn mức nhớ của bạn.</p>}

              <div className="flex items-center justify-between px-2 pt-1">
                {card.card_type === 'listening' ? (
                  <button
                    onClick={() => void handleSkip()}
                    className="flex items-center gap-1 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white py-1.5 px-3 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    title="Bỏ qua thẻ này, không chấm điểm"
                  >
                    <span className="material-symbols-outlined text-[16px]">skip_next</span>
                    <span>Bỏ qua thẻ</span>
                  </button>
                ) : (
                  <span />
                )}
                <button
                  onClick={toggleFlip}
                  className="flex items-center gap-1.5 text-xs font-bold text-[#a43073] dark:text-pink-300 bg-[#ffd8e7]/60 dark:bg-pink-900/30 hover:bg-[#ffd8e7] dark:hover:bg-pink-900/50 py-2 px-5 rounded-full transition-colors shadow-xs dark:shadow-none"
                >
                  <span className="material-symbols-outlined text-[18px]">sync</span>
                  <span>Lật thẻ (Space)</span>
                </button>
                {card.card_type === 'listening' ? (
                  <button
                    onClick={() => speak(card.front.audio_text ?? card.term)}
                    className="flex items-center gap-1 text-xs font-semibold text-blue-700 dark:text-blue-300 hover:text-blue-900 dark:hover:text-blue-200 py-1.5 px-3 rounded-full hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                  >
                    <span className="material-symbols-outlined text-[16px]">replay</span>
                    <span>Thử lại âm thanh</span>
                  </button>
                ) : (
                  <span />
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
