import React from 'react';
import { statusLabel } from '../api/imaging';
import { TranslationStatus } from '../api/library';

const STYLES: Record<TranslationStatus, { box: string; icon: string; spin?: boolean }> = {
  queued: { box: 'bg-amber-50 text-amber-800 border-amber-200', icon: 'schedule' },
  running: { box: 'bg-blue-50 text-blue-800 border-blue-200', icon: 'progress_activity', spin: true },
  done: { box: 'bg-emerald-50 text-emerald-800 border-emerald-200', icon: 'check_circle' },
  failed: { box: 'bg-red-50 text-red-700 border-red-200', icon: 'error' }
};

/** Nhãn trạng thái xử lý ảnh (đang xếp hàng / đang xử lý / xong / lỗi). */
export const StatusPill: React.FC<{ status: TranslationStatus | null; textReady?: boolean }> = ({ status, textReady = false }) => {
  const partial = textReady && (status === 'queued' || status === 'running');
  const style = partial
    ? { box: 'bg-sky-50 text-sky-800 border-sky-200', icon: 'text_fields', spin: false }
    : status
      ? STYLES[status] : { box: 'bg-slate-50 text-slate-600 border-slate-200', icon: 'hourglass_empty', spin: false };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold ${style.box}`}>
      <span className={`material-symbols-outlined text-[13px] ${style.spin ? 'animate-spin' : ''}`}>{style.icon}</span>
      {partial ? 'Đã có chữ' : statusLabel(status)}
    </span>
  );
};
