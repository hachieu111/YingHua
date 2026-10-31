import React, { useState } from 'react';
import { errorMessage } from '../api/client';
import { QuizDetail, QuizQuestion, quizSourceLabel, saveQuizWord } from '../api/quiz';
import { speakChinese } from '../utils/speech';
import { MistakeReviewPanel } from './MistakeReviewPanel';
import { HighlightedText } from './QuizRoom';

interface QuizResultProps {
  quiz: QuizDetail;
  onBack: () => void;
  /** Sang Phòng Flashcard để ôn các từ vừa làm sai. */
  onGoReview: () => void;
  /** Gọi sau khi lưu từ mở rộng để làm mới số liệu Sổ tay. */
  onWordSaved: () => void;
  showToast: (message: string) => void;
}

export const QuizResult: React.FC<QuizResultProps> = ({ quiz, onBack, onGoReview, onWordSaved, showToast }) => {
  const [savedIds, setSavedIds] = useState<Set<number>>(() => new Set());
  const [savingIds, setSavingIds] = useState<Set<number>>(() => new Set());

  const questions = [...quiz.questions].sort((a, b) => a.position - b.position);
  const savedCount = quiz.question_count;
  const score = quiz.score ?? 0;
  const ratio = savedCount > 0 ? score / savedCount : 0;
  const tone = ratio >= 0.8 ? 'text-emerald-600 dark:text-emerald-400' : ratio >= 0.5 ? 'text-[#a43073] dark:text-pink-400' : 'text-rose-600 dark:text-rose-400';

  const handleSave = async (question: QuizQuestion) => {
    if (savingIds.has(question.id) || savedIds.has(question.id)) return;
    setSavingIds(prev => new Set(prev).add(question.id));
    try {
      await saveQuizWord(quiz.id, question.id);
      setSavedIds(prev => new Set(prev).add(question.id));
      showToast(`Đã lưu “${question.term ?? ''}” vào Sổ tay`);
      onWordSaved();
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setSavingIds(prev => {
        const next = new Set(prev);
        next.delete(question.id);
        return next;
      });
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="relative flex flex-col gap-4 overflow-hidden rounded-3xl border border-pink-100 bg-gradient-to-br from-[#eff4ff] to-white p-6 shadow-soft sm:p-8 dark:border-pink-900/40 dark:from-slate-800 dark:to-slate-800">
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-pink-100/60 blur-2xl dark:bg-pink-900/30"></div>
        <div className="relative z-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#a43073] dark:text-pink-400">Kết quả bài kiểm tra</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className={`font-['Plus_Jakarta_Sans'] text-5xl font-extrabold ${tone}`}>{score}</span>
              <span className="text-xl font-bold text-slate-400">/ {savedCount}</span>
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">câu từ đã lưu đúng</span>
            </div>
            {quiz.related_count > 0 && (
              <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900 dark:bg-amber-900/30 dark:text-amber-300">
                <span className="material-symbols-outlined text-[14px]">travel_explore</span>
                Đoán từ mới: {quiz.related_score ?? 0}/{quiz.related_count}
              </div>
            )}
          </div>
          <span className="rounded-full bg-white px-3 py-1 text-[11px] font-bold text-slate-600 shadow-xs dark:bg-slate-800 dark:text-slate-300">{quizSourceLabel(quiz.source)}</span>
        </div>

        {quiz.rescheduled_terms.length > 0 && (
          <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-pink-100 bg-white p-4 dark:border-pink-900/40 dark:bg-slate-800">
            <div className="text-sm text-slate-700 dark:text-slate-100">
              <span className="font-bold text-[#a43073] dark:text-pink-400">Đã đưa {quiz.rescheduled_terms.length} từ vào ôn lại:</span>{' '}
              <span className="font-['Noto_Serif_SC']">{quiz.rescheduled_terms.join('、')}</span>
            </div>
            <button onClick={onGoReview} className="rounded-full bg-[#a43073] px-4 py-2 text-xs font-bold text-white hover:bg-[#85145a]">
              Sang Phòng Flashcard
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3">
        {questions.map((q, i) => {
          const correct = q.is_correct === true;
          const isRelated = q.target_kind === 'related';
          const saved = savedIds.has(q.id);
          return (
            <div key={q.id} className={`rounded-2xl border bg-white p-4 shadow-xs sm:p-5 ${correct ? 'border-emerald-200 dark:border-emerald-900/40' : 'border-rose-200 dark:border-rose-900/40'} dark:bg-slate-800`}>
              <div className="flex items-start gap-3">
                <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white ${correct ? 'bg-emerald-500' : 'bg-rose-500'}`}>
                  <span className="material-symbols-outlined text-[16px]">{correct ? 'check' : 'close'}</span>
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-bold text-slate-400">Câu {i + 1}</span>
                    {isRelated && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900 dark:bg-amber-900/30 dark:text-amber-300">Từ mới để đoán</span>}
                    {q.related_to && <span className="text-[11px] text-slate-500 dark:text-slate-400">liên quan tới “{q.related_to.term}”</span>}
                  </div>
                  <p className="text-sm font-bold leading-relaxed text-slate-800 dark:text-slate-100">
                    <HighlightedText text={q.prompt} />
                  </p>

                  <div className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
                    <div className={`rounded-xl px-3 py-2 ${correct ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-rose-50 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300'}`}>
                      <span className="font-semibold">Bạn chọn: </span>
                      {q.user_answer?.trim() ? q.user_answer : <em>Chưa trả lời</em>}
                    </div>
                    {!correct && (
                      <div className="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                        <span className="font-semibold">Đáp án đúng: </span>
                        {q.correct_answer}
                      </div>
                    )}
                  </div>

                  {q.explanation && <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300">{q.explanation}</p>}

                  {q.example && (
                    <div className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3 dark:border-slate-700 dark:bg-[#1e293b]">
                      <div className="min-w-0">
                        <p className="font-['Noto_Serif_SC'] text-sm text-slate-800 dark:text-slate-100"><HighlightedText text={q.example.zh} /></p>
                        {q.example.pinyin && <p className="font-mono text-[11px] text-slate-500 dark:text-slate-400">{q.example.pinyin}</p>}
                        {q.example.vi && <p className="text-xs text-slate-600 dark:text-slate-300">{q.example.vi}</p>}
                      </div>
                      <button
                        onClick={() => void speakChinese((q.example?.zh ?? '').replace(/[【】]/g, ''))}
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-slate-400 hover:bg-pink-100 hover:text-pink-600 dark:bg-slate-800 dark:hover:bg-pink-900/40"
                        title="Nghe câu ví dụ"
                        aria-label="Nghe câu ví dụ"
                      >
                        <span className="material-symbols-outlined text-[18px]">volume_up</span>
                      </button>
                    </div>
                  )}

                  {!correct && <MistakeReviewPanel quizId={quiz.id} questionId={q.id} hasReview={q.has_mistake_review === true} />}

                  {isRelated && q.can_save === true && (
                    <button
                      onClick={() => void handleSave(q)}
                      disabled={saved || savingIds.has(q.id)}
                      className={`self-start rounded-full px-4 py-1.5 text-xs font-bold transition-colors ${
                        saved ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-pink-50 text-[#a43073] hover:bg-pink-100 disabled:opacity-60 dark:bg-pink-900/30 dark:text-pink-400 dark:hover:bg-pink-900/40'
                      }`}
                    >
                      {saved ? 'Đã lưu' : savingIds.has(q.id) ? 'Đang lưu...' : 'Lưu vào Sổ tay'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <button onClick={onBack} className="self-center rounded-full bg-[#a43073] px-6 py-2.5 text-xs font-bold text-white shadow-md hover:bg-[#85145a]">
        Về khu kiểm tra
      </button>
    </div>
  );
};
