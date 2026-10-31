import React, { useCallback, useEffect, useState } from 'react';
import { AdminSettings, getUserSettings, updateUserSettings } from '../api/adminUserData';
import { errorMessage, LoadState } from './AdminDataParts';

interface TabProps {
  userId: number;
  notify: (message: string) => void;
}

const FIELD = 'rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-100 dark:placeholder:text-slate-500 px-3 py-2 text-sm font-normal';
const LABEL = 'text-xs font-semibold text-slate-600 dark:text-slate-300 flex flex-col gap-1';

/** Xem và sửa cài đặt của người dùng (cùng các trường với trang cài đặt cá nhân). */
export const AdminUserSettingsTab: React.FC<TabProps> = ({ userId, notify }) => {
  const [saved, setSaved] = useState<AdminSettings | null>(null);
  const [form, setForm] = useState<AdminSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getUserSettings(userId)
      .then(value => { setSaved(value); setForm(value); })
      .catch(err => setError(errorMessage(err, 'Không tải được cài đặt')))
      .finally(() => setLoading(false));
  }, [userId]);

  useEffect(load, [load]);

  if (!form || !saved) return <LoadState loading={loading} error={error} onRetry={load} />;

  const set = <K extends keyof AdminSettings>(key: K, value: AdminSettings[K]) => setForm({ ...form, [key]: value });

  const save = async () => {
    const changes: Partial<AdminSettings> = {};
    (Object.keys(form) as (keyof AdminSettings)[]).forEach(key => {
      if (form[key] !== saved[key]) Object.assign(changes, { [key]: form[key] });
    });
    if (Object.keys(changes).length === 0) return notify('Không có thay đổi để lưu.');
    setBusy(true);
    try {
      const updated = await updateUserSettings(userId, changes);
      setSaved(updated);
      setForm(updated);
      notify('Đã lưu cài đặt của người dùng.');
    } catch (err) {
      notify(errorMessage(err, 'Không lưu được cài đặt'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid sm:grid-cols-2 gap-4">
      <label className={LABEL}>Cấp HSK
        <select value={form.hsk_level ?? ''} onChange={e => set('hsk_level', e.target.value === '' ? null : Number(e.target.value))} className={FIELD}>
          <option value="">Chưa chọn</option>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(level => <option key={level} value={level}>HSK {level}</option>)}
        </select>
      </label>
      <label className={LABEL}>Chế độ mặc định
        <select value={form.default_mode} onChange={e => set('default_mode', e.target.value as AdminSettings['default_mode'])} className={FIELD}>
          <option value="read">Đọc</option><option value="learn">Học</option>
        </select>
      </label>
      <label className={LABEL}>Mục tiêu học
        <select value={form.learning_goal ?? ''}
          onChange={e => set('learning_goal', (e.target.value || null) as AdminSettings['learning_goal'])} className={FIELD}>
          <option value="">Chưa chọn</option>
          <option value="study">Học tập</option><option value="entertainment">Giải trí</option><option value="both">Cả hai</option>
        </select>
      </label>
      <label className={LABEL}>Số trang đọc mỗi tuần
        <input type="number" min={1} value={form.weekly_page_goal ?? ''} placeholder="Chưa đặt"
          onChange={e => set('weekly_page_goal', e.target.value === '' ? null : Number(e.target.value))} className={FIELD} />
      </label>
      <label className={LABEL}>Giọng đọc (TTS)
        <input value={form.tts_voice ?? ''} maxLength={64} placeholder="Mặc định, ví dụ zh-CN-XiaoxiaoNeural"
          onChange={e => set('tts_voice', e.target.value.trim() === '' ? null : e.target.value.trim())} className={FIELD} />
      </label>
      <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 flex items-center gap-2 self-end pb-2">
        <input type="checkbox" checked={form.show_xianxia} onChange={e => set('show_xianxia', e.target.checked)} />
        Hiện truyện tiên hiệp
      </label>
      <div className="sm:col-span-2">
        <button disabled={busy} onClick={save} className="px-5 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold disabled:opacity-50">
          {busy ? 'Đang lưu...' : 'Lưu cài đặt'}
        </button>
      </div>
    </div>
  );
};
