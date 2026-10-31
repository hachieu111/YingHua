import React, { useEffect, useState } from 'react';
import {
  AdminFrame,
  AdminRewardItem,
  ItemKind,
  RewardItemInput,
  createRewardItem,
  listAdminFrames,
  updateRewardItem
} from '../api/rewards';
import { errorMessage } from './AdminDataParts';

const FIELD = 'rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-100 px-3 py-2 text-sm font-normal disabled:bg-slate-50 disabled:text-slate-400 dark:disabled:bg-slate-800 dark:disabled:text-slate-500';
const LABEL = 'text-xs font-semibold text-slate-600 dark:text-slate-300 flex flex-col gap-1';

export const KIND_LABEL: Record<ItemKind, string> = {
  vip_days: 'Ngày VIP',
  vip_ticket: 'Vé đọc truyện VIP',
  avatar_frame: 'Khung avatar'
};

interface FormState {
  code: string;
  kind: ItemKind;
  name: string;
  description: string;
  price: string;
  vipDays: string;
  ticketCount: string;
  frameCode: string;
  limit: string;
  sortOrder: string;
  isActive: boolean;
}

const toState = (item: AdminRewardItem | null): FormState => ({
  code: item?.code ?? '',
  kind: item?.kind ?? 'vip_days',
  name: item?.name ?? '',
  description: item?.description ?? '',
  price: item ? String(item.price_coins) : '',
  vipDays: item?.vip_days != null ? String(item.vip_days) : '',
  ticketCount: item?.ticket_count != null ? String(item.ticket_count) : '',
  frameCode: item?.frame?.code ?? '',
  limit: item?.per_user_limit != null ? String(item.per_user_limit) : '',
  sortOrder: item ? String(item.sort_order) : '0',
  isActive: item?.is_active ?? true
});

const intOrNull = (value: string): number | null => (value.trim() === '' ? null : Number(value));

const toInput = (form: FormState): RewardItemInput => ({
  name: form.name.trim(),
  description: form.description.trim() || null,
  price_coins: Number(form.price),
  vip_days: form.kind === 'vip_days' ? intOrNull(form.vipDays) : null,
  ticket_count: form.kind === 'vip_ticket' ? intOrNull(form.ticketCount) : null,
  frame_code: form.kind === 'avatar_frame' ? form.frameCode || null : null,
  per_user_limit: intOrNull(form.limit),
  is_active: form.isActive,
  sort_order: Number(form.sortOrder) || 0
});

const NULLABLE_KEYS: (keyof RewardItemInput)[] = ['description', 'per_user_limit'];
const TARGET_KEYS: (keyof RewardItemInput)[] = ['vip_days', 'ticket_count', 'frame_code'];

/**
 * Chỉ gửi trường đã đổi. Chỉ `description` và `per_user_limit` được gửi null (để xóa);
 * các trường khác không bao giờ null, và đối tượng món bị bỏ qua khi món đã có lượt đổi.
 */
const diffInput = (before: RewardItemInput, after: RewardItemInput, locked: boolean): Partial<RewardItemInput> => {
  const changes: Partial<RewardItemInput> = {};
  (Object.keys(after) as (keyof RewardItemInput)[]).forEach(key => {
    if (before[key] === after[key]) return;
    if (locked && TARGET_KEYS.includes(key)) return;
    if (after[key] === null && !NULLABLE_KEYS.includes(key)) return;
    Object.assign(changes, { [key]: after[key] });
  });
  return changes;
};

interface AdminRewardItemFormProps {
  /** null = thêm món mới. */
  item: AdminRewardItem | null;
  onClose: () => void;
  onSaved: () => void;
  notify: (message: string) => void;
}

