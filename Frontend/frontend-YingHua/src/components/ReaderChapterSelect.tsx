import React from 'react';
import { ApiChapter } from '../api/library';
import { formatChapterNumber } from '../utils/format';

interface ReaderChapterSelectProps {
  chapters: ApiChapter[];
  currentChapterId: number | null;
  onSelect: (chapterId: number) => void;
}

/** Ô chọn chương của truyện đang đọc; chỉ hiện khi truyện có nhiều hơn một chương đọc được. */
export const ReaderChapterSelect: React.FC<ReaderChapterSelectProps> = ({ chapters, currentChapterId, onSelect }) => {
  if (chapters.length < 2 || currentChapterId === null) return null;
  return (
    <select
      value={currentChapterId}
      onChange={event => onSelect(Number(event.target.value))}
      aria-label="Chọn chương"
      className="max-w-[14rem] truncate rounded-full border border-pink-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 outline-none focus:ring-2 focus:ring-pink-200 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-200 dark:focus:ring-pink-900/40"
    >
      {chapters.map(chapter => (
        <option key={chapter.id} value={chapter.id}>
          {`${chapter.is_locked ? '🔒 ' : ''}Chương ${formatChapterNumber(chapter.number)}${chapter.title ? `: ${chapter.title}` : ''}`}
        </option>
      ))}
    </select>
  );
};
