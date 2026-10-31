import React, { useCallback, useEffect, useState } from 'react';
import { AdminTranslation, AdminTranslationPage, listTranslations, retryTranslation, statusLabel } from '../api/imaging';
import { TranslationStatus } from '../api/library';
import { Chip, LoadState, Pager, errorMessage, formatDateTime } from './AdminDataParts';
import { StatusPill } from './StatusPill';

const PAGE_SIZE = 10;
const FILTERS: { key: TranslationStatus | 'all'; label: string }[] = [
  { key: 'all', label: 'Tất cả' },
  { key: 'queued', label: 'Đang xếp hàng' },
  { key: 'running', label: 'Đang xử lý' },
  { key: 'failed', label: 'Lỗi' },
  { key: 'done', label: 'Hoàn tất' }
];
const REFRESH_MS = 10000;

const formatDuration = (ms: number | null): string => (ms === null ? '—' : `${(ms / 1000).toFixed(1)} giây`);

interface AdminImagingPanelProps {
  notify: (message: string) => void;
}

/** Giám sát hàng đợi xử lý ảnh và chạy lại bản dịch lỗi (F04.05, F04.06). */
export const AdminImagingPanel: React.FC<AdminImagingPanelProps> = ({ notify }) => {
  const [filter, setFilter] = useState<TranslationStatus | 'all'>('all');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminTranslationPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<number | null>(null);

  const load = useCallback(
    (silent = false) => {
      if (!silent) setLoading(true);
      listTranslations({ status: filter === 'all' ? undefined : filter, page, size: PAGE_SIZE })
        .then(result => {
          setData(result);
          setError(null);
        })
        .catch(err => setError(errorMessage(err, 'Không tải được hàng đợi xử lý ảnh')))
        .finally(() => setLoading(false));
    },
    [filter, page]
  );

  useEffect(() => load(), [load]);

  // Tự làm mới khi còn bản dịch đang chạy để quản trị viên thấy tiến triển.
  const active = (data?.counts.queued ?? 0) + (data?.counts.running ?? 0) > 0;
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => load(true), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [active, load]);

  const handleRetry = async (item: AdminTranslation) => {
    setRetrying(item.id);
    try {
      await retryTranslation(item.id);
      notify(`Đã gửi lệnh chạy lại bản dịch #${item.id}.`);
      load(true);
    } catch (err) {
      notify(errorMessage(err, 'Không chạy lại được bản dịch'));
    } finally {
      setRetrying(null);
    }
  };

  const counts = data?.counts ?? {};

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: 'Đang xếp hàng', value: counts.queued ?? 0 },
          { label: 'Đang xử lý', value: counts.running ?? 0 },
          { label: 'Lỗi', value: counts.failed ?? 0 },
          { label: 'Hoàn tất', value: counts.done ?? 0 }
        ].map(stat => (
          <div key={stat.label} className="rounded-xl border border-slate-100 dark:border-slate-700 p-3">
            <div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">{stat.label}</div>
            <div className="mt-1 text-xl font-extrabold text-slate-900 dark:text-white">{stat.value}</div>
          </div>
        ))}
        <div className="rounded-xl border border-slate-100 dark:border-slate-700 p-3">
          <div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">Thời gian xử lý trung bình</div>
          <div className="mt-1 text-xl font-extrabold text-slate-900 dark:text-white">{formatDuration(data?.avg_processing_ms ?? null)}</div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {FILTERS.map(item => (
          <Chip key={item.key} active={filter === item.key} onClick={() => { setFilter(item.key); setPage(1); }}>
            {item.label}
          </Chip>
        ))}
        <button onClick={() => load()} className="ml-auto text-xs text-blue-700 dark:text-blue-300 font-semibold">Làm mới</button>
      </div>

      {!data ? (
        <LoadState loading={loading} error={error} onRetry={() => load()} />
      ) : (
        <>
          {error && <LoadState loading={false} error={error} onRetry={() => load()} />}
          {data.items.length === 0 ? (
            <div className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">Không có bản dịch nào ở trạng thái này.</div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-700 rounded-xl border border-slate-100 dark:border-slate-700">
              {data.items.map(item => (
                <div key={item.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-100">Bản dịch #{item.id}</span>
                      <StatusPill status={item.status} />
                      <span className="text-[10px] text-slate-500 dark:text-slate-400">Lần thử: {item.attempts}</span>
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">
                      Xếp hàng {formatDateTime(item.queued_at)} · Xong {formatDateTime(item.finished_at)} · {formatDuration(item.processing_ms)}
                      {item.worker_id ? ` · Worker ${item.worker_id}` : ''}
                    </div>
                    {item.status === 'failed' && (
                      <div className="text-[11px] text-red-600 dark:text-red-400">
                        {item.error_step ? `Bước “${item.error_step}”: ` : ''}
                        {item.error_message ?? statusLabel('failed')}
                      </div>
                    )}
                  </div>
                  {item.status === 'failed' && (
                    <button
                      onClick={() => handleRetry(item)}
                      disabled={retrying === item.id}
                      className="shrink-0 rounded-full bg-pink-500 dark:bg-[#a43073] px-3.5 py-1.5 text-[11px] font-bold text-white hover:bg-pink-600 dark:hover:bg-[#85145a] disabled:opacity-60"
                    >
                      {retrying === item.id ? 'Đang gửi...' : 'Chạy lại'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          <Pager page={data.page} size={data.size} total={data.total} onPage={setPage} />
        </>
      )}
    </div>
  );
};