/** Biểu mẫu thêm/sửa món đổi thưởng (F17.09). Món đã có lượt đổi thì khóa loại và đối tượng. */
export const AdminRewardItemForm: React.FC<AdminRewardItemFormProps> = ({ item, onClose, onSaved, notify }) => {
  const [form, setForm] = useState<FormState>(() => toState(item));
  const [frames, setFrames] = useState<AdminFrame[]>([]);
  const [framesFailed, setFramesFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const locked = item?.has_redemptions ?? false;

  useEffect(() => {
    const controller = new AbortController();
    listAdminFrames(controller.signal)
      .then(list => setFrames(list.filter(frame => frame.acquire_kind === 'shop')))
      .catch(() => {
        if (!controller.signal.aborted) setFramesFailed(true);
      });
    return () => controller.abort();
  }, []);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm(current => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = toInput(form);
      if (item) {
        await updateRewardItem(item.id, diffInput(toInput(toState(item)), body, locked));
        notify('Đã cập nhật món đổi thưởng.');
      } else {
        await createRewardItem({ ...body, code: form.code.trim(), kind: form.kind });
        notify('Đã thêm món đổi thưởng.');
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Không lưu được món đổi thưởng'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] bg-slate-900/50 dark:bg-black/70 flex items-center justify-center p-4" onClick={busy ? undefined : onClose}>
      <form
        onSubmit={event => void submit(event)}
        onClick={event => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={item ? 'Sửa món đổi thưởng' : 'Thêm món đổi thưởng'}
        className="bg-white dark:bg-[#0f172a] dark:border dark:border-slate-700 rounded-2xl shadow-2xl dark:shadow-none w-full max-w-xl max-h-[90vh] overflow-y-auto p-5 flex flex-col gap-4"
      >
        <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100">{item ? 'Sửa món đổi thưởng' : 'Thêm món đổi thưởng'}</h3>
        {locked && <p className="rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900/50 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">Món này đã có lượt đổi nên không đổi được loại và đối tượng (số ngày, vé, khung).</p>}

        <div className="grid sm:grid-cols-2 gap-3">
          <label className={LABEL}>Mã món (a-z, 0-9, _)
            <input required minLength={2} maxLength={32} pattern="[a-z0-9_]{2,32}" disabled={!!item} value={form.code} onChange={e => set('code', e.target.value)} className={FIELD} />
          </label>
          <label className={LABEL}>Loại
            <select disabled={!!item} value={form.kind} onChange={e => set('kind', e.target.value as ItemKind)} className={FIELD}>
              {(Object.keys(KIND_LABEL) as ItemKind[]).map(kind => <option key={kind} value={kind}>{KIND_LABEL[kind]}</option>)}
            </select>
          </label>
          <label className={`${LABEL} sm:col-span-2`}>Tên hiển thị
            <input required maxLength={100} value={form.name} onChange={e => set('name', e.target.value)} className={FIELD} />
          </label>
          <label className={`${LABEL} sm:col-span-2`}>Mô tả
            <input maxLength={255} value={form.description} onChange={e => set('description', e.target.value)} className={FIELD} />
          </label>
          <label className={LABEL}>Giá (xu)
            <input required type="number" min={1} max={100000} value={form.price} onChange={e => set('price', e.target.value)} className={FIELD} />
          </label>
          {form.kind === 'vip_days' && (
            <label className={LABEL}>Số ngày VIP (1–365)
              <input required type="number" min={1} max={365} disabled={locked} value={form.vipDays} onChange={e => set('vipDays', e.target.value)} className={FIELD} />
            </label>
          )}
          {form.kind === 'vip_ticket' && (
            <label className={LABEL}>Số vé (1–10)
              <input required type="number" min={1} max={10} disabled={locked} value={form.ticketCount} onChange={e => set('ticketCount', e.target.value)} className={FIELD} />
            </label>
          )}
          {form.kind === 'avatar_frame' && (
            <label className={LABEL}>Khung avatar
              <select required disabled={locked} value={form.frameCode} onChange={e => set('frameCode', e.target.value)} className={FIELD}>
                <option value="">Chọn khung</option>
                {frames.map(frame => <option key={frame.code} value={frame.code}>{frame.name}</option>)}
              </select>
              {framesFailed && <span role="alert" className="text-[11px] font-normal text-rose-600 dark:text-rose-400">Không tải được danh sách khung. Đóng và mở lại biểu mẫu để thử lại.</span>}
              {!framesFailed && frames.length === 0 && <span className="text-[11px] font-normal text-slate-500 dark:text-slate-400">Chưa có khung nào được bán trong cửa hàng.</span>}
            </label>
          )}
          <label className={LABEL}>Giới hạn lượt đổi mỗi người (để trống = không giới hạn)
            <input type="number" min={1} max={32767} value={form.limit} onChange={e => set('limit', e.target.value)} className={FIELD} />
          </label>
          <label className={LABEL}>Thứ tự hiển thị
            <input type="number" min={-32768} max={32767} value={form.sortOrder} onChange={e => set('sortOrder', e.target.value)} className={FIELD} />
          </label>
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-600 dark:text-slate-300 sm:col-span-2">
            <input type="checkbox" checked={form.isActive} onChange={e => set('isActive', e.target.checked)} />
            Đang bán trong cửa hàng
          </label>
        </div>

        {error && <p role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-900/50 px-3 py-2 text-xs font-semibold text-rose-700 dark:text-rose-400">{error}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" disabled={busy} onClick={onClose} className="px-4 py-2 rounded-full text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50">Hủy</button>
          <button type="submit" disabled={busy} className="px-5 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold disabled:opacity-60">{busy ? 'Đang lưu...' : 'Lưu'}</button>
        </div>
      </form>
    </div>
  );
};
