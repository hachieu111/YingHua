import React, { useCallback, useEffect, useState } from 'react';
import {
  deleteUserVocab,
  deleteUserVocabContext,
  getUserVocab,
  listUserVocab,
  updateUserVocab
} from '../api/adminUserData';
import { ApiVocabDetail, ApiVocabItem, UpdateVocabBody, VocabPage, VocabStatus } from '../api/vocab';
import { CARD_STATE_LABEL, CARD_TYPE_LABEL } from '../api/review';
import { AuthImage } from './AuthImage';
import { ConfirmDialog } from './ConfirmDialog';
import { Chip, errorMessage, formatDateTime, LoadState, Pager, STATUS_LABEL } from './AdminDataParts';

interface TabProps {
  userId: number;
  notify: (message: string) => void;
}

const PAGE_SIZE = 10;
const STATUSES: VocabStatus[] = ['learning', 'known', 'ignored'];

type Pending = { kind: 'entry' } | { kind: 'context'; contextId: number };

/** Chi tiết + sửa một mục từ của người dùng: trạng thái, ghi chú, nghĩa, sao, ngữ cảnh, thẻ. */
const VocabDetailEditor: React.FC<TabProps & { entryId: number; onBack: () => void; onChanged: () => void }> = ({
  userId, entryId, notify, onBack, onChanged
}) => {
  const [detail, setDetail] = useState<ApiVocabDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [meaning, setMeaning] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);

  const apply = (value: ApiVocabDetail) => {
    setDetail(value);
    setMeaning(value.meaning_vi ?? '');
    setNote(value.note ?? '');
  };

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getUserVocab(userId, entryId)
      .then(apply)
      .catch(err => setError(errorMessage(err, 'Không tải được mục từ')))
      .finally(() => setLoading(false));
  }, [userId, entryId]);

  useEffect(load, [load]);

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true);
    try {
      await action();
      notify(success);
    } catch (err) {
      notify(errorMessage(err, 'Thao tác không thành công'));
    } finally {
      setBusy(false);
    }
  };

  const patch = (body: UpdateVocabBody, success: string) =>
    run(async () => {
      apply(await updateUserVocab(userId, entryId, body));
      onChanged();
    }, success);

  const saveText = () => {
    if (!detail) return;
    const body: UpdateVocabBody = {};
    if (meaning.trim() && meaning.trim() !== (detail.meaning_vi ?? '')) body.meaning_vi = meaning.trim();
    if (note !== (detail.note ?? '')) body.note = note.trim() === '' ? null : note;
    if (Object.keys(body).length === 0) return notify('Không có thay đổi để lưu.');
    return patch(body, 'Đã lưu thay đổi của mục từ.');
  };

  const confirmDelete = async () => {
    const target = pending;
    if (!target) return;
    await run(async () => {
      if (target.kind === 'entry') {
        await deleteUserVocab(userId, entryId);
        onChanged();
        onBack();
      } else {
        await deleteUserVocabContext(userId, entryId, target.contextId);
        apply(await getUserVocab(userId, entryId));
        onChanged();
      }
    }, target.kind === 'entry' ? 'Đã xóa mục từ.' : 'Đã xóa ngữ cảnh.');
    setPending(null);
  };

  return (
    <div className="flex flex-col gap-4">
      <button onClick={onBack} className="self-start text-xs font-bold text-[#a43073]">← Về danh sách từ</button>
      {!detail ? <LoadState loading={loading} error={error} onRetry={load} /> : (
        <>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-2xl font-bold text-slate-800">{detail.term}</div>
              <div className="text-xs text-slate-500">{detail.pinyin} {detail.sino_vietnamese ? `· ${detail.sino_vietnamese}` : ''} {detail.hsk_level ? `· HSK ${detail.hsk_level}` : ''}</div>
            </div>
            <button disabled={busy} onClick={() => patch({ is_starred: !detail.is_starred }, detail.is_starred ? 'Đã bỏ sao.' : 'Đã gắn sao.')}
              aria-pressed={detail.is_starred} className={`px-3 py-1.5 rounded-full text-xs font-bold ${detail.is_starred ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
              {detail.is_starred ? '★ Đã gắn sao' : '☆ Gắn sao'}
            </button>
          </div>

          <div className="flex gap-2 flex-wrap">
            {STATUSES.map(s => <Chip key={s} active={detail.status === s} onClick={() => detail.status !== s && void patch({ status: s }, `Đã chuyển sang “${STATUS_LABEL[s]}”.`)}>{STATUS_LABEL[s]}</Chip>)}
          </div>

          <label className="text-xs font-semibold text-slate-600 flex flex-col gap-1">Nghĩa tiếng Việt
            <input value={meaning} maxLength={500} onChange={e => setMeaning(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-normal" />
          </label>
          <label className="text-xs font-semibold text-slate-600 flex flex-col gap-1">Ghi chú
            <textarea value={note} maxLength={2000} rows={3} onChange={e => setNote(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-normal" />
          </label>
          <div className="flex gap-2">
            <button disabled={busy} onClick={saveText} className="px-4 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold disabled:opacity-50">Lưu thay đổi</button>
            <button disabled={busy} onClick={() => setPending({ kind: 'entry' })} className="px-4 py-2 rounded-full bg-rose-50 text-rose-700 text-xs font-bold disabled:opacity-50">Xóa từ</button>
          </div>

          <section>
            <h4 className="text-xs font-bold text-slate-700 mb-2">Ngữ cảnh ({detail.contexts.length})</h4>
            {detail.contexts.length === 0 && <div className="text-xs text-slate-500">Chưa có ngữ cảnh.</div>}
            <div className="flex flex-col gap-2">
              {detail.contexts.map(c => (
                <div key={c.id} className="flex gap-3 rounded-xl border border-slate-100 p-3">
                  <AuthImage src={c.snippet_url} alt="Ảnh ngữ cảnh" className="w-24 h-16 rounded-lg object-cover shrink-0" />
                  <div className="min-w-0 flex-1 text-xs">
                    <div className="font-semibold text-slate-800">{c.sentence_zh}</div>
                    {c.sentence_vi && <div className="text-slate-500">{c.sentence_vi}</div>}
                    <div className="text-[10px] text-slate-400 mt-1">{c.source_label ?? 'Không rõ nguồn'} · {formatDateTime(c.created_at)}</div>
                  </div>
                  <button disabled={busy} onClick={() => setPending({ kind: 'context', contextId: c.id })} className="self-start text-[11px] font-bold text-rose-600 disabled:opacity-50">Xóa</button>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h4 className="text-xs font-bold text-slate-700 mb-2">Thẻ ôn ({detail.cards.length})</h4>
            <div className="flex flex-col gap-1">
              {detail.cards.map(c => (
                <div key={c.id} className="flex flex-wrap justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  <span className="font-semibold">{CARD_TYPE_LABEL[c.card_type]}{c.is_suspended ? ' (tạm ngưng)' : ''}</span>
                  <span>{CARD_STATE_LABEL[c.state] ?? c.state} · hạn {formatDateTime(c.due_at)} · ôn {c.reps} lần, quên {c.lapses}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
      {pending && (
        <ConfirmDialog
          title={pending.kind === 'entry' ? 'Xóa từ này?' : 'Xóa ngữ cảnh này?'}
          message={pending.kind === 'entry' ? 'Từ cùng toàn bộ ngữ cảnh và thẻ ôn của người dùng sẽ bị xóa vĩnh viễn.' : 'Ngữ cảnh sẽ bị xóa khỏi từ của người dùng.'}
          confirmLabel="Xóa" busy={busy} onConfirm={confirmDelete} onCancel={() => setPending(null)}
        />
      )}
    </div>
  );
};

/** Sổ tay của người dùng: tìm kiếm, lọc, phân trang, mở chi tiết để sửa/xóa (F13.07). */
export const AdminUserVocabTab: React.FC<TabProps> = ({ userId, notify }) => {
  const [data, setData] = useState<VocabPage | null>(null);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<VocabStatus | undefined>();
  const [starred, setStarred] = useState(false);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => setPage(1), [q, status, starred]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      listUserVocab(userId, { q: q.trim() || undefined, status, starred: starred || undefined, page, size: PAGE_SIZE }, controller.signal)
        .then(setData)
        .catch(err => { if (!controller.signal.aborted) setError(errorMessage(err, 'Không tải được Sổ tay')); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [userId, q, status, starred, page, version]);

  if (openId !== null) {
    return <VocabDetailEditor userId={userId} entryId={openId} notify={notify} onBack={() => setOpenId(null)} onChanged={() => setVersion(v => v + 1)} />;
  }

  const items: ApiVocabItem[] = data?.items ?? [];
  return (
    <div className="flex flex-col gap-3">
      <input value={q} onChange={e => setQ(e.target.value)} placeholder="Tìm theo chữ Hán, pinyin hoặc nghĩa..." aria-label="Tìm trong Sổ tay"
        className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
      <div className="flex gap-2 flex-wrap">
        <Chip active={!status} onClick={() => setStatus(undefined)}>Tất cả</Chip>
        {STATUSES.map(s => <Chip key={s} active={status === s} onClick={() => setStatus(s)}>{STATUS_LABEL[s]}</Chip>)}
        <Chip active={starred} onClick={() => setStarred(v => !v)}>★ Có sao</Chip>
      </div>
      <LoadState loading={loading && !data} error={error} empty={!loading && !error && items.length === 0} emptyText="Không có từ nào phù hợp" onRetry={() => setVersion(v => v + 1)} />
      <div className="divide-y divide-slate-100 rounded-xl border border-slate-100">
        {items.map(item => (
          <button key={item.id} onClick={() => setOpenId(item.id)} className="w-full text-left flex items-center justify-between gap-3 p-3 hover:bg-slate-50">
            <div className="min-w-0">
              <div className="text-sm font-bold text-slate-800">{item.term} <span className="text-xs font-normal text-slate-500">{item.pinyin}</span> {item.is_starred && <span className="text-amber-500">★</span>}</div>
              <div className="text-xs text-slate-500 truncate">{item.meaning_vi ?? '—'}</div>
            </div>
            <span className="shrink-0 rounded-full bg-pink-50 px-2 py-0.5 text-[10px] font-bold text-[#a43073]">{STATUS_LABEL[item.status]}</span>
          </button>
        ))}
      </div>
      {data && data.total > 0 && <Pager page={page} size={PAGE_SIZE} total={data.total} onPage={setPage} />}
    </div>
  );
};
