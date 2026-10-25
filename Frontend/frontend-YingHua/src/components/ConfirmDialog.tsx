import React from 'react';

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Hộp xác nhận cho thao tác khó hoàn tác (xóa từ, xóa ngữ cảnh, đặt lại thẻ). */
export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({ title, message, confirmLabel, busy = false, onConfirm, onCancel }) => (
  <div className="fixed inset-0 z-[70] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4" onClick={busy ? undefined : onCancel}>
    <div
      className="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-6 flex flex-col gap-4"
      onClick={e => e.stopPropagation()}
      role="alertdialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="flex flex-col gap-1.5">
        <h3 className="text-lg font-bold text-slate-800 font-['Plus_Jakarta_Sans']">{title}</h3>
        <p className="text-sm text-slate-600 leading-relaxed">{message}</p>
      </div>
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={onCancel}
          disabled={busy}
          className="px-4 py-2 rounded-full text-xs font-bold text-slate-600 hover:bg-slate-100 disabled:opacity-50"
        >
          Hủy
        </button>
        <button
          onClick={onConfirm}
          disabled={busy}
          className="px-5 py-2 rounded-full text-xs font-bold text-white bg-[#a43073] hover:bg-[#85145a] disabled:opacity-60"
        >
          {busy ? 'Đang xử lý...' : confirmLabel}
        </button>
      </div>
    </div>
  </div>
);
