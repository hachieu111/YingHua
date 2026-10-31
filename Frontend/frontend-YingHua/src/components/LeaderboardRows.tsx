import React from 'react';
import { BoardRow, Leaderboard } from '../api/gamification';
import { hskLabel } from '../api/dictionary';
import { badgeStyle } from '../data/achievements';
import { PersonAvatar } from './PersonAvatar';
import { VipPill } from './AvatarFrame';

const formatScore = (row: BoardRow): string => row.score.toLocaleString('vi-VN');

const RowBadge: React.FC<{ row: BoardRow }> = ({ row }) => {
  if (!row.badge) return null;
  const style = badgeStyle(row.badge.style_key);
  const Icon = style.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold ${style.color}`}>
      <Icon className="w-3 h-3" aria-hidden="true" />
      {row.badge.name}
    </span>
  );
};

interface LeaderboardRowsProps {
  rows: BoardRow[];
  unitLabel: string;
  /** Hạng của dòng đầu tiên nếu API không gửi hạng. */
  startRank: number;
}

/** Danh sách xếp hạng từ hạng 4 trở đi (hoặc cả trang khi đang xem trang sau). */
export const LeaderboardRows: React.FC<LeaderboardRowsProps> = ({ rows, unitLabel, startRank }) => (
  <div className="flex flex-col rounded-3xl bg-white shadow-soft border border-pink-100 p-4 sm:p-6 dark:bg-slate-800 dark:border-pink-900/40">
    <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100 text-xs font-bold text-slate-400 uppercase tracking-wider dark:border-slate-700">
      <span>Xếp hạng</span>
      <div className="hidden sm:flex items-center gap-10">
        <span className="w-24 text-center">Trình độ</span>
        <span className="w-24 text-right">{unitLabel}</span>
      </div>
      <span className="sm:hidden">{unitLabel}</span>
    </div>

    {rows.length === 0 ? (
      <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">Chưa có thêm người học nào trên bảng này.</p>
    ) : (
      <ul className="divide-y divide-slate-100 dark:divide-slate-700">
        {rows.map((row, index) => (
          <li
            key={`${row.rank ?? startRank + index}-${row.display_name}`}
            className={`flex items-center justify-between p-3.5 rounded-2xl transition-colors ${row.is_me ? 'bg-pink-50/70 dark:bg-pink-900/30' : 'hover:bg-slate-50/70'}`}
          >
            <div className="flex items-center gap-3.5 min-w-0">
              <span className="w-7 text-center text-sm font-bold text-slate-400">{row.rank ?? startRank + index}</span>
              <PersonAvatar row={row} sizeClass="w-10 h-10" />
              <div className="flex flex-col min-w-0 gap-0.5">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-bold text-xs sm:text-sm text-slate-800 truncate dark:text-slate-100">{row.display_name}</span>
                  {row.is_me && <span className="px-2 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[10px] font-bold dark:bg-pink-900/30 dark:text-pink-400">Bạn</span>}
                  {row.is_vip && <VipPill />}
                  <RowBadge row={row} />
                </div>
                <span className="text-[11px] text-slate-400 sm:hidden">{hskLabel(row.hsk_level)}</span>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-10">
              <div className="w-24 text-center">
                <span className="px-2.5 py-1 rounded-full bg-[#eff4ff] text-[#0060ac] text-xs font-bold dark:bg-[#1e293b] dark:text-blue-300">{hskLabel(row.hsk_level)}</span>
              </div>
              <span className="w-24 text-right text-sm font-bold text-[#a43073] dark:text-pink-400">{formatScore(row)}</span>
            </div>
            <span className="sm:hidden text-xs font-bold text-[#a43073] dark:text-pink-400">{formatScore(row)}</span>
          </li>
        ))}
      </ul>
    )}
  </div>
);

interface MyRankCardProps {
  data: Leaderboard;
  periodLabel: string;
  onOpenPrivacy: () => void;
}

/** Thẻ "Vị trí của bạn": hạng, điểm, mốc thưởng kế tiếp; báo rõ khi bạn đang ẩn danh (F16.08). */
export const MyRankCard: React.FC<MyRankCardProps> = ({ data, periodLabel, onOpenPrivacy }) => {
  const { me, next_milestone: milestone } = data;
  return (
    <div className="sticky top-24 z-30 w-full p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-pink-100/90 via-white to-blue-100/80 backdrop-blur-xl shadow-md border border-pink-200 flex flex-col gap-3 dark:from-pink-900/20 dark:via-slate-800 dark:to-blue-900/20 dark:border-pink-900/40">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-center justify-center w-12 h-12 rounded-2xl bg-[#a43073] text-white shadow-xs shrink-0">
            <span className="text-[10px] uppercase font-bold">Hạng</span>
            <span className="text-base font-extrabold leading-tight">{me.rank !== null ? `#${me.rank}` : '—'}</span>
          </div>
          <PersonAvatar row={{ ...me, anonymous: false }} sizeClass="w-12 h-12" />
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-sm text-slate-800 dark:text-slate-100">{me.display_name}</h3>
              <span className="px-2 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[10px] font-bold dark:bg-pink-900/30 dark:text-pink-400">Bạn</span>
            </div>
            <div className="flex items-center gap-2 text-slate-500 text-xs mt-0.5 dark:text-slate-400">
              <span className="font-bold text-[#a43073] dark:text-pink-400">
                {formatScore(me)} {me.unit}
              </span>
              <span>•</span>
              <span>{periodLabel}</span>
              {me.rank === null && <span className="text-slate-400">· Chưa có hạng</span>}
            </div>
          </div>
        </div>

        {milestone && (
          <div className="w-full sm:w-auto flex flex-col sm:items-end gap-1.5 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-200/60 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Chỉ cần thêm <strong className="text-[#a43073] dark:text-pink-400">{milestone.xp_missing.toLocaleString('vi-VN')} EXP</strong> để lọt
              </span>
              <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-900 text-xs font-bold dark:bg-blue-900/30 dark:text-blue-300">Top {milestone.rank}</span>
            </div>
            <div className="w-full sm:w-48 h-2 bg-slate-200 rounded-full overflow-hidden dark:bg-slate-700">
              <div
                className="h-full bg-gradient-to-r from-pink-400 to-[#a43073] rounded-full"
                style={{ width: `${Math.round(Math.min(1, Math.max(0, milestone.ratio)) * 100)}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {data.me_hidden && (
        <div role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-[11px] text-amber-900 dark:bg-amber-900/30 dark:border-amber-900/40 dark:text-amber-300">
          <span>{data.me_hidden_note ?? 'Bạn đang ẩn danh trên bảng xếp hạng.'}</span>
          <button type="button" onClick={onOpenPrivacy} className="font-bold text-[#a43073] hover:underline dark:text-pink-400">
            Đổi trong Cài đặt
          </button>
        </div>
      )}
    </div>
  );
};
