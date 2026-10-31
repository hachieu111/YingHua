import React, { useState } from 'react';
import { Link } from 'react-router';
import { BLADE_GAME_PATH, REWARD_SHOP_PATH } from '../routes';
import { useRewards } from '../utils/useRewards';
import { RewardLedgerTab } from './RewardLedgerTab';
import { WalletSummary } from './WalletSummary';

/** Ví của tôi trên hồ sơ: XP, hạng mùa, xu, vé, VIP, khung đang đeo và lịch sử ví (F16.03, F17.02, F17.03). */
export const ProfileWalletCard: React.FC = () => {
  const { wallet, me, loading, error, reload } = useRewards();
  const [showLedger, setShowLedger] = useState(false);
  return (
    <div className="p-5 sm:p-6 rounded-3xl bg-white dark:bg-[#0f172a] shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 flex flex-col gap-4 min-w-0 transition-colors duration-300">
      <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
        <span className="material-symbols-outlined text-[#a43073] dark:text-pink-400 text-[20px]">account_balance_wallet</span>
        <span>Ví &amp; điểm kinh nghiệm</span>
      </h3>

      {error && !wallet && !me && (
        <p role="alert" className="text-xs text-rose-600 dark:text-rose-300">
          Chưa tải được ví của bạn.{' '}
          <button type="button" onClick={reload} className="font-bold underline">
            Thử lại
          </button>
        </p>
      )}

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2.5 rounded-2xl bg-[#eff4ff] dark:bg-slate-800">
          <div className="text-lg font-extrabold text-[#0060ac] dark:text-blue-300">{me ? me.xp_today.toLocaleString('vi-VN') : '—'}</div>
          <div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">XP hôm nay</div>
        </div>
        <div className="p-2.5 rounded-2xl bg-[#eff4ff] dark:bg-slate-800">
          <div className="text-lg font-extrabold text-[#a43073] dark:text-pink-400">{me ? me.xp_total.toLocaleString('vi-VN') : '—'}</div>
          <div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">Tổng XP</div>
        </div>
        <div className="p-2.5 rounded-2xl bg-[#eff4ff] dark:bg-slate-800">
          <div className="text-lg font-extrabold text-amber-600 dark:text-amber-400">{me?.season_rank != null ? `#${me.season_rank}` : '—'}</div>
          <div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">Hạng mùa</div>
        </div>
      </div>
      {me?.next_streak_milestone && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400">
          Còn {me.next_streak_milestone.days_left} ngày nữa để chạm mốc chuỗi {me.next_streak_milestone.days} ngày.
        </p>
      )}

      <WalletSummary wallet={wallet} loading={loading} stacked />

      {wallet?.equipped_frame && <p className="text-[11px] text-slate-500 dark:text-slate-400">Khung avatar đang đeo: <strong>{wallet.equipped_frame.name}</strong></p>}

      <div className="flex flex-wrap gap-2">
        <Link to={REWARD_SHOP_PATH} className="px-4 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold hover:bg-[#85145a] transition-colors flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px]">storefront</span>
          Cửa hàng đổi thưởng
        </Link>
        <Link to={BLADE_GAME_PATH} className="px-4 py-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px]">swords</span>
          Phi Kiếm Trảm Tự
        </Link>
        <button
          type="button"
          onClick={() => setShowLedger(value => !value)}
          aria-expanded={showLedger}
          className="px-4 py-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors flex items-center gap-1.5"
        >
          <span className="material-symbols-outlined text-[16px]">receipt_long</span>
          {showLedger ? 'Ẩn lịch sử ví' : 'Lịch sử ví'}
        </button>
      </div>

      {showLedger && <RewardLedgerTab compact />}
    </div>
  );
};
