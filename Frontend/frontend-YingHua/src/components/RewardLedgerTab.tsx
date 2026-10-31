import React, { useState } from 'react';
import { Currency, LedgerEntry, listLedger } from '../api/rewards';
import { useApiResource } from '../utils/useApiResource';

const PAGE_SIZE = 15;

const FILTERS: { id: Currency | 'all'; label: string }[] = [
  { id: 'all', label: 'Tất cả' },
  { id: 'coin', label: 'Xu' },
  { id: 'ticket', label: 'Vé' },
  { id: 'vip_days', label: 'Ngày VIP' }
];

const UNIT: Record<Currency, string> = { coin: 'xu', ticket: 'vé', vip_days: 'ngày VIP' };

export const formatLedgerAmount = (entry: LedgerEntry): string => `${entry.amount > 0 ? '+' : ''}${entry.amount.toLocaleString('vi-VN')} ${UNIT[entry.currency]}`;

const formatDateTime = (iso: string): string => new Date(iso).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' });

/** Lịch sử nhận và tiêu của ví (xu, vé, ngày VIP), mới nhất trước (F17.02). */
export const RewardLedgerTab: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const [currency, setCurrency] = useState<Currency | 'all'>('all');
  const [page, setPage] = useState(1);
  const ledger = useApiResource(signal => listLedger({ currency: currency === 'all' ? undefined : currency, page, size: PAGE_SIZE }, signal), [currency, page]);
  const data = ledger.data;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className={compact ? 'flex flex-col gap-3' : 'rounded-3xl bg-white shadow-soft border border-pink-100 p-5 flex flex-col gap-3 dark:bg-slate-800 dark:border-pink-900/40'}>
      <div className="flex flex-wrap items-center gap-1.5">
        {FILTERS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            aria-pressed={currency === id}
            onClick={() => {
              setCurrency(id);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-full text-[11px] font-semibold ${currency === id ? 'bg-[#a43073] text-white' : 'bg-slate-100 text-slate-600 dark:bg-[#1e293b] dark:text-slate-300'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {ledger.loading && <p className="py-6 text-center text-xs text-slate-400">Đang tải lịch sử...</p>}
      {ledger.error && !data && (
        <p role="alert" className="py-4 text-center text-xs text-rose-600 dark:text-rose-400">
          {ledger.error}{' '}
          <button type="button" onClick={ledger.reload} className="font-bold underline">
            Thử lại
          </button>
        </p>
      )}
      {data && data.items.length === 0 && <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">Chưa có giao dịch nào.</p>}
      {data && data.items.length > 0 && (
        <ul className="divide-y divide-slate-100 dark:divide-slate-700">
          {data.items.map(entry => (
            <li key={entry.id} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <div className="text-xs font-bold text-slate-800 dark:text-slate-100">{entry.reason_label}</div>
                <div className="text-[10px] text-slate-400 truncate">
                  {formatDateTime(entry.created_at)}
                  {entry.note ? ` · ${entry.note}` : ''}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className={`text-sm font-extrabold ${entry.amount >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>{formatLedgerAmount(entry)}</div>
                {entry.balance_after !== null && <div className="text-[10px] text-slate-400">Còn {entry.balance_after.toLocaleString('vi-VN')}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span>
            Trang {page}/{totalPages}
          </span>
          <div className="flex gap-1">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-3 py-1 rounded-full bg-slate-100 disabled:opacity-40 dark:bg-[#1e293b]">
              Trước
            </button>
            <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="px-3 py-1 rounded-full bg-slate-100 disabled:opacity-40 dark:bg-[#1e293b]">
              Sau
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
