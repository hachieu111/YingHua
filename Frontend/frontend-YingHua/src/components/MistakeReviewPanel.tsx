import React, { useEffect, useRef, useState } from 'react';
import { ApiError, errorMessage, isAbortedError } from '../api/client';
import { MistakeReview, PracticeResult, answerMistakePractice, getMistakeReview } from '../api/quiz';

interface MistakeReviewPanelProps {
  quizId: number;
  questionId: number;
  /** Đã có sẵn giải thích: nút ghi "Xem lại giải thích". */
  hasReview: boolean;
}

const errorText = (err: unknown): string => {
  if (err instanceof ApiError) {
    if (err.code === 'QUIZ_NOT_SUBMITTED') return 'Bài kiểm tra chưa được nộp nên chưa xem được giải thích.';
    if (err.code === 'QUESTION_NOT_WRONG') return 'Chỉ câu làm sai mới có phần giải thích này.';
    if (err.code === 'INVALID_PRACTICE_CHOICE') return 'Lựa chọn không hợp lệ. Hãy chọn một trong các đáp án.';
    if (err.status === 404) return 'Không tìm thấy câu hỏi này.';
  }
  return errorMessage(err);
};

export const MistakeReviewPanel: React.FC<MistakeReviewPanelProps> = ({ quizId, questionId, hasReview }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [review, setReview] = useState<MistakeReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [choice, setChoice] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [practiceResult, setPracticeResult] = useState<PracticeResult | null>(null);
  const [practiceError, setPracticeError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const load = async () => {
    const controller = new AbortController();
    controllerRef.current?.abort();
    controllerRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const data = await getMistakeReview(quizId, questionId, controller.signal);
      if (!controller.signal.aborted) setReview(data);
    } catch (err) {
      if (isAbortedError(err) || controller.signal.aborted) return;
      setError(errorText(err));
    } finally {
      if (controllerRef.current === controller) setLoading(false);
    }
  };

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (!review && !loading) void load();
  };

  const submitChoice = async (option: string) => {
    if (checking || practiceResult) return;
    setChoice(option);
    setChecking(true);
    setPracticeError(null);
    try {
      setPracticeResult(await answerMistakePractice(quizId, questionId, option));
    } catch (err) {
      if (isAbortedError(err)) return;
      setChoice(null);
      setPracticeError(errorText(err));
    } finally {
      setChecking(false);
    }
  };

  const retryPractice = () => {
    setChoice(null);
    setPracticeResult(null);
    setPracticeError(null);
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex items-center gap-1.5 self-start rounded-full bg-pink-50 px-4 py-1.5 text-xs font-bold text-[#a43073] transition-colors hover:bg-pink-100 dark:bg-pink-900/20 dark:text-pink-400 dark:hover:bg-pink-900/30"
      >
        <span className="material-symbols-outlined text-[16px]">psychology_alt</span>
        {open ? 'Ẩn giải thích' : hasReview ? 'Xem lại: Vì sao sai?' : 'Vì sao sai?'}
      </button>

      {open && (
        <div className="flex flex-col gap-3 rounded-xl border border-pink-100 bg-pink-50/40 p-3 dark:border-pink-900/40 dark:bg-pink-900/10">
          {loading && <p className="text-xs text-slate-500 dark:text-slate-400">Đang chuẩn bị giải thích...</p>}
          {error && (
            <div role="alert" className="flex flex-wrap items-center justify-between gap-2 text-xs text-rose-700 dark:text-rose-300">
              <span>{error}</span>
              <button type="button" onClick={() => void load()} className="font-bold text-[#a43073] dark:text-pink-400 hover:underline">Thử lại</button>
            </div>
          )}

          {review && (
            <>
              <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-200">{review.explanation}</p>
              {review.difference && (
                <p className="rounded-lg bg-white px-3 py-2 text-xs leading-relaxed text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                  <span className="font-bold text-[#a43073] dark:text-pink-400">Điểm khác biệt: </span>
                  {review.difference}
                </p>
              )}
              {review.ai_label && <p className="text-[11px] italic text-slate-500 dark:text-slate-400">{review.ai_label}</p>}

              {review.practice && (
                <div className="flex flex-col gap-2 rounded-xl border border-slate-100 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
                  <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Luyện thêm</span>
                  <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{review.practice.prompt}</p>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {review.practice.options.map(option => {
                      const picked = choice === option;
                      const isRight = practiceResult?.correct_answer === option;
                      let tone = 'border-slate-200 bg-white text-slate-700 hover:bg-pink-50 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-200 dark:hover:bg-slate-700';
                      if (practiceResult) {
                        if (isRight) tone = 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-900/30 dark:text-emerald-300';
                        else if (picked) tone = 'border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-900/50 dark:bg-rose-900/30 dark:text-rose-300';
                        else tone = 'border-slate-100 bg-slate-50 text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-500';
                      } else if (picked) {
                        tone = 'border-[#a43073] bg-pink-50 text-[#a43073] dark:bg-pink-900/20 dark:text-pink-400';
                      }
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => void submitChoice(option)}
                          disabled={checking || practiceResult !== null}
                          className={`rounded-xl border px-3 py-2 text-left text-xs font-semibold transition-colors ${tone}`}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                  {practiceError && <p role="alert" className="text-xs text-rose-700 dark:text-rose-300">{practiceError}</p>}
                  {practiceResult && (
                    <div className="flex flex-col gap-1 text-xs">
                      <p className={`font-bold ${practiceResult.is_correct ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-300'}`}>
                        {practiceResult.is_correct ? 'Chính xác!' : `Chưa đúng. Đáp án: ${practiceResult.correct_answer}`}
                      </p>
                      <p className="leading-relaxed text-slate-600 dark:text-slate-300">{practiceResult.explanation}</p>
                      <button type="button" onClick={retryPractice} className="self-start text-[11px] font-bold text-[#a43073] dark:text-pink-400 hover:underline">
                        Làm lại
                      </button>
                    </div>
                  )}
                  <p className="text-[11px] italic text-slate-400 dark:text-slate-500">Câu luyện thêm chỉ để ôn tập, không thay đổi điểm bài kiểm tra.</p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
