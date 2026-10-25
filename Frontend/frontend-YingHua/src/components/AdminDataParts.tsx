import React from 'react';
import { ApiError } from '../api/client';

export const errorMessage = (err: unknown, fallback: string): string => (err instanceof ApiError ? err.message : fallback);

export const formatDateTime = (iso: string | null | undefined): string =>
  iso ? new Date(iso).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' }) : '—';

interface LoadStateProps {
  loading: boolean;
  error: string | null;
  empty?: boolean;
  emptyText?: string;
  onRetry?: () => void;
}

/** Trạng thái đang tải / lỗi / rỗng dùng chung cho các tab dữ liệu người dùng. */
export const LoadState: React.FC<LoadStateProps> = ({ loading, error, empty, emptyText = 'Chưa có dữ liệu', onRetry }) => {
  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center gap-2 text-xs text-slate-400">
        <span className="w-4 h-4 border-2 border-pink-300 border-t-transparent rounded-full animate-spin"></span>Đang tải...
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert" className="p-4 rounded-xl bg-rose-50 text-xs font-semibold text-rose-700 flex items-center justify-between gap-3">
        <span>{error}</span>
        {onRetry && <button onClick={onRetry} className="px-3 py-1 rounded-full bg-white text-rose-700 font-bold">Thử lại</button>}
      </div>
    );
  }
  return empty ? <div className="p-6 text-center text-sm text-slate-500">{emptyText}</div> : null;
};

interface PagerProps {
  page: number;
  size: number;
  total: number;
  onPage: (page: number) => void;
}

export const Pager: React.FC<PagerProps> = ({ page, size, total, onPage }) => {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex items-center justify-between pt-3 text-[11px] text-slate-500">
      <span>Trang {page}/{pages} · {total} mục</span>
      <div className="flex gap-1">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="px-3 py-1 rounded-full bg-slate-100 disabled:opacity-40">Trước</button>
        <button disabled={page >= pages} onClick={() => onPage(page + 1)} className="px-3 py-1 rounded-full bg-slate-100 disabled:opacity-40">Sau</button>
      </div>
    </div>
  );
};

export const Chip: React.FC<{ active: boolean; onClick: () => void; children: React.ReactNode }> = ({ active, onClick, children }) => (
  <button onClick={onClick} className={`px-3 py-1.5 rounded-full text-[11px] font-semibold ${active ? 'bg-[#a43073] text-white' : 'bg-slate-100 text-slate-600'}`}>
    {children}
  </button>
);

export const Stat: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="rounded-xl border border-slate-100 p-3">
    <div className="text-[10px] font-semibold text-slate-500">{label}</div>
    <div className="mt-1 text-lg font-bold text-slate-800">{value}</div>
  </div>
);

export const STATUS_LABEL: Record<string, string> = { learning: 'Đang học', known: 'Đã thuộc', ignored: 'Bỏ qua' };
