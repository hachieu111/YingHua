import React, { useState } from 'react';
import { errorMessage } from '../api/client';
import { FrameEntry, equipFrame, listFrames } from '../api/rewards';
import { useApiResource } from '../utils/useApiResource';
import { notifyRewardsChanged } from '../utils/useRewards';
import { AvatarFrame } from './AvatarFrame';

const formatDate = (iso: string): string => new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });

interface FrameCardProps {
  frame: FrameEntry;
  busy: boolean;
  onToggle: (frame: FrameEntry) => void;
}

const FrameCard: React.FC<FrameCardProps> = ({ frame, busy, onToggle }) => (
  <div className={`p-5 rounded-3xl bg-white shadow-soft border flex flex-col items-center text-center gap-3 ${frame.equipped ? 'border-[#a43073]' : 'border-pink-100 dark:border-pink-900/40'} dark:bg-slate-800`}>
    <AvatarFrame styleKey={frame.style_key}>
      <span className="w-16 h-16 rounded-full bg-gradient-to-tr from-pink-100 to-blue-100 flex items-center justify-center text-[#a43073] dark:from-pink-900/20 dark:to-blue-900/20">
        <span className="material-symbols-outlined text-[32px]">person</span>
      </span>
    </AvatarFrame>
    <div>
      <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100">{frame.name}</h4>
      {frame.description && <p className="text-[11px] text-slate-500 mt-0.5 dark:text-slate-400">{frame.description}</p>}
      <p className="text-[11px] text-slate-400 mt-1">{frame.acquire_label}</p>
      {frame.owned && frame.expires_at && <p className="text-[11px] text-amber-700 mt-0.5 dark:text-amber-400">Dùng được đến {formatDate(frame.expires_at)}</p>}
    </div>
    {frame.owned || frame.equippable ? (
      <button
        type="button"
        disabled={busy || (!frame.equippable && !frame.equipped)}
        onClick={() => onToggle(frame)}
        className={`px-4 py-2 rounded-full text-xs font-bold transition-colors disabled:opacity-50 ${
          frame.equipped ? 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-[#1e293b] dark:text-slate-100 dark:hover:bg-slate-700' : 'bg-[#a43073] text-white hover:bg-[#85145a]'
        }`}
      >
        {frame.equipped ? 'Tháo khung' : 'Đeo khung'}
      </button>
    ) : (
      <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-500 text-[11px] font-bold dark:bg-[#1e293b] dark:text-slate-400">Chưa sở hữu</span>
    )}
  </div>
);

/** Danh sách khung avatar: sở hữu, đang đeo, cách kiếm; đeo/tháo ngay (F17.08). */
export const RewardFramesTab: React.FC<{ showToast: (message: string) => void }> = ({ showToast }) => {
  const frames = useApiResource(signal => listFrames(signal), []);
  const [busy, setBusy] = useState(false);

  const toggle = async (frame: FrameEntry) => {
    setBusy(true);
    try {
      await equipFrame(frame.equipped ? null : frame.code);
      showToast(frame.equipped ? 'Đã tháo khung avatar.' : `Đã đeo khung "${frame.name}".`);
      notifyRewardsChanged();
      frames.reload();
    } catch (err) {
      showToast(errorMessage(err));
      frames.reload();
    } finally {
      setBusy(false);
    }
  };

  if (frames.loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500 dark:text-slate-400" role="status">
        <span className="w-5 h-5 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
        Đang tải khung avatar...
      </div>
    );
  }
  if (frames.error && !frames.data) {
    return (
      <div role="alert" className="rounded-2xl bg-rose-50 border border-rose-200 p-5 text-center text-sm text-rose-700 dark:bg-rose-900/30 dark:border-rose-900/40 dark:text-rose-400">
        <p>{frames.error}</p>
        <button type="button" onClick={frames.reload} className="mt-3 px-4 py-2 rounded-full bg-white text-rose-700 text-xs font-bold dark:bg-slate-800 dark:text-rose-400">
          Thử lại
        </button>
      </div>
    );
  }
  if (!frames.data || frames.data.length === 0) return <p className="py-12 text-center text-sm text-slate-500 dark:text-slate-400">Chưa có khung avatar nào.</p>;
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {frames.data.map(frame => (
        <FrameCard key={frame.code} frame={frame} busy={busy} onToggle={toggle} />
      ))}
    </div>
  );
};
