import React, { useCallback, useEffect, useState } from 'react';
import { isAbortedError } from '../api/client';
import { AdminRewardItem, listAdminRewardItems, updateRewardItem } from '../api/rewards';
import { LoadState, errorMessage } from './AdminDataParts';
import { AdminRewardItemForm, KIND_LABEL } from './AdminRewardItemForm';

interface AdminRewardsPanelProps {
  notify: (message: string) => void;
}

const describeTarget = (item: AdminRewardItem): string => {
  if (item.kind === 'vip_days') return `${item.vip_days ?? '?'} ngày VIP`;
  if (item.kind === 'vip_ticket') return `${item.ticket_count ?? '?'} vé`;
  return item.frame?.name ?? 'Khung avatar';
};

/** Danh mục đổi thưởng đầy đủ: thêm, sửa giá, bật/tắt bán (F17.09). Cờ VIP của truyện đặt ở "Kho truyện Manhua". */
export const AdminRewardsPanel: React.FC<AdminRewardsPanelProps> = ({ notify }) => {
  const [items, setItems] = useState<AdminRewardItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [busyId, setBusyId] = useState<number | null>(null);
  // undefined = đóng; null = thêm mới; món = sửa món đó.
  const [editing, setEditing] = useState<AdminRewardItem | null | undefined>(undefined);
  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    listAdminRewardItems(controller.signal)
      .then(result => {
        setItems(result);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err, 'Không tải được danh mục đổi thưởng'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [tick]);

  const toggleActive = async (item: AdminRewardItem) => {
    setBusyId(item.id);
    try {
      await updateRewardItem(item.id, { is_active: !item.is_active });
      notify(item.is_active ? 'Đã ngừng bán món.' : 'Đã mở bán món.');
      reload();
    } catch (err) {
      notify(errorMessage(err, 'Thao tác không thành công, vui lòng thử lại'));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-[#0f172a] text-slate-800 dark:text-slate-200 shadow-sm dark:shadow-none transition-colors duration-300">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-700 px-4 py-3">
        <h2 className="text-sm font-extrabold text-slate-800 dark:text-slate-100">Danh mục đổi thưởng</h2>
        <button onClick={() => setEditing(null)} className="rounded-full bg-pink-500 dark:bg-[#a43073] px-3 py-1.5 text-[10px] font-bold text-white">+ Thêm món</button>
      </div>
      <div className="p-4">
        <LoadState loading={loading && !items} error={error} empty={!!items && items.length === 0} emptyText='Chưa có món nào. Bấm "+ Thêm món" để tạo.' onRetry={reload} />
        {items && items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[10px] uppercase text-slate-400 dark:text-slate-500">
                <tr><th className="py-2 pr-3">Món</th><th className="pr-3">Loại</th><th className="pr-3">Giá</th><th className="pr-3">Giới hạn</th><th className="pr-3">Trạng thái</th><th /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {items.map(item => (
                  <tr key={item.id}>
                    <td className="py-2.5 pr-3">
                      <div className="font-bold text-slate-800 dark:text-slate-100">{item.name}</div>
                      <div className="text-[10px] text-slate-400 dark:text-slate-500">{item.code} · {describeTarget(item)}</div>
                    </td>
                    <td className="pr-3">{KIND_LABEL[item.kind]}</td>
                    <td className="pr-3 font-bold text-amber-700 dark:text-amber-400">{item.price_coins.toLocaleString('vi-VN')} xu</td>
                    <td className="pr-3">{item.per_user_limit ?? 'Không'}</td>
                    <td className="pr-3">
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${item.is_active ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'}`}>
                        {item.is_active ? 'Đang bán' : 'Ngừng bán'}
                      </span>
                    </td>
                    <td className="whitespace-nowrap text-right text-[10px] font-bold">
                      <button onClick={() => setEditing(item)} className="mr-3 text-blue-700 dark:text-blue-300">Sửa</button>
                      <button disabled={busyId === item.id} onClick={() => void toggleActive(item)} className="text-slate-600 dark:text-slate-300 disabled:opacity-40">
                        {item.is_active ? 'Ngừng bán' : 'Mở bán'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {editing !== undefined && (
        <AdminRewardItemForm key={editing?.id ?? 'new'} item={editing} onClose={() => setEditing(undefined)} onSaved={reload} notify={notify} />
      )}
    </section>
  );
};
