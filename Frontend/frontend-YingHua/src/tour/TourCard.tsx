import React from 'react';

export interface TourCardActions {
  onBack: () => void;
  onNext: () => void;
  onSkip: () => void;
  onNeverAgain: () => void;
  onToggleNeverAgain: (checked: boolean) => void;
}

interface TourCardProps extends TourCardActions {
  title: string;
  body: string;
  welcome: boolean;
  /** Số thứ tự bước, không tính thẻ chào. */
  stepNumber: number;
  stepTotal: number;
  finishLabel: string;
  neverAgain: boolean;
  titleId: string;
  bodyId: string;
}

const PRIMARY_BUTTON = 'rounded-full bg-[#a43073] px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors hover:bg-[#85145a]';
const SECONDARY_BUTTON = 'rounded-full px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700';

/** Nội dung thẻ hướng dẫn: thẻ chào hoặc một bước. Vị trí do TourOverlay quyết định. */
export const TourCard: React.FC<TourCardProps> = ({
  title,
  body,
  welcome,
  stepNumber,
  stepTotal,
  finishLabel,
  neverAgain,
  titleId,
  bodyId,
  onBack,
  onNext,
  onSkip,
  onNeverAgain,
  onToggleNeverAgain
}) => {
  if (welcome) {
    return (
      <div className="flex flex-col items-center gap-3 p-6 text-center">
        <img src="/assets/imagetest/media_1792630135660_75497c66.png" alt="" className="h-12 w-12 rounded-full border border-pink-200 object-contain p-0.5 dark:border-pink-900/40" />
        <h2 id={titleId} className="text-lg font-extrabold text-[#a43073] dark:text-pink-400 font-['Plus_Jakarta_Sans']">{title}</h2>
        <p id={bodyId} className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{body}</p>
        <span className="inline-flex items-center gap-1 rounded-full bg-pink-50 px-2.5 py-1 text-[11px] font-bold text-[#a43073] dark:bg-pink-900/20 dark:text-pink-400">
          <span className="material-symbols-outlined text-[14px]" aria-hidden="true">schedule</span>
          Khoảng 1 phút
        </span>
        <div className="mt-1 flex items-center gap-2">
          <button type="button" onClick={onSkip} className={SECONDARY_BUTTON}>Để sau</button>
          <button type="button" onClick={onNext} className={PRIMARY_BUTTON}>Bắt đầu xem</button>
        </div>
        <button type="button" onClick={onNeverAgain} className="text-[11px] font-semibold text-slate-500 hover:underline dark:text-slate-400">
          Không nhắc lại
        </button>
      </div>
    );
  }

  const isLast = stepNumber === stepTotal;
  const percent = Math.round((stepNumber / stepTotal) * 100);

  return (
    <div className="flex flex-col gap-3 p-5">
      <div className="flex items-center gap-3">
        <span className="text-[11px] font-bold tabular-nums text-[#a43073] dark:text-pink-400" aria-label={`Bước ${stepNumber} trên ${stepTotal}`}>
          {stepNumber}/{stepTotal}
        </span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-pink-100 dark:bg-slate-700" aria-hidden="true">
          <div className="tour-progress h-full rounded-full bg-[#a43073] dark:bg-pink-400" style={{ width: `${percent}%` }}></div>
        </div>
        <button type="button" onClick={onSkip} className="text-[11px] font-semibold text-slate-500 hover:underline dark:text-slate-400">
          Bỏ qua
        </button>
      </div>

      <div>
        <h2 id={titleId} className="text-sm font-extrabold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">{title}</h2>
        <p id={bodyId} className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-300">{body}</p>
      </div>

      <div className="flex items-center justify-between gap-2">
        <label className="flex cursor-pointer items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
          <input
            type="checkbox"
            checked={neverAgain}
            onChange={event => onToggleNeverAgain(event.target.checked)}
            className="h-3.5 w-3.5 cursor-pointer accent-[#a43073]"
          />
          Không nhắc lại
        </label>
        <div className="flex items-center gap-1">
          {stepNumber > 1 && <button type="button" onClick={onBack} className={SECONDARY_BUTTON}>Quay lại</button>}
          <button type="button" onClick={onNext} className={PRIMARY_BUTTON}>{isLast ? finishLabel : 'Tiếp tục'}</button>
        </div>
      </div>
    </div>
  );
};
