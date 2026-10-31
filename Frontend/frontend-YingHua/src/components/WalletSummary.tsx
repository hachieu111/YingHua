import React from 'react';
import { Wallet } from '../api/rewards';

export const formatVipUntil = (iso: string | null): string =>
  iso ? new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—';

interface WalletSummaryProps {
  wallet: Wallet | null;
  loading?: boolean;
  /** Xếp ba ô thành một cột (khung hẹp như cột bên của hồ sơ). */
  stacked?: boolean;
}

/** Ba ô số dư: xu, vé đọc truyện VIP và trạng thái VIP (F17.02, F17.03). */
export const WalletSummary: React.FC<WalletSummaryProps> = ({ wallet, loading = false, stacked = false }) => {
  const placeholder = loading ? '…' : '—';
  return (
    <div className={`grid grid-cols-1 gap-3 ${stacked ? '' : 'sm:grid-cols-3'}`}>
      <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-center gap-3 dark:bg-amber-900/30 dark:border-amber-900/40">
        <span className="w-10 h-10 rounded-full bg-amber-200 text-amber-900 flex items-center justify-center dark:bg-amber-900/40 dark:text-amber-300">
          <span className="material-symbols-outlined">toll</span>
        </span>
        <div className="flex flex-col">
          <span className="text-[11px] font-bold text-amber-800 uppercase dark:text-amber-300">Xu Sakura</span>
          <span className="text-2xl font-extrabold text-slate-800 leading-tight dark:text-slate-100">
            {wallet ? wallet.coin_balance.toLocaleString('vi-VN') : placeholder}
          </span>
        </div>
      </div>
      <div className="p-4 rounded-2xl bg-pink-50 border border-pink-200 flex items-center gap-3 dark:bg-pink-900/30 dark:border-pink-900/40">
        <span className="w-10 h-10 rounded-full bg-pink-200 text-[#85145a] flex items-center justify-center dark:bg-pink-900/40 dark:text-pink-300">
          <span className="material-symbols-outlined">confirmation_number</span>
        </span>
        <div className="flex flex-col">
          <span className="text-[11px] font-bold text-[#85145a] uppercase dark:text-pink-300">Vé đọc truyện VIP</span>
          <span className="text-2xl font-extrabold text-slate-800 leading-tight dark:text-slate-100">{wallet ? wallet.ticket_balance : placeholder}</span>
        </div>
      </div>
      <div className="p-4 rounded-2xl bg-blue-50 border border-blue-200 flex items-center gap-3 dark:bg-blue-900/30 dark:border-blue-900/40">
        <span className="w-10 h-10 rounded-full bg-blue-200 text-blue-900 flex items-center justify-center dark:bg-blue-900/40 dark:text-blue-300">
          <span className="material-symbols-outlined">workspace_premium</span>
        </span>
        <div className="flex flex-col">
          <span className="text-[11px] font-bold text-blue-900 uppercase dark:text-blue-300">Thành viên VIP</span>
          <span className="text-sm font-extrabold text-slate-800 leading-tight dark:text-slate-100">
            {!wallet ? placeholder : wallet.vip.is_active ? `Còn ${wallet.vip.days_left} ngày` : 'Chưa kích hoạt'}
          </span>
          {wallet?.vip.is_active && <span className="text-[10px] text-slate-500 dark:text-slate-400">Đến hết {formatVipUntil(wallet.vip.vip_until)}</span>}
        </div>
      </div>
    </div>
  );
};
