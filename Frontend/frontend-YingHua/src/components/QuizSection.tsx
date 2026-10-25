import React, { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import {
  QUIZ_MAX_QUESTIONS,
  QUIZ_MIN_QUESTIONS,
  QuizDetail,
  QuizItem,
  QuizSummary,
  createQuiz,
  getQuiz,
  getQuizSummary,
  isNotEnoughWords,
  listQuizzes,
  quizSourceLabel
} from '../api/quiz';
import { formatDateTime } from '../utils/format';
import { QuizResult } from './QuizResult';
import { QuizRoom } from './QuizRoom';

interface QuizSectionProps {
  onNavigateToReader: () => void;
  /** Cuộn tới Phòng Flashcard để ôn các từ làm sai. */
  onGoReview: () => void;
  /** Làm mới số liệu Sổ tay / thẻ sau khi nộp bài hoặc lưu từ. */
  onChanged: () => void;
  showToast: (message: string) => void;
  /** Tăng lên khi nơi khác (nhiệm vụ ngày) yêu cầu đưa người học tới khu kiểm tra. */
  focusTick: number;
}

type View = { kind: 'home' } | { kind: 'taking'; quiz: QuizDetail } | { kind: 'result'; quiz: QuizDetail };

const HISTORY_SIZE = 5;

export const QuizSection: React.FC<QuizSectionProps> = ({ onNavigateToReader, onGoReview, onChanged, showToast, focusTick }) => {
  const [view, setView] = useState<View>({ kind: 'home' });
  const [summary, setSummary] = useState<QuizSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [history, setHistory] = useState<QuizItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [reloadTick, setReloadTick] = useState(0);
  const [questionCount, setQuestionCount] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);
  const creatingRef = useRef(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (focusTick > 0) rootRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [focusTick]);

  useEffect(() => {
    const controller = new AbortController();
    setSummaryError(null);
    getQuizSummary(controller.signal)
      .then(data => {
        setSummary(data);
        setQuestionCount(current => current ?? data.question_count);
      })
      .catch(err => {
        if (!isAbortedError(err)) setSummaryError(errorMessage(err));
      });
    return () => controller.abort();
  }, [reloadTick]);

  useEffect(() => {
    const controller = new AbortController();
    setHistoryLoading(true);
    setHistoryError(null);
    listQuizzes(historyPage, HISTORY_SIZE, controller.signal)
      .then(data => {
        setHistory(data.items);
        setHistoryTotal(data.total);
      })
      .catch(err => {
        if (!isAbortedError(err)) setHistoryError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setHistoryLoading(false);
      });
    return () => controller.abort();
  }, [historyPage, reloadTick]);

  const reload = useCallback(() => setReloadTick(value => value + 1), []);

  const handleCreate = async () => {
    if (creatingRef.current) return;
    creatingRef.current = true;
    setCreating(true);
    setCreateError(null);
    try {
      const quiz = await createQuiz(questionCount ?? undefined);
      setView({ kind: 'taking', quiz });
      reload();
    } catch (err) {
      if (isNotEnoughWords(err)) {
        const current = Number(err.details?.current ?? summary?.eligible_words ?? 0);
        const required = Number(err.details?.required ?? summary?.min_words ?? 10);
        setCreateError(`Cần tối thiểu ${required} từ trong Sổ tay (hiện có ${current}).`);
        reload();
      } else {
        setCreateError(errorMessage(err));
      }
    } finally {
      creatingRef.current = false;
      setCreating(false);
    }
  };

  const handleOpen = async (item: QuizItem) => {
    setOpeningId(item.id);
    try {
      const quiz = await getQuiz(item.id);
      setView({ kind: quiz.status === 'submitted' ? 'result' : 'taking', quiz });
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setOpeningId(null);
    }
  };

  const backHome = () => {
    setView({ kind: 'home' });
    reload();
  };

  const handleSubmitted = (result: QuizDetail) => {
    setView({ kind: 'result', quiz: result });
    reload();
    onChanged();
  };

  const inProgress = history.find(item => item.status !== 'submitted');
  const notEnough = summary !== null && summary.eligible_words < summary.min_words;
  const pageCount = Math.max(1, Math.ceil(historyTotal / HISTORY_SIZE));

  return (
    <div ref={rootRef} className="scroll-mt-24 rounded-3xl border border-pink-100 bg-white p-5 shadow-soft sm:p-8">
      {view.kind === 'taking' && <QuizRoom key={view.quiz.id} quiz={view.quiz} onSubmitted={handleSubmitted} onExit={backHome} />}
      {view.kind === 'result' && (
        <QuizResult
          key={view.quiz.id}
          quiz={view.quiz}
          onBack={backHome}
          onGoReview={() => {
            backHome();
            onGoReview();
          }}
          onWordSaved={onChanged}
          showToast={showToast}
        />
      )}

      {view.kind === 'home' && (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
            <div className="flex max-w-xl flex-col gap-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-[#a43073]">Kiểm tra cá nhân hóa</span>
              <h3 className="font-['Plus_Jakarta_Sans'] text-2xl font-bold text-slate-800">Thử sức với từ trong Sổ tay của bạn</h3>
              <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
                Đề được ra từ chính những từ bạn đã lưu, ưu tiên từ bạn dễ quên. Từ làm sai sẽ được đưa về ôn sớm, kèm vài từ mới liên quan để bạn đoán.
              </p>
            </div>

            <div className="flex min-w-[260px] flex-col gap-3 rounded-2xl border border-pink-100 bg-gradient-to-br from-[#eff4ff] to-white p-4">
              {!summary && !summaryError && <span className="text-xs text-slate-500">Đang kiểm tra Sổ tay...</span>}
              {summaryError && (
                <div className="flex items-center justify-between gap-2 text-xs text-rose-700">
                  <span>{summaryError}</span>
                  <button onClick={reload} className="font-bold text-[#a43073] hover:underline">Thử lại</button>
                </div>
              )}
              {summary && notEnough && (
                <div className="flex flex-col gap-2">
                  <span className="text-sm font-bold text-slate-800">
                    Cần tối thiểu {summary.min_words} từ trong Sổ tay (hiện có {summary.eligible_words})
                  </span>
                  <span className="text-xs text-slate-500">Đọc truyện và lưu thêm từ để mở khóa bài kiểm tra.</span>
                  <button onClick={onNavigateToReader} className="self-start rounded-full bg-[#a43073] px-4 py-2 text-xs font-bold text-white hover:bg-[#85145a]">
                    Đi đọc truyện
                  </button>
                </div>
              )}
              {summary && !notEnough && (
                <>
                  <span className="text-xs text-slate-600">
                    Có <b className="text-[#a43073]">{summary.eligible_words}</b> từ đủ điều kiện ra đề
                  </span>
                  <label className="flex items-center justify-between gap-3 text-xs font-semibold text-slate-700">
                    Số câu
                    <input
                      type="number"
                      min={QUIZ_MIN_QUESTIONS}
                      max={QUIZ_MAX_QUESTIONS}
                      value={questionCount ?? summary.question_count}
                      disabled={creating}
                      onChange={event => {
                        const value = Number(event.target.value);
                        setQuestionCount(Number.isFinite(value) ? Math.min(QUIZ_MAX_QUESTIONS, Math.max(QUIZ_MIN_QUESTIONS, Math.round(value))) : null);
                      }}
                      className="w-20 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-center text-xs outline-none focus:ring-2 focus:ring-[#f472b6]"
                    />
                  </label>
                  <button
                    onClick={() => void handleCreate()}
                    disabled={creating}
                    className="flex items-center justify-center gap-2 rounded-full bg-[#a43073] px-4 py-2.5 text-xs font-bold text-white shadow-md hover:bg-[#85145a] disabled:opacity-70"
                  >
                    {creating ? (
                      <>
                        <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                        <span className="animate-pulse">Đang tạo đề...</span>
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-[16px]">quiz</span>
                        <span>Tạo bài kiểm tra mới</span>
                      </>
                    )}
                  </button>
                  {creating && <span className="text-[11px] text-slate-500">Việc này có thể mất vài giây, vui lòng chờ.</span>}
                </>
              )}
              {createError && <span className="text-xs font-semibold text-rose-600">{createError}</span>}
            </div>
          </div>

          {inProgress && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <span className="text-sm font-semibold text-amber-900">Bạn có một bài đang làm dở (tạo lúc {formatDateTime(inProgress.created_at)}).</span>
              <button
                onClick={() => void handleOpen(inProgress)}
                disabled={openingId === inProgress.id}
                className="rounded-full bg-amber-500 px-4 py-1.5 text-xs font-bold text-white hover:bg-amber-600 disabled:opacity-60"
              >
                Làm tiếp
              </button>
            </div>
          )}

          <div className="flex flex-col gap-3">
            <h4 className="text-sm font-bold text-slate-800">Lịch sử bài kiểm tra</h4>
            {historyError && (
              <div className="flex items-center justify-between gap-3 rounded-2xl bg-rose-50 p-3 text-xs text-rose-700">
                <span>{historyError}</span>
                <button onClick={reload} className="rounded-full bg-[#a43073] px-3 py-1 font-bold text-white">Thử lại</button>
              </div>
            )}
            {!historyError && historyLoading && history.length === 0 && <p className="py-4 text-center text-xs text-slate-500">Đang tải lịch sử...</p>}
            {!historyError && !historyLoading && history.length === 0 && (
              <p className="py-4 text-center text-xs text-slate-500">Bạn chưa làm bài kiểm tra nào.</p>
            )}
            {history.length > 0 && (
              <ul className="flex flex-col gap-2">
                {history.map(item => {
                  const done = item.status === 'submitted';
                  return (
                    <li key={item.id}>
                      <button
                        onClick={() => void handleOpen(item)}
                        disabled={openingId === item.id}
                        className="flex w-full items-center justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-left transition-colors hover:border-pink-200 hover:bg-pink-50/50 disabled:opacity-60"
                      >
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate-800">{formatDateTime(item.submitted_at ?? item.created_at)}</span>
                          <span className="text-[11px] text-slate-500">{quizSourceLabel(item.source)}</span>
                        </div>
                        {done ? (
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-extrabold text-[#a43073]">{item.score ?? 0}/{item.question_count}</span>
                            {item.related_count > 0 && (
                              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900">
                                Từ mới {item.related_score ?? 0}/{item.related_count}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold text-amber-900">Đang làm dở</span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
            {pageCount > 1 && (
              <div className="flex items-center justify-center gap-3 pt-1 text-xs font-semibold text-slate-600">
                <button disabled={historyPage <= 1} onClick={() => setHistoryPage(historyPage - 1)} className="rounded-full bg-slate-100 px-4 py-1.5 hover:bg-slate-200 disabled:opacity-40">Trước</button>
                <span>{historyPage} / {pageCount}</span>
                <button disabled={historyPage >= pageCount} onClick={() => setHistoryPage(historyPage + 1)} className="rounded-full bg-slate-100 px-4 py-1.5 hover:bg-slate-200 disabled:opacity-40">Sau</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
