import React from 'react';
import { Link } from 'react-router';
import { listDecks } from '../api/vocab';
import { deckReviewPath } from '../routes';
import { useApiResource } from '../utils/useApiResource';

interface ProfileSeriesDecksProps {
  /** Đưa người học tới danh mục truyện khi chưa có bộ thẻ nào. */
  onBrowse: () => void;
}

/** Bộ flashcard theo từng truyện lấy từ Sổ tay (F08.10); mỗi bộ có lối thẳng tới trang ôn đúng bộ đó. */
export const ProfileSeriesDecks: React.FC<ProfileSeriesDecksProps> = ({ onBrowse }) => {
  const decks = useApiResource(signal => listDecks(signal), []);

  if (decks.loading) return <p className="text-sm text-slate-500 dark:text-slate-400" role="status">Đang tải bộ flashcard theo truyện...</p>;
  if (decks.error && !decks.data) {
    return (
      <p role="alert" className="text-sm text-rose-600 dark:text-rose-300">
        {decks.error}{' '}
        <button type="button" onClick={decks.reload} className="font-bold underline">Thử lại</button>
      </p>
    );
  }

  const seriesDecks = (decks.data ?? []).filter(deck => deck.kind === 'series');
  if (seriesDecks.length === 0) {
    return (
      <div className="p-8 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 text-center flex flex-col items-center gap-3">
        <span className="material-symbols-outlined text-[40px] text-pink-300 dark:text-pink-400/70">style</span>
        <p className="text-sm text-slate-600 dark:text-slate-300">Bạn chưa có bộ flashcard theo truyện nào. Hãy lưu từ khi đọc truyện, bộ thẻ sẽ tự xuất hiện ở đây.</p>
        <button type="button" onClick={onBrowse} className="px-5 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold shadow-md hover:bg-[#85145a]">
          Khám phá truyện
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {seriesDecks.map(deck => {
        const percent = deck.word_count > 0 ? Math.round((deck.reviewed_count / deck.word_count) * 100) : 0;
        const done = deck.due_count === 0;
        return (
          <div key={deck.key} className="p-5 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 flex flex-col justify-between min-w-0 transition-colors duration-300">
            <div>
              <div className="flex items-center justify-between gap-2">
                <span className="px-2.5 py-0.5 rounded-full bg-pink-100 dark:bg-pink-900/30 text-[#a43073] dark:text-pink-400 text-xs font-bold truncate">{deck.title}</span>
                <span className="text-xs text-slate-400 dark:text-slate-500 shrink-0">{deck.word_count} từ vựng</span>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs font-semibold">
                <span className="text-slate-500 dark:text-slate-400">Đã ôn: {deck.reviewed_count}/{deck.word_count}</span>
                <span className={done ? 'text-emerald-600 dark:text-emerald-400' : 'text-[#a43073] dark:text-pink-400'}>{done ? 'Không có thẻ đến hạn' : `Cần ôn: ${deck.due_count} thẻ`}</span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-700 h-1.5 rounded-full mt-1.5 overflow-hidden" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={`Tiến độ bộ ${deck.title}`}>
                <div className={`${done ? 'bg-emerald-500' : 'bg-[#a43073]'} h-full rounded-full`} style={{ width: `${percent}%` }}></div>
              </div>
            </div>
            <Link
              to={deckReviewPath(deck.key)}
              className={`mt-4 w-full py-2.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1 ${
                done ? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700' : 'bg-[#f472b6] dark:bg-[#a43073] text-white shadow-xs hover:opacity-95'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">{done ? 'replay' : 'psychology'}</span>
              <span>{done ? 'Xem lại bộ này' : 'Ôn tập ngay'}</span>
            </Link>
          </div>
        );
      })}
    </div>
  );
};
