import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { errorMessage } from '../api/client';
import {
  QuizDetail,
  QuizQuestion,
  clearQuizDraft,
  getQuiz,
  isAlreadySubmitted,
  loadQuizDraft,
  saveQuizDraft,
  submitQuiz
} from '../api/quiz';
import { ConfirmDialog } from './ConfirmDialog';

interface QuizRoomProps {
  quiz: QuizDetail;
  onSubmitted: (result: QuizDetail) => void;
  /** Thoát về màn chính của khu kiểm tra; đáp án đã lưu tạm nên làm tiếp được. */
  onExit: () => void;
}

const OPTION_KEYS = ['1', '2', '3', '4'];

/** Tách chuỗi theo 【】 để tô nổi phần được hỏi, không dùng innerHTML. */
export const HighlightedText: React.FC<{ text: string; className?: string }> = ({ text, className }) => {
  const parts = text.split(/(【[^】]*】)/g).filter(part => part !== '');
  return (
    <span className={className}>
      {parts.map((part, index) =>
        part.startsWith('【') && part.endsWith('】') ? (
          <span key={index} className="rounded-md bg-[#ffd8e7] px-1 font-bold text-[#a43073] dark:text-pink-400 dark:bg-pink-900/40">
            {part}
          </span>
        ) : (
          <React.Fragment key={index}>{part}</React.Fragment>
        )
      )}
    </span>
  );
};

