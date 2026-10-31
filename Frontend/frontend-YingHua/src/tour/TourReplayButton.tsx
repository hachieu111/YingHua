import React from 'react';
import { useTour } from './TourProvider';

interface TourReplayButtonProps {
  className?: string;
}

/** Nút dấu hỏi nhỏ: xem lại hướng dẫn của màn hình đang mở. */
export const TourReplayButton: React.FC<TourReplayButtonProps> = ({ className = '' }) => {
  const { replay } = useTour();
  return (
    <button
      type="button"
      onClick={replay}
      title="Xem lại hướng dẫn"
      aria-label="Xem lại hướng dẫn"
      className={`h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-slate-500 border border-pink-100 hover:border-pink-300 hover:text-[#a43073] transition-colors dark:bg-[#1e293b] dark:border-slate-700 dark:text-slate-300 dark:hover:text-pink-400 ${className}`}
    >
      <span translate="no" className="material-symbols-outlined text-[18px]" aria-hidden="true">help</span>
    </button>
  );
};
