import React, { useRef, useState } from 'react';
import { Link } from 'react-router';
import { ApiError, errorMessage } from '../api/client';
import { ShopItem, listShopItems, newRequestId, redeemItem } from '../api/rewards';
import { BLADE_GAME_PATH } from '../routes';
import { notifyRewardsChanged, useRewards } from '../utils/useRewards';
import { useApiResource } from '../utils/useApiResource';
import { ConfirmDialog } from './ConfirmDialog';
import { RewardFramesTab } from './RewardFramesTab';
import { RewardLedgerTab } from './RewardLedgerTab';
import { WalletSummary } from './WalletSummary';
import { useTourPage } from '../tour/TourProvider';

type ShopTab = 'items' | 'frames' | 'ledger';

const TABS: { id: ShopTab; label: string; icon: string }[] = [
  { id: 'items', label: 'Đổi thưởng', icon: 'storefront' },
  { id: 'frames', label: 'Khung avatar', icon: 'account_circle' },
  { id: 'ledger', label: 'Lịch sử ví', icon: 'receipt_long' }
];

const KIND_ICON: Record<ShopItem['kind'], { icon: string; box: string }> = {
  vip_days: { icon: 'workspace_premium', box: 'bg-blue-100 text-blue-900 dark:bg-blue-900/30 dark:text-blue-300' },
  vip_ticket: { icon: 'confirmation_number', box: 'bg-pink-100 text-[#85145a] dark:bg-pink-900/30 dark:text-pink-300' },
  avatar_frame: { icon: 'account_circle', box: 'bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-300' }
};

const unavailableReason = (item: ShopItem): string | null => {
  if (item.owned) return 'Bạn đã sở hữu khung này';
  if (item.remaining !== null && item.remaining <= 0) return 'Hết lượt đổi';
  if (!item.affordable) return 'Chưa đủ xu';
  return null;
};

interface ShopItemCardProps {
  item: ShopItem;
  onRedeem: (item: ShopItem) => void;
}

