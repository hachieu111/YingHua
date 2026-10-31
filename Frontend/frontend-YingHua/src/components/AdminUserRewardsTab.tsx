import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';
import {
  AdminUserRewards,
  MAX_COINS_PER_GRANT,
  MAX_TICKETS_PER_GRANT,
  MAX_VIP_DAYS_PER_GRANT,
  NOTE_MAX_LENGTH,
  adjustWallet,
  getUserRewards,
  grantVip,
  newRequestId
} from '../api/rewards';
import { Pager, errorMessage, formatDateTime, LoadState } from './AdminDataParts';
import { formatLedgerAmount } from './RewardLedgerTab';

interface TabProps {
  userId: number;
  notify: (message: string) => void;
}

const PAGE_SIZE = 10;
const FIELD = 'rounded-xl border border-slate-200 px-3 py-2 text-sm font-normal dark:border-slate-700';
const LABEL = 'text-xs font-semibold text-slate-600 flex flex-col gap-1 dark:text-slate-300';
/** Mã yêu cầu gắn với một ý định gửi: giữ khi lỗi mạng, bỏ sau thành công hoặc lỗi 4xx; đổi nội dung thì sinh mã mới. */
interface Intent {
  signature: string;
  id: string;
}

const BUTTON = 'px-4 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold disabled:opacity-50';

