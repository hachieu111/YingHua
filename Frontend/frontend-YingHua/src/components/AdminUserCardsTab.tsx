import React, { useCallback, useEffect, useState } from 'react';
import {
  AdminCard,
  getUserCardHistory,
  getUserReviewSummary,
  listUserCards,
  resetUserCard,
  resumeUserCard,
  suspendUserCard
} from '../api/adminUserData';
import { ApiReviewLog, CARD_STATE_LABEL, CARD_TYPE_LABEL, RATING_LABEL, ReviewSummary } from '../api/review';
import { Paged } from '../api/library';
import { ConfirmDialog } from './ConfirmDialog';
import { Chip, errorMessage, formatDateTime, LoadState, Pager, Stat } from './AdminDataParts';

interface TabProps {
  userId: number;
  notify: (message: string) => void;
}

const PAGE_SIZE = 10;
type StateFilter = 'learning' | 'review' | 'relearning' | undefined;
type Flag = 'all' | 'yes' | 'no';

const toBool = (flag: Flag): boolean | undefined => (flag === 'all' ? undefined : flag === 'yes');

const History: React.FC<{ userId: number; cardId: number }> = ({ userId, cardId }) => {
  const [items, setItems] = useState<ApiReviewLog[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getUserCardHistory(userId, cardId, 1, 10)
      .then(result => setItems(result.items))
      .catch(err => setError(errorMessage(err, 'Không tải được lịch sử')));
  }, [userId, cardId]);

  if (error) return <div className="text-xs text-rose-600 dark:text-rose-400">{error}</div>;
  if (!items) return <div className="text-xs text-slate-400">Đang tải lịch sử...</div>;
  if (items.length === 0) return <div className="text-xs text-slate-500 dark:text-slate-400">Thẻ chưa có lượt ôn nào.</div>;
  return (
    <ul className="text-xs text-slate-600 flex flex-col gap-1 dark:text-slate-300">
      {items.map(log => (
        <li key={log.id}>
          {formatDateTime(log.reviewed_at)} · <b>{RATING_LABEL[log.rating] ?? log.rating}</b> · hạn kế tiếp {formatDateTime(log.due_after)}
        </li>
      ))}
    </ul>
  );
};

