import React, { useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { ErrorReport, ReportStatus, ReportType, listMyErrorReports } from '../api/notifications';

export const REPORT_TYPE_LABEL: Record<ReportType, string> = { ocr: 'Nhận diện sai', translation: 'Dịch sai', other: 'Khác' };
const STATUS_LABEL: Record<ReportStatus, string> = { new: 'Đang chờ xử lý', resolved: 'Đã xử lý', rejected: 'Bị từ chối' };
const STATUS_STYLE: Record<ReportStatus, string> = {
  new: 'bg-amber-100 text-amber-800',
  resolved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-slate-200 text-slate-700'
};
const PAGE_SIZE = 20;

const where = (report: ErrorReport): string => {
  const parts: string[] = [];
  if (report.series_title) parts.push(report.series_title);
  if (report.chapter_number !== null) parts.push(`Chương ${report.chapter_number}`);
  if (report.page_no !== null) parts.push(`Trang ${report.page_no}`);
  return parts.join(' · ') || 'Trang đã bị xóa';
};

/** "Báo lỗi của tôi" (F14.01): trạng thái và ghi chú xử lý của các báo lỗi đã gửi, tải lại khi quay lại tab. */
export const ProfileErrorReports: React.FC = () => {
  const [items, setItems] = useState<ErrorReport[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === 'visible') setTick(value => value + 1);
    };
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listMyErrorReports(1, PAGE_SIZE, controller.signal)
      .then(page => {
        setItems(page.items);
        setTotal(page.total);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [tick]);

  if (error) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-2xl bg-rose-50 p-4 text-sm text-rose-700">
        <span>{error}</span>
        <button onClick={() => setTick(value => value + 1)} className="px-4 py-1.5 rounded-full bg-[#a43073] text-white text-xs font-bold">Thử lại</button>
      </div>
    );
  }
  if (loading && items.length === 0) return <div className="py-10 text-center text-sm text-slate-500">Đang tải...</div>;
  if (items.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-slate-500">
        Bạn chưa báo lỗi nào. Khi gặp bản dịch sai, hãy bấm “Báo lỗi” ngay trong trình đọc.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {items.map(report => (
        <div key={report.id} className="p-4 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-bold text-slate-800">{where(report)}</span>
            <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${STATUS_STYLE[report.status]}`}>{STATUS_LABEL[report.status]}</span>
          </div>
          <div className="text-[11px] text-slate-500">
            {REPORT_TYPE_LABEL[report.report_type]} · {new Date(report.created_at).toLocaleString('vi-VN', { hour12: false })}
          </div>
          {report.bubble_text_zh && (
            <div className="text-xs text-slate-600">
              <span className="font-['Noto_Serif_SC'] font-bold">{report.bubble_text_zh}</span>
              {report.bubble_text_vi && <span className="text-slate-500"> — {report.bubble_text_vi}</span>}
            </div>
          )}
          {report.description && <p className="text-xs text-slate-700 break-words">{report.description}</p>}
          {report.resolution_note && (
            <p className="text-xs rounded-xl bg-pink-50 border border-pink-100 p-2.5 text-[#85145a] break-words">
              Ghi chú xử lý: {report.resolution_note}
            </p>
          )}
        </div>
      ))}
      {total > items.length && <p className="text-center text-[11px] text-slate-400">Đang hiển thị {items.length} báo lỗi gần nhất trên tổng {total}.</p>}
    </div>
  );
};