/** Ví, VIP, khung và lịch sử phần thưởng của một người dùng; cấp/thu xu, vé, VIP kèm lý do (F17.10). Quản trị được tự cấp cho chính mình. */
export const AdminUserRewardsTab: React.FC<TabProps> = ({ userId, notify }) => {
  const [data, setData] = useState<AdminUserRewards | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [vipDays, setVipDays] = useState('7');
  const [vipReason, setVipReason] = useState('');
  const [currency, setCurrency] = useState<'coin' | 'ticket'>('coin');
  const [amount, setAmount] = useState('');
  const [walletReason, setWalletReason] = useState('');
  const vipIntent = useRef<Intent | null>(null);
  const walletIntent = useRef<Intent | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getUserRewards(userId, page, PAGE_SIZE)
      .then(setData)
      .catch(err => setError(errorMessage(err, 'Không tải được phần thưởng của người dùng')))
      .finally(() => setLoading(false));
  }, [userId, page]);

  useEffect(load, [load]);

  const requestIdFor = (intent: React.MutableRefObject<Intent | null>, signature: string): string => {
    if (intent.current?.signature !== signature) intent.current = { signature, id: newRequestId() };
    return intent.current.id;
  };

  const run = async (
    intent: React.MutableRefObject<Intent | null>,
    action: () => Promise<unknown>,
    done: string,
    after?: () => void
  ) => {
    if (busy) return;
    setBusy(true);
    try {
      await action();
      intent.current = null;
      notify(done);
      after?.();
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) intent.current = null;
      notify(errorMessage(err, 'Thao tác không thành công, vui lòng thử lại'));
    } finally {
      setBusy(false);
    }
  };

  if (!data) return <LoadState loading={loading} error={error} onRetry={load} />;

  const days = Number(vipDays);
  const daysValid = Number.isInteger(days) && days >= 1 && days <= MAX_VIP_DAYS_PER_GRANT;
  const amountNumber = Number(amount);
  const limit = currency === 'coin' ? MAX_COINS_PER_GRANT : MAX_TICKETS_PER_GRANT;
  const amountValid = Number.isInteger(amountNumber) && amountNumber !== 0 && Math.abs(amountNumber) <= limit;

  const submitVip = (revoke: boolean) => {
    if (!vipReason.trim()) return notify('Vui lòng nhập lý do.');
    if (revoke && !window.confirm('Thu hồi toàn bộ VIP của người dùng này?')) return;
    const reason = vipReason.trim();
    const requestId = requestIdFor(vipIntent, revoke ? `revoke|${reason}` : `${days}|${reason}`);
    void run(
      vipIntent,
      () => grantVip(userId, revoke ? { revoke: true, reason, request_id: requestId } : { days, reason, request_id: requestId }),
      revoke ? 'Đã thu hồi VIP.' : `Đã cấp ${days} ngày VIP.`,
      () => setVipReason('')
    );
  };

  const submitWallet = () => {
    if (!walletReason.trim()) return notify('Vui lòng nhập lý do.');
    const reason = walletReason.trim();
    const requestId = requestIdFor(walletIntent, `${currency}|${amountNumber}|${reason}`);
    void run(
      walletIntent,
      () => adjustWallet(userId, { currency, amount: amountNumber, reason, request_id: requestId }),
      `Đã điều chỉnh ${amountNumber > 0 ? '+' : ''}${amountNumber} ${currency === 'coin' ? 'xu' : 'vé'}.`,
      () => {
        setAmount('');
        setWalletReason('');
      }
    );
  };

  const { wallet } = data;
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 min-[420px]:grid-cols-3 gap-3 text-center">
        <div className="rounded-xl border border-slate-100 p-3 dark:border-slate-700"><div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">Xu</div><div className="mt-1 text-lg font-bold text-slate-800 dark:text-slate-100">{wallet.coin_balance.toLocaleString('vi-VN')}</div></div>
        <div className="rounded-xl border border-slate-100 p-3 dark:border-slate-700"><div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">Vé VIP</div><div className="mt-1 text-lg font-bold text-slate-800 dark:text-slate-100">{wallet.ticket_balance}</div></div>
        <div className="rounded-xl border border-slate-100 p-3 dark:border-slate-700">
          <div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">VIP</div>
          <div className="mt-1 text-sm font-bold text-slate-800 dark:text-slate-100">{wallet.vip.is_active ? `Còn ${wallet.vip.days_left} ngày` : 'Chưa kích hoạt'}</div>
          {wallet.vip.is_active && <div className="text-[10px] text-slate-500 dark:text-slate-400">Đến {formatDateTime(wallet.vip.vip_until)}</div>}
        </div>
      </div>

      <section className="rounded-2xl border border-slate-100 p-4 flex flex-col gap-3 dark:border-slate-700">
        <h3 className="text-sm font-extrabold text-slate-800 dark:text-slate-100">Cấp hoặc thu hồi VIP</h3>
        <div className="grid sm:grid-cols-[8rem_1fr] gap-3">
          <label className={LABEL}>Số ngày (1–{MAX_VIP_DAYS_PER_GRANT})
            <input type="number" min={1} max={MAX_VIP_DAYS_PER_GRANT} value={vipDays} onChange={e => setVipDays(e.target.value)} className={FIELD} />
          </label>
          <label className={LABEL}>Lý do (bắt buộc, ghi nhật ký)
            <input value={vipReason} maxLength={NOTE_MAX_LENGTH} onChange={e => setVipReason(e.target.value)} className={FIELD} />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <button disabled={busy || !daysValid || !vipReason.trim()} onClick={() => submitVip(false)} className={BUTTON}>Cấp ngày VIP</button>
          <button disabled={busy || !vipReason.trim() || !wallet.vip.is_active} onClick={() => submitVip(true)} className="px-4 py-2 rounded-full bg-rose-50 text-rose-700 text-xs font-bold disabled:opacity-50 dark:bg-rose-900/30 dark:text-rose-400">Thu hồi VIP</button>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-100 p-4 flex flex-col gap-3 dark:border-slate-700">
        <h3 className="text-sm font-extrabold text-slate-800 dark:text-slate-100">Cấp hoặc thu xu / vé</h3>
        <div className="grid sm:grid-cols-[8rem_10rem_1fr] gap-3">
          <label className={LABEL}>Loại
            <select value={currency} onChange={e => setCurrency(e.target.value as 'coin' | 'ticket')} className={FIELD}>
              <option value="coin">Xu</option>
              <option value="ticket">Vé đọc truyện</option>
            </select>
          </label>
          <label className={LABEL}>Số lượng (âm = thu, tối đa ±{limit.toLocaleString('vi-VN')})
            <input type="number" value={amount} onChange={e => setAmount(e.target.value)} className={FIELD} />
          </label>
          <label className={LABEL}>Lý do (bắt buộc, ghi nhật ký)
            <input value={walletReason} maxLength={NOTE_MAX_LENGTH} onChange={e => setWalletReason(e.target.value)} className={FIELD} />
          </label>
        </div>
        <div><button disabled={busy || !amountValid || !walletReason.trim()} onClick={submitWallet} className={BUTTON}>Áp dụng</button></div>
      </section>

      <section className="rounded-2xl border border-slate-100 p-4 dark:border-slate-700">
        <h3 className="text-sm font-extrabold text-slate-800 mb-2 dark:text-slate-100">Khung và truyện đã mở khóa</h3>
        <div className="text-xs text-slate-600 flex flex-col gap-1 dark:text-slate-300">
          <div>Khung sở hữu: {data.frames.length ? data.frames.map(f => f.name + (f.expires_at ? ` (đến ${formatDateTime(f.expires_at)})` : '')).join(', ') : 'chưa có'}</div>
          <div>Truyện VIP đã mở khóa: {data.unlocks.length ? data.unlocks.map(u => u.series_title ?? `#${u.series_id}`).join(', ') : 'chưa có'}</div>
          <div>Khung đang đeo: {wallet.equipped_frame?.name ?? 'không'}</div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-100 p-4 dark:border-slate-700">
        <h3 className="text-sm font-extrabold text-slate-800 mb-2 dark:text-slate-100">Lịch sử ví</h3>
        <LoadState loading={false} error={error} empty={data.ledger.items.length === 0} emptyText="Chưa có giao dịch nào." onRetry={load} />
        <ul className="divide-y divide-slate-100 dark:divide-slate-700">
          {data.ledger.items.map(entry => (
            <li key={entry.id} className="py-2 flex items-center justify-between gap-3 text-xs">
              <div className="min-w-0">
                <div className="font-bold text-slate-800 dark:text-slate-100">{entry.reason_label}{entry.actor_id !== null ? ` · bởi quản trị #${entry.actor_id}` : ''}</div>
                <div className="text-[10px] text-slate-400 truncate">{formatDateTime(entry.created_at)}{entry.note ? ` · ${entry.note}` : ''}</div>
              </div>
              <div className={`font-extrabold shrink-0 ${entry.amount >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>{formatLedgerAmount(entry)}</div>
            </li>
          ))}
        </ul>
        {data.ledger.total > PAGE_SIZE && <Pager page={page} size={PAGE_SIZE} total={data.ledger.total} onPage={setPage} />}
      </section>
    </div>
  );
};