/** Thẻ ôn của người dùng: lọc, lịch sử, tạm ngưng/tiếp tục, đặt lại (F13.07). */
export const AdminUserCardsTab: React.FC<TabProps> = ({ userId, notify }) => {
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [data, setData] = useState<Paged<AdminCard> | null>(null);
  const [state, setState] = useState<StateFilter>();
  const [suspended, setSuspended] = useState<Flag>('all');
  const [due, setDue] = useState<Flag>('all');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historyId, setHistoryId] = useState<number | null>(null);
  const [resetTarget, setResetTarget] = useState<AdminCard | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => setPage(1), [state, suspended, due]);

  useEffect(() => {
    getUserReviewSummary(userId).then(setSummary).catch(() => setSummary(null));
  }, [userId, version]);

  const load = useCallback(() => setVersion(v => v + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    listUserCards(userId, { state, suspended: toBool(suspended), due: toBool(due), page, size: PAGE_SIZE }, controller.signal)
      .then(setData)
      .catch(err => { if (!controller.signal.aborted) setError(errorMessage(err, 'Không tải được danh sách thẻ')); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [userId, state, suspended, due, page, version]);

  const act = async (card: AdminCard, action: () => Promise<unknown>, success: string) => {
    setBusyId(card.id);
    try {
      await action();
      notify(success);
      load();
    } catch (err) {
      notify(errorMessage(err, 'Thao tác không thành công'));
    } finally {
      setBusyId(null);
      setResetTarget(null);
    }
  };

  const items = data?.items ?? [];
  return (
    <div className="flex flex-col gap-3">
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Tổng số thẻ" value={summary.total_cards} />
          <Stat label="Đến hạn" value={summary.due_now} />
          <Stat label="Ôn hôm nay" value={summary.reviewed_today} />
          <Stat label="Hạn kế tiếp" value={<span className="text-xs">{formatDateTime(summary.next_due_at)}</span>} />
        </div>
      )}
      <div className="flex gap-2 flex-wrap items-center">
        <Chip active={!state} onClick={() => setState(undefined)}>Mọi trạng thái</Chip>
        {(['learning', 'review', 'relearning'] as const).map(s => <Chip key={s} active={state === s} onClick={() => setState(s)}>{CARD_STATE_LABEL[s]}</Chip>)}
        <select aria-label="Lọc tạm ngưng" value={suspended} onChange={e => setSuspended(e.target.value as Flag)} className="rounded-full border border-slate-200 px-3 py-1 text-[11px] dark:border-slate-700">
          <option value="all">Tạm ngưng: tất cả</option><option value="yes">Đang tạm ngưng</option><option value="no">Không tạm ngưng</option>
        </select>
        <select aria-label="Lọc đến hạn" value={due} onChange={e => setDue(e.target.value as Flag)} className="rounded-full border border-slate-200 px-3 py-1 text-[11px] dark:border-slate-700">
          <option value="all">Hạn: tất cả</option><option value="yes">Đã đến hạn</option><option value="no">Chưa đến hạn</option>
        </select>
      </div>
      <LoadState loading={loading && !data} error={error} empty={!loading && !error && items.length === 0} emptyText="Không có thẻ nào phù hợp" onRetry={load} />
      <div className="flex flex-col gap-2">
        {items.map(card => (
          <div key={card.id} className="rounded-xl border border-slate-100 p-3 flex flex-col gap-2 dark:border-slate-700">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-sm font-bold text-slate-800 dark:text-slate-100">{card.term ?? '(mục từ đã xóa)'} <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{card.pinyin}</span></div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  {CARD_TYPE_LABEL[card.card_type]} · {CARD_STATE_LABEL[card.state] ?? card.state}{card.is_suspended ? ' · tạm ngưng' : ''} · hạn {formatDateTime(card.due_at)} · ôn {card.reps}, quên {card.lapses}
                </div>
              </div>
              <div className="flex gap-2 text-[11px] font-bold">
                <button onClick={() => setHistoryId(historyId === card.id ? null : card.id)} className="px-3 py-1 rounded-full bg-slate-100 text-slate-600 dark:bg-[#1e293b] dark:text-slate-300">Lịch sử</button>
                <button disabled={busyId === card.id} onClick={() => act(card, () => (card.is_suspended ? resumeUserCard(userId, card.id) : suspendUserCard(userId, card.id)), card.is_suspended ? 'Đã tiếp tục thẻ.' : 'Đã tạm ngưng thẻ.')}
                  className="px-3 py-1 rounded-full bg-blue-50 text-blue-700 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-400">{card.is_suspended ? 'Tiếp tục' : 'Tạm ngưng'}</button>
                <button disabled={busyId === card.id} onClick={() => setResetTarget(card)} className="px-3 py-1 rounded-full bg-rose-50 text-rose-700 disabled:opacity-50 dark:bg-rose-900/30 dark:text-rose-400">Đặt lại</button>
              </div>
            </div>
            {historyId === card.id && <History userId={userId} cardId={card.id} />}
          </div>
        ))}
      </div>
      {data && data.total > 0 && <Pager page={page} size={PAGE_SIZE} total={data.total} onPage={setPage} />}
      {resetTarget && (
        <ConfirmDialog
          title="Đặt lại thẻ này?"
          message={`Thẻ “${resetTarget.term ?? ''}” sẽ về trạng thái học mới; tiến độ ghi nhớ của người dùng bị mất.`}
          confirmLabel="Đặt lại" busy={busyId === resetTarget.id}
          onConfirm={() => void act(resetTarget, () => resetUserCard(userId, resetTarget.id), 'Đã đặt lại thẻ.')}
          onCancel={() => setResetTarget(null)}
        />
      )}
    </div>
  );
};
