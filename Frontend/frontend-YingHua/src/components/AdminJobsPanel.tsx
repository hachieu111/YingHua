import React, { useCallback, useEffect, useState } from 'react';
import { JobInfo, listJobs } from '../api/jobs';
import { LoadState, errorMessage, formatDateTime } from './AdminDataParts';

// Tên tác vụ do máy chủ đặt (F15.01-F15.03); tên lạ vẫn hiển thị nguyên văn.
const JOB_LABELS: Record<string, string> = {
  cleanup_quick_uploads: 'Dọn ảnh tải nhanh hết hạn',
  cleanup_sessions: 'Dọn phiên đăng nhập và liên kết hết hạn',
  cleanup_orphan_files: 'Dọn tệp kết quả mồ côi'
};

const STATUS_STYLE: Record<string, { label: string; className: string }> = {
  ok: { label: 'Thành công', className: 'bg-emerald-100 text-emerald-700' },
  running: { label: 'Đang chạy', className: 'bg-blue-100 text-blue-700' },
  failed: { label: 'Lỗi', className: 'bg-rose-100 text-rose-700' }
};

const formatInterval = (seconds: number): string => {
  if (seconds % 86400 === 0) return `${seconds / 86400} ngày`;
  if (seconds % 3600 === 0) return `${seconds / 3600} giờ`;
  if (seconds % 60 === 0) return `${seconds / 60} phút`;
  return `${seconds} giây`;
};

const summaryText = (summary: Record<string, unknown> | null): string =>
  summary
    ? Object.entries(summary)
        .map(([key, value]) => `${key}: ${String(value)}`)
        .join(' · ')
    : '';

interface AdminJobsPanelProps {
  notify: (message: string) => void;
}

/** Trạng thái các tác vụ nền định kỳ của worker (F15.03). */
export const AdminJobsPanel: React.FC<AdminJobsPanelProps> = ({ notify }) => {
  const [jobs, setJobs] = useState<JobInfo[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    listJobs()
      .then(result => {
        setJobs(result.items);
        setError(null);
      })
      .catch(err => {
        const message = errorMessage(err, 'Không tải được danh sách tác vụ nền');
        setError(message);
        notify(message);
      })
      .finally(() => setLoading(false));
  }, [notify]);

  // Chỉ tải khi mở mục; notify đổi tham chiếu mỗi lần vẽ nên không đưa vào phụ thuộc.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  if (!jobs) return <div className="p-4"><LoadState loading={loading} error={error} onRetry={load} /></div>;

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>{jobs.length} tác vụ định kỳ do worker chạy; thời gian hiển thị theo múi giờ của trình duyệt.</span>
        <button onClick={load} disabled={loading} className="text-xs text-blue-700 font-semibold disabled:opacity-50">Làm mới</button>
      </div>
      {error && <LoadState loading={false} error={error} onRetry={load} />}
      {jobs.length === 0 ? (
        <div className="p-6 text-center text-sm text-slate-500">Chưa có tác vụ nền nào được đăng ký.</div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {jobs.map(job => {
            const status = job.last_status ? (STATUS_STYLE[job.last_status] ?? { label: job.last_status, className: 'bg-slate-100 text-slate-600' }) : null;
            return (
              <article key={job.name} className="rounded-xl border border-slate-100 p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-slate-800">{JOB_LABELS[job.name] ?? job.name}</div>
                    <div className="text-[10px] text-slate-400">{job.name} · chạy mỗi {formatInterval(job.interval_seconds)}</div>
                  </div>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${status?.className ?? 'bg-slate-100 text-slate-600'}`}>
                    {status?.label ?? 'Chưa chạy'}
                  </span>
                </div>
                <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                  <dt className="text-slate-500">Bật</dt>
                  <dd className="font-semibold text-slate-700">{job.enabled ? 'Có' : 'Đã tắt'}</dd>
                  <dt className="text-slate-500">Lần chạy gần nhất</dt>
                  <dd className="font-semibold text-slate-700">{formatDateTime(job.last_started_at)}</dd>
                  <dt className="text-slate-500">Kết thúc</dt>
                  <dd className="font-semibold text-slate-700">{formatDateTime(job.last_finished_at)}</dd>
                  <dt className="text-slate-500">Lần chạy kế tiếp</dt>
                  <dd className="font-semibold text-slate-700">{formatDateTime(job.next_run_at)}</dd>
                  {job.locked_by && (
                    <>
                      <dt className="text-slate-500">Đang giữ bởi</dt>
                      <dd className="font-semibold text-slate-700">{job.locked_by}</dd>
                    </>
                  )}
                </dl>
                {job.last_run?.summary && (
                  <div className="rounded-lg bg-slate-50 px-2.5 py-1.5 text-[10px] text-slate-600">Kết quả: {summaryText(job.last_run.summary)}</div>
                )}
                {job.last_run?.error_message && (
                  <div className="rounded-lg bg-rose-50 px-2.5 py-1.5 text-[10px] text-rose-700" role="alert">{job.last_run.error_message}</div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
};