export const QuizRoom: React.FC<QuizRoomProps> = ({ quiz, onSubmitted, onExit }) => {
  const questions = useMemo(() => [...quiz.questions].sort((a, b) => a.position - b.position), [quiz.questions]);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>(() => loadQuizDraft(quiz.id));
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submittingRef = useRef(false);

  const question: QuizQuestion | undefined = questions[index];
  const answeredCount = questions.filter(q => (answers[q.id] ?? '').trim() !== '').length;
  const unanswered = questions.length - answeredCount;

  useEffect(() => {
    saveQuizDraft(quiz.id, answers);
  }, [quiz.id, answers]);

  const setAnswer = useCallback((questionId: number, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  }, []);

  const doSubmit = useCallback(async () => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const payload = questions.map(q => ({ question_id: q.id, answer: (answers[q.id] ?? '').trim() || null }));
      let result: QuizDetail;
      try {
        result = await submitQuiz(quiz.id, payload);
      } catch (err) {
        if (!isAlreadySubmitted(err)) throw err;
        result = await getQuiz(quiz.id);
      }
      clearQuizDraft(quiz.id);
      onSubmitted(result);
    } catch (err) {
      setError(errorMessage(err));
      setConfirmOpen(false);
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }, [answers, onSubmitted, questions, quiz.id]);

  const requestSubmit = () => {
    if (unanswered > 0) setConfirmOpen(true);
    else void doSubmit();
  };

  // Phím 1–4 chọn đáp án ở câu trắc nghiệm; không bắt phím khi đang gõ vào ô nhập.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!question || question.question_type !== 'multiple_choice' || confirmOpen) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      const choice = OPTION_KEYS.indexOf(event.key);
      const option = choice >= 0 ? question.options?.[choice] : undefined;
      if (option !== undefined) setAnswer(question.id, option);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [question, confirmOpen, setAnswer]);

  if (!question) {
    return <div className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">Bài kiểm tra này chưa có câu hỏi nào.</div>;
  }

  const isRelated = question.target_kind === 'related';
  const current = answers[question.id] ?? '';
  const progress = Math.round((answeredCount / questions.length) * 100);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button onClick={onExit} className="inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-[#a43073] dark:text-slate-400 dark:hover:text-pink-300">
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Tạm dừng
        </button>
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
          Câu {index + 1}/{questions.length} • Đã trả lời {answeredCount}
        </span>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-[#1e293b]" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-[#a43073] transition-all" style={{ width: `${progress}%` }}></div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {questions.map((q, i) => {
          const done = (answers[q.id] ?? '').trim() !== '';
          return (
            <button
              key={q.id}
              onClick={() => setIndex(i)}
              aria-label={`Đến câu ${i + 1}`}
              className={`h-7 w-7 rounded-full text-[11px] font-bold transition-colors ${
                i === index
                  ? 'bg-[#a43073] text-white'
                  : done
                    ? 'bg-[#ffd8e7] text-[#85145a] dark:text-pink-300 dark:bg-pink-900/40'
                    : 'bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-[#1e293b] dark:text-slate-400 dark:hover:bg-slate-700'
              }`}
            >
              {i + 1}
            </button>
          );
        })}
      </div>

      <div className="flex flex-col gap-4 rounded-3xl border border-pink-100 bg-white p-5 shadow-soft sm:p-7 dark:border-pink-900/40 dark:bg-slate-800">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[10px] font-bold text-blue-900 dark:bg-blue-900/30 dark:text-blue-300">
            {question.question_type === 'multiple_choice' ? 'Trắc nghiệm' : 'Điền từ'}
          </span>
          {isRelated && (
            <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold text-amber-900 dark:bg-amber-900/30 dark:text-amber-300">Từ mới để đoán</span>
          )}
        </div>

        <h3 className="font-['Plus_Jakarta_Sans'] text-lg font-bold leading-relaxed text-slate-800 sm:text-xl dark:text-slate-100">
          <HighlightedText text={question.prompt} />
        </h3>

        {question.example && (
          <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-700 dark:bg-[#1e293b]">
            <p className="font-['Noto_Serif_SC'] text-base leading-relaxed text-slate-800 dark:text-slate-100">
              <HighlightedText text={question.example.zh} />
            </p>
            {question.example.pinyin && <p className="mt-1 font-mono text-xs text-slate-500 dark:text-slate-400">{question.example.pinyin}</p>}
          </div>
        )}

        {isRelated && question.hint && (
          <div className="flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/30 dark:text-amber-300">
            <span className="material-symbols-outlined text-[16px]">lightbulb</span>
            <span>Gợi ý: {question.hint}</span>
          </div>
        )}

        {question.question_type === 'multiple_choice' ? (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {(question.options ?? []).map((option, i) => {
              const selected = current === option;
              return (
                <button
                  key={`${i}-${option}`}
                  onClick={() => setAnswer(question.id, option)}
                  className={`flex items-center gap-3 rounded-2xl border px-4 py-3 text-left text-sm font-semibold transition-all ${
                    selected
                      ? 'border-[#a43073] bg-[#ffd8e7]/60 text-[#85145a] ring-2 ring-pink-200 dark:text-pink-300'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-pink-300 hover:bg-pink-50/50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'
                  }`}
                >
                  <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${selected ? 'bg-[#a43073] text-white' : 'bg-slate-100 text-slate-500 dark:bg-[#1e293b] dark:text-slate-400'}`}>
                    {i + 1}
                  </span>
                  <span className="min-w-0 break-words">{option}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <input
            type="text"
            value={current}
            maxLength={200}
            onChange={event => setAnswer(question.id, event.target.value)}
            placeholder="Nhập đáp án của bạn..."
            aria-label="Đáp án của bạn"
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none focus:ring-2 focus:ring-[#f472b6] dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-100"
          />
        )}
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-2xl bg-rose-50 p-4 text-sm text-rose-700 dark:bg-rose-900/30 dark:text-rose-400">
          <span>{error} Đáp án của bạn vẫn được giữ lại.</span>
          <button onClick={() => void doSubmit()} className="rounded-full bg-[#a43073] px-4 py-1.5 text-xs font-bold text-white">Nộp lại</button>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <button
          onClick={() => setIndex(i => Math.max(0, i - 1))}
          disabled={index === 0}
          className="rounded-full bg-slate-100 px-5 py-2.5 text-xs font-bold text-slate-600 hover:bg-slate-200 disabled:opacity-40 dark:bg-[#1e293b] dark:text-slate-300 dark:hover:bg-slate-700"
        >
          Câu trước
        </button>
        {index < questions.length - 1 ? (
          <button
            onClick={() => setIndex(i => Math.min(questions.length - 1, i + 1))}
            className="rounded-full bg-[#a43073] px-6 py-2.5 text-xs font-bold text-white shadow-md hover:bg-[#85145a]"
          >
            Câu sau
          </button>
        ) : (
          <button
            onClick={requestSubmit}
            disabled={submitting}
            className="rounded-full bg-[#a43073] px-6 py-2.5 text-xs font-bold text-white shadow-md hover:bg-[#85145a] disabled:opacity-60"
          >
            {submitting ? 'Đang nộp...' : 'Nộp bài'}
          </button>
        )}
      </div>

      {index < questions.length - 1 && (
        <button
          onClick={requestSubmit}
          disabled={submitting}
          className="self-center text-xs font-bold text-[#a43073] hover:underline disabled:opacity-60 dark:text-pink-400"
        >
          {submitting ? 'Đang nộp...' : 'Nộp bài ngay'}
        </button>
      )}

      {confirmOpen && (
        <ConfirmDialog
          title="Nộp bài khi còn câu chưa làm?"
          message={`Bạn còn ${unanswered} câu chưa trả lời. Câu bỏ trống sẽ tính là sai và không thể làm lại sau khi nộp.`}
          confirmLabel="Nộp bài"
          busy={submitting}
          onConfirm={() => void doSubmit()}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </div>
  );
};
