import React from 'react';
import { BoardRow } from '../api/gamification';
import { hskLabel } from '../api/dictionary';
import { BadgeChip } from './BadgeChip';
import { PersonAvatar } from './PersonAvatar';
import { VipPill } from './AvatarFrame';

interface LeaderboardPodiumProps {
  /** Tối đa 3 người đầu bảng theo thứ tự hạng 1, 2, 3. */
  top: BoardRow[];
  metricLabel: string;
}

const formatScore = (row: BoardRow): string => row.score.toLocaleString('vi-VN');

interface SlotProps {
  row: BoardRow | undefined;
  place: 1 | 2 | 3;
}

const SLOT_STYLES = {
  1: {
    medal: '🥇',
    order: 'order-2',
    avatar: 'w-20 h-20 sm:w-28 sm:h-28 md:w-32 md:h-32',
    box: 'h-44 sm:h-52 md:h-60 rounded-3xl bg-gradient-to-t from-amber-100 via-amber-50 to-white border-t-4 border-amber-300 shadow-lg dark:from-amber-900/20 dark:via-amber-900/20 dark:to-slate-800 dark:border-amber-900/40',
    score: 'text-2xl sm:text-3xl text-slate-900 dark:text-slate-100'
  },
  2: {
    medal: '🥈',
    order: 'order-1',
    avatar: 'w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24',
    box: 'h-32 sm:h-36 md:h-44 rounded-2xl bg-gradient-to-t from-slate-200 via-slate-100 to-white border-t-2 border-slate-300 shadow-xs dark:from-slate-800 dark:via-slate-800 dark:to-slate-800 dark:border-slate-700',
    score: 'text-lg sm:text-xl text-slate-700 dark:text-slate-100'
  },
  3: {
    medal: '🥉',
    order: 'order-3',
    avatar: 'w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24',
    box: 'h-28 sm:h-32 md:h-40 rounded-2xl bg-gradient-to-t from-amber-200/50 via-amber-100/50 to-white border-t-2 border-amber-400 shadow-xs dark:from-amber-900/20 dark:via-amber-900/20 dark:to-slate-800',
    score: 'text-lg sm:text-xl text-amber-900 dark:text-amber-300'
  }
} as const;

const PodiumSlot: React.FC<SlotProps> = ({ row, place }) => {
  const style = SLOT_STYLES[place];
  return (
    <div className={`flex flex-col items-center ${style.order} group`}>
      <div className="relative flex flex-col items-center mb-3 transition-transform duration-300 group-hover:-translate-y-1">
        <span className="px-2.5 py-0.5 rounded-full bg-white/90 text-slate-700 text-xs font-bold shadow-xs mb-1.5 dark:bg-slate-800 dark:text-slate-100">
          {style.medal} #{place}
        </span>
        {row ? (
          <PersonAvatar row={row} sizeClass={style.avatar} />
        ) : (
          <span className={`${style.avatar} rounded-full bg-slate-100 border-2 border-dashed border-slate-300 dark:bg-[#1e293b] dark:border-slate-700`} />
        )}
      </div>
      <div className="text-center mb-2 max-w-full px-1">
        <h4 className="font-bold text-xs sm:text-sm text-slate-800 truncate max-w-[100px] sm:max-w-[140px] dark:text-slate-100">
          {row ? row.display_name : 'Đang chờ bạn'}
        </h4>
        {row && !row.anonymous && (
          <span className="flex flex-wrap items-center justify-center gap-1 mt-0.5">
            {row.hsk_level !== null && (
              <span className="px-2 py-0.5 rounded-full bg-white text-[#0060ac] text-[10px] font-bold shadow-xs dark:bg-slate-800 dark:text-blue-300">{hskLabel(row.hsk_level)}</span>
            )}
            {row.is_vip && <VipPill />}
          </span>
        )}
      </div>
      <div className={`w-full ${style.box} p-3 flex flex-col items-center justify-between overflow-hidden`}>
        <div className="flex flex-col items-center">
          <span className={`font-extrabold font-['Plus_Jakarta_Sans'] ${style.score}`}>{row ? formatScore(row) : '—'}</span>
          {row && <span className="text-[10px] text-slate-500 font-bold uppercase dark:text-slate-400">{row.unit}</span>}
        </div>
        {row?.badge && <BadgeChip badge={row.badge} className="!px-2 !py-0.5 max-w-full [&_span]:truncate" />}
      </div>
    </div>
  );
};

/** Bục vinh danh top 3 của bảng đang xem. */
export const LeaderboardPodium: React.FC<LeaderboardPodiumProps> = ({ top, metricLabel }) => (
  <div className="relative w-full rounded-3xl bg-gradient-to-b from-white via-white/80 to-[#eff4ff] p-6 sm:p-10 shadow-soft border border-pink-100 overflow-hidden dark:from-slate-800 dark:via-slate-800 dark:to-slate-800 dark:border-pink-900/40">
    <div className="absolute -top-20 -left-20 w-64 h-64 bg-amber-100/40 rounded-full blur-3xl pointer-events-none dark:bg-amber-900/30"></div>
    <div className="absolute -bottom-10 right-0 w-72 h-72 bg-pink-100/40 rounded-full blur-3xl pointer-events-none dark:bg-pink-900/30"></div>

    <div className="relative flex items-center justify-between mb-8">
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[#a43073] text-[24px] dark:text-pink-400">workspace_premium</span>
        <span className="text-xl font-bold text-slate-800 font-['Plus_Jakarta_Sans'] dark:text-slate-100">Top 3 · {metricLabel}</span>
      </div>
    </div>

    <div className="relative grid grid-cols-3 items-end gap-2 sm:gap-4 md:gap-6 pt-4">
      <PodiumSlot row={top[1]} place={2} />
      <PodiumSlot row={top[0]} place={1} />
      <PodiumSlot row={top[2]} place={3} />
    </div>
  </div>
);
