import React, { useEffect, useState } from 'react';
import { errorMessage } from '../api/client';
import { ReportType, createErrorReport, isReportDuplicate } from '../api/notifications';

export interface ReportTarget {
  pageId: number;
  /** null: báo lỗi cả trang. */
  bubbleId: number | null;
}

interface ReportErrorDialogProps {
  target: ReportTarget;
  onClose: () => void;
  onDone: (message: string) => void;
}

const MAX_DESCRIPTION = 1000;
const TYPES: { value: ReportType; label: string }[] = [
  { value: 'ocr', label: 'Nhận diện chữ sai' },
  { value: 'translation', label: 'Dịch sai' },
  { value: 'other', label: 'Khác' }
];

/** Hộp thoại báo lỗi nhận diện/dịch (F14.01). Báo trùng được thông báo nhẹ nhàng, không coi là lỗi hệ thống. */
export const ReportErrorDialog: React.FC<ReportErrorDialogProps> = ({ target, onClose, onDone }) => {
  const [reportType, setReportType] = useState<ReportType>('translation');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await createErrorReport({
        page_id: target.pageId,
        bubble_id: target.bubbleId ?? undefined,
        report_type: reportType,
        description: description.trim() || undefined
      });
      onDone('Đã gửi báo lỗi, cảm ơn bạn! Bạn sẽ nhận thông báo khi được xử lý.');
      onClose();
    } catch (err) {
      if (isReportDuplicate(err)) {
        onDone('Bạn đã báo lỗi chỗ này, đang chờ xử lý.');
        onClose();
      } else {
        setError(errorMessage(err));
        setBusy(false);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 dark:bg-black/70 p-4" onMouseDown={() => !busy && onClose()}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Báo lỗi bản dịch"
        className="w-full max-w-md rounded-3xl bg-white p-6 shadow-floating border border-pink-100 dark:bg-[#0f172a] dark:border-slate-700 dark:shadow-none flex flex-col gap-4"
        onMouseDown={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <span className="material-symbols-outlined text-[#a43073] dark:text-pink-400 text-[20px]">flag</span>
            {target.bubbleId === null ? 'Báo lỗi trang này' : 'Báo lỗi câu thoại này'}
          </h3>
          <button onClick={onClose} disabled={busy} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200" aria-label="Đóng">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <fieldset className="flex flex-wrap gap-2">
          <legend className="sr-only">Loại lỗi</legend>
          {TYPES.map(type => (
            <label
              key={type.value}
              className={`cursor-pointer px-3.5 py-1.5 rounded-full text-xs font-bold border transition-all ${
                reportType === type.value ? 'bg-[#a43073] text-white border-[#a43073]' : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50 dark:bg-[#1e293b] dark:text-slate-200 dark:border-slate-700 dark:hover:bg-slate-700'
              }`}
            >
              <input
                type="radio"
                name="report-type"
                value={type.value}
                checked={reportType === type.value}
                onChange={() => setReportType(type.value)}
                className="sr-only"
              />
              {type.label}
            </label>
          ))}
        </fieldset>

        <div>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            maxLength={MAX_DESCRIPTION}
            rows={4}
            placeholder="Mô tả lỗi (không bắt buộc): chữ nào bị nhận sai, bản dịch đúng phải là gì..."
            className="w-full text-xs text-slate-700 p-3 rounded-2xl border border-slate-200 outline-none focus:ring-2 focus:ring-[#f472b6] dark:bg-[#1e293b] dark:text-slate-200 dark:border-slate-700 dark:placeholder:text-slate-500"
            aria-label="Mô tả lỗi"
          />
          <div className="text-right text-[10px] text-slate-400 dark:text-slate-500">{description.length}/{MAX_DESCRIPTION}</div>
        </div>

        {error && <p className="text-xs text-rose-600 dark:text-rose-300">{error}</p>}

        <div className="flex items-center justify-end gap-2">
          <button onClick={onClose} disabled={busy} className="px-4 py-2 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700">
            Hủy
          </button>
          <button
            onClick={() => void submit()}
            disabled={busy}
            className="px-5 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold hover:bg-[#85145a] disabled:opacity-60"
          >
            {busy ? 'Đang gửi...' : 'Gửi báo lỗi'}
          </button>
        </div>
      </div>
    </div>
  );
};