const ShopItemCard: React.FC<ShopItemCardProps> = ({ item, onRedeem }) => {
  const look = KIND_ICON[item.kind];
  const reason = unavailableReason(item);
  return (
    <div className="p-4 sm:p-5 rounded-3xl bg-white shadow-soft border border-pink-100 flex flex-col justify-between gap-4 min-w-0 dark:bg-slate-800 dark:border-pink-900/40">
      <div className="flex items-start gap-3">
        <span className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${look.box}`}>
          <span className="material-symbols-outlined text-[26px]">{look.icon}</span>
        </span>
        <div className="min-w-0">
          <h4 className="text-sm font-bold text-slate-800 break-words dark:text-slate-100">{item.name}</h4>
          {item.description && <p className="text-xs text-slate-500 mt-0.5 break-words dark:text-slate-400">{item.description}</p>}
          {item.per_user_limit !== null && (
            <p className="text-[11px] text-slate-400 mt-1">
              Còn {item.remaining ?? item.per_user_limit}/{item.per_user_limit} lượt đổi của bạn
            </p>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="inline-flex items-center gap-1 text-sm font-extrabold text-amber-700 dark:text-amber-400">
          <span className="material-symbols-outlined text-[18px]">toll</span>
          {item.price_coins.toLocaleString('vi-VN')} xu
        </span>
        <button
          type="button"
          disabled={reason !== null}
          onClick={() => onRedeem(item)}
          className="px-4 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold shadow-xs hover:bg-[#85145a] disabled:bg-slate-200 disabled:text-slate-500 disabled:cursor-not-allowed transition-colors"
        >
          {reason ?? 'Đổi ngay'}
        </button>
      </div>
    </div>
  );
};

/** Cửa hàng đổi thưởng: đổi xu lấy ngày VIP, vé đọc truyện, khung avatar; xem khung và lịch sử ví (F17.02, F17.07, F17.08). */
export const RewardShopPage: React.FC<{ showToast: (message: string) => void }> = ({ showToast }) => {
  useTourPage('shop');
  const { wallet, loading: walletLoading } = useRewards();
  const [tab, setTab] = useState<ShopTab>('items');
  const items = useApiResource(signal => listShopItems(signal), []);
  const [pending, setPending] = useState<ShopItem | null>(null);
  const [busy, setBusy] = useState(false);
  // Giữ cùng một mã yêu cầu cho tới khi có kết quả rõ ràng, để bấm lại sau lỗi mạng không đổi hai lần.
  const requestIds = useRef(new Map<number, string>());

  const confirmRedeem = async () => {
    if (!pending || busy) return;
    const item = pending;
    const requestId = requestIds.current.get(item.id) ?? newRequestId();
    requestIds.current.set(item.id, requestId);
    setBusy(true);
    try {
      const result = await redeemItem(item.id, requestId);
      requestIds.current.delete(item.id);
      showToast(`Đã đổi "${result.item_name}" với ${result.price_coins.toLocaleString('vi-VN')} xu.`);
      notifyRewardsChanged();
      items.reload();
    } catch (err) {
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) requestIds.current.delete(item.id);
      showToast(errorMessage(err));
      items.reload();
    } finally {
      setBusy(false);
      setPending(null);
    }
  };

  return (
    <div className="w-full max-w-[1100px] mx-auto px-4 md:px-8 py-6 flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans'] flex flex-wrap items-center gap-x-3 dark:text-slate-100">
          <span>Cửa Hàng Đổi Thưởng</span>
          <span className="text-[#a43073] font-['Noto_Serif_SC'] italic text-2xl font-light dark:text-pink-400">奖励</span>
        </h1>
        <p className="text-sm text-slate-600 max-w-2xl dark:text-slate-300">
          Xu Sakura kiếm được từ huy hiệu, nhiệm vụ ngày và thưởng mùa giải. Dùng xu để đổi ngày VIP, vé mở khóa truyện VIP hoặc khung avatar. Yinghua không bán xu hay VIP bằng tiền thật.
        </p>
      </div>

      <div data-tour="shop-wallet">
      <WalletSummary wallet={wallet} loading={walletLoading} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div data-tour="shop-tabs" role="tablist" aria-label="Mục cửa hàng" className="bg-white p-1.5 rounded-full shadow-xs border border-pink-100 flex items-center gap-1 overflow-x-auto dark:bg-slate-800 dark:border-pink-900/40">
          {TABS.map(({ id, label, icon }) => (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`px-4 py-2 rounded-full text-xs font-bold flex items-center gap-1.5 whitespace-nowrap transition-all ${
                tab === id ? 'bg-[#f472b6] text-white shadow-xs dark:bg-[#a43073]' : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">{icon}</span>
              {label}
            </button>
          ))}
        </div>
        <Link to={BLADE_GAME_PATH} className="text-xs font-bold text-[#a43073] hover:underline flex items-center gap-1 dark:text-pink-400">
          <span className="material-symbols-outlined text-[16px]">swords</span>
          Chơi Phi Kiếm Trảm Tự để kiếm thêm XP
        </Link>
      </div>

      {tab === 'items' && (
        <>
          {items.loading && (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500 dark:text-slate-400" role="status">
              <span className="w-5 h-5 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
              Đang tải cửa hàng...
            </div>
          )}
          {items.error && !items.data && (
            <div role="alert" className="rounded-2xl bg-rose-50 border border-rose-200 p-5 text-center text-sm text-rose-700 dark:bg-rose-900/30 dark:border-rose-900/40 dark:text-rose-400">
              <p>{items.error}</p>
              <button type="button" onClick={items.reload} className="mt-3 px-4 py-2 rounded-full bg-white text-rose-700 text-xs font-bold dark:bg-slate-800 dark:text-rose-400">
                Thử lại
              </button>
            </div>
          )}
          {items.data && items.data.length === 0 && <p className="py-12 text-center text-sm text-slate-500 dark:text-slate-400">Cửa hàng chưa có món nào đang bán. Quay lại sau nhé!</p>}
          {items.data && items.data.length > 0 && (
            <div data-tour="shop-items" className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {items.data.map(item => (
                <ShopItemCard key={item.id} item={item} onRedeem={setPending} />
              ))}
            </div>
          )}
        </>
      )}
      {tab === 'frames' && <RewardFramesTab showToast={showToast} />}
      {tab === 'ledger' && <RewardLedgerTab />}

      {pending && (
        <ConfirmDialog
          title="Xác nhận đổi thưởng"
          message={`Đổi "${pending.name}" với ${pending.price_coins.toLocaleString('vi-VN')} xu? Xu đã dùng sẽ không được hoàn lại.`}
          confirmLabel="Đổi ngay"
          busy={busy}
          onConfirm={() => void confirmRedeem()}
          onCancel={() => setPending(null)}
        />
      )}
    </div>
  );
};
