import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { ApiError, errorMessage } from '../api/client';
import { newRequestId, unlockSeries } from '../api/rewards';
import { REWARD_SHOP_PATH } from '../routes';
import { notifyRewardsChanged, useRewards } from '../utils/useRewards';

interface UnlockVipDialogProps {
  seriesId: number;
  seriesTitle?: string | null;
  /** Gợi ý từ lỗi VIP_REQUIRED khi ví chưa tải xong. */
  hasTicketsHint?: boolean;
  onClose: () => void;
  /** Gọi sau khi mở khóa thành công để màn bên dưới tải lại chương. */
  onUnlocked: () => void;
  showToast?: (message: string) => void;
}

/** Hộp mở khóa truyện VIP vĩnh viễn bằng 1 vé khi gặp chương khóa (F17.05, F17.06). */
export const UnlockVipDialog: React.FC<UnlockVipDialogProps> = ({ seriesId, seriesTitle, hasTicketsHint, onClose, onUnlocked, showToast }) => {
  const navigate = useNavigate();
  const { wallet } = useRewards();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Cùng một mã yêu cầu cho tới khi có kết quả rõ ràng, để bấm lại sau lỗi mạng không tốn hai vé.
  const requestId = useRef<string | null>(null);

  const tickets = wallet?.ticket_balance;
  const canUnlock = tickets !== undefined ? tickets > 0 : (hasTicketsHint ?? false);

  const unlock = async () => {
    if (busy) return;
    requestId.current = requestId.current ?? newRequestId();
    setBusy(true);
    setError(null);
    try {
      await unlockSeries(seriesId, requestId.current);
      requestId.current = null;
      notifyRewardsChanged();
      showToast?.('Đã mở khóa truyện bằng 1 vé. Chúc bạn đọc vui!');
      onUnlocked();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) requestId.current = null;
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const goShop = () => {
    onClose();
    navigate(REWARD_SHOP_PATH);
  };

  return (
    <div className="fixed inset-0 z-[70] bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={busy ? undefined : onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Mở khóa truyện VIP"
        onClick={event => event.stopPropagation()}
        className="bg-white dark:bg-[#0f172a] rounded-3xl shadow-2xl dark:shadow-none dark:border dark:border-slate-700 w-full max-w-md max-h-[90vh] overflow-y-auto p-5 sm:p-6 flex flex-col gap-4"
      >
        <div className="flex items-center gap-3">
          <span className="w-12 h-12 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center shrink-0 dark:bg-amber-900/30 dark:text-amber-300">
            <span className="material-symbols-outlined text-[28px]">workspace_premium</span>
          </span>
          <div className="min-w-0">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">Truyện dành cho VIP</h3>
            {seriesTitle && <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{seriesTitle}</p>}
          </div>
        </div>

        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          Chương này thuộc truyện VIP. Bạn có thể dùng <strong>1 vé đọc truyện VIP</strong> để mở khóa vĩnh viễn cả truyện, hoặc đang VIP là đọc không giới hạn. Vé và ngày VIP kiếm bằng xu ở cửa hàng đổi thưởng.
        </p>

        <div className="flex items-center justify-between rounded-2xl bg-pink-50 dark:bg-pink-900/20 border border-pink-100 dark:border-pink-900/40 px-4 py-2.5 text-xs">
          <span className="font-semibold text-[#85145a] dark:text-pink-300">Vé đang có</span>
          <span className="text-lg font-extrabold text-slate-800 dark:text-white">{tickets ?? (canUnlock ? '≥ 1' : '—')}</span>
        </div>

        {error && (
          <p role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-900/50 px-3 py-2 text-xs font-semibold text-rose-700 dark:text-rose-400">
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-end gap-2">
          <button type="button" onClick={onClose} disabled={busy} className="px-4 py-2 rounded-full text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50">
            Để sau
          </button>
          {canUnlock ? (
            <button
              type="button"
              onClick={() => void unlock()}
              disabled={busy}
              className="px-5 py-2 rounded-full text-xs font-bold text-white bg-[#a43073] hover:bg-[#85145a] disabled:opacity-60"
            >
              {busy ? 'Đang mở khóa...' : 'Dùng 1 vé mở khóa'}
            </button>
          ) : (
            <button type="button" onClick={goShop} className="px-5 py-2 rounded-full text-xs font-bold text-white bg-[#a43073] hover:bg-[#85145a]">
              Đến cửa hàng đổi vé
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
