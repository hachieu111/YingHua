import React, { useCallback, useEffect, useState } from 'react';
import {
  SamplePageCandidate,
  SystemSettings,
  SystemSettingsValues,
  getSystemSettings,
  listSamplePageCandidates,
  updateSystemSettings
} from '../api/adminSystem';
import { isAbortedError } from '../api/client';
import { LoadState, errorMessage } from './AdminDataParts';
import { SamplePageSelect } from './SamplePageSelect';

type BooleanKey = {
  [K in keyof SystemSettingsValues]: SystemSettingsValues[K] extends boolean ? K : never;
}[keyof SystemSettingsValues];
type NumberKey = 'quiz_daily_llm_limit' | 'ai_note_daily_limit' | 'grammar_daily_limit' | 'mistake_review_daily_limit';

const SWITCHES: { key: BooleanKey; label: string; description: string; note?: string }[] = [
  { key: 'llm_enabled', label: 'Tính năng AI (LLM)', description: 'Đề kiểm tra AI, thẻ mở rộng AI, phân tích ngữ pháp. Tắt thì dùng đề dự phòng.' },
  { key: 'tts_enabled', label: 'Nghe phát âm (TTS)', description: 'Phát âm từ và câu bằng giọng máy chủ.' },
  { key: 'maintenance_mode', label: 'Chế độ bảo trì', description: 'Mọi API trả 503 cho người dùng thường (kèm băng thông báo bảo trì); quản trị viên vẫn dùng bình thường.' },
  { key: 'auto_moderation_enabled', label: 'Kiểm duyệt tự động', description: 'Gắn cờ nghi vấn cho ảnh mới tải lên trong hàng chờ kiểm duyệt.' },
  { key: 'ocr_on_upload_enabled', label: 'OCR khi tải ảnh lên', description: 'Nhận diện chữ ngay khi tải ảnh.', note: 'Chưa có tác dụng' },
  { key: 'admin_notifications_enabled', label: 'Thông báo quản trị', description: 'Nhận thông báo khi có báo lỗi hoặc khiếu nại mới.' }
];

const LIMITS: { key: NumberKey; label: string }[] = [
  { key: 'quiz_daily_llm_limit', label: 'Số đề kiểm tra AI mỗi người mỗi ngày' },
  { key: 'ai_note_daily_limit', label: 'Số thẻ mở rộng AI mỗi người mỗi ngày' },
  { key: 'grammar_daily_limit', label: 'Số lượt phân tích ngữ pháp mỗi người mỗi ngày' },
  { key: 'mistake_review_daily_limit', label: 'Số lượt ôn lại câu sai bằng AI mỗi người mỗi ngày' }
];

interface AdminSettingsPanelProps {
  notify: (message: string) => void;
}

/** Cài đặt hệ thống (F13.05): chỉ gửi các khóa đã đổi, lỗi giá trị hiện ngay trong khung. */
export const AdminSettingsPanel: React.FC<AdminSettingsPanelProps> = ({ notify }) => {
  const [saved, setSaved] = useState<SystemSettings | null>(null);
  const [draft, setDraft] = useState<SystemSettingsValues | null>(null);
  const [candidates, setCandidates] = useState<SamplePageCandidate[] | null>(null);
  const [candidatesError, setCandidatesError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(value => value + 1), []);

  const adopt = (settings: SystemSettings) => {
    setSaved(settings);
    setDraft(settings.values);
  };

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    getSystemSettings(controller.signal)
      .then(settings => {
        adopt(settings);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err, 'Không tải được cài đặt hệ thống'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    setCandidatesError(null);
    listSamplePageCandidates(controller.signal)
      .then(setCandidates)
      .catch(err => {
        if (!isAbortedError(err)) setCandidatesError(errorMessage(err, 'Không tải được danh sách trang mẫu'));
      });
    return () => controller.abort();
  }, [tick]);

  if (!saved || !draft) return <div className="p-4"><LoadState loading={loading} error={error} onRetry={reload} /></div>;

  const changes: Partial<SystemSettingsValues> = {};
  (Object.keys(draft) as (keyof SystemSettingsValues)[]).forEach(key => {
    if (draft[key] !== saved.values[key]) Object.assign(changes, { [key]: draft[key] });
  });
  const dirty = Object.keys(changes).length > 0;

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      adopt(await updateSystemSettings(changes));
      notify('Đã lưu cài đặt hệ thống.');
    } catch (err) {
      setSaveError(errorMessage(err, 'Không lưu được cài đặt, vui lòng thử lại'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {SWITCHES.map(({ key, label, description, note }) => (
          <div key={key} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 p-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5 text-xs font-bold">
                {label}
                {note && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[9px] font-semibold text-slate-500">{note}</span>}
                {saved.overridden.includes(key) && <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-semibold text-blue-600">Đã tùy chỉnh</span>}
              </div>
              <div className="mt-1 text-[10px] text-slate-500">{description}</div>
            </div>
            <button
              role="switch"
              aria-checked={draft[key]}
              aria-label={label}
              onClick={() => setDraft({ ...draft, [key]: !draft[key] })}
              className={`relative h-5 w-9 shrink-0 rounded-full ${draft[key] ? 'bg-blue-600' : 'bg-slate-300'}`}
            >
              <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${draft[key] ? 'left-[18px]' : 'left-0.5'}`} />
            </button>
          </div>
        ))}
      </div>

      <h3 className="mb-2 mt-5 text-xs font-bold text-slate-700">Hạn mức dùng AI mỗi ngày</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        {LIMITS.map(({ key, label }) => (
          <label key={key} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 p-4 text-xs font-semibold text-slate-700">
            <span>{label}</span>
            <input
              type="number"
              min={0}
              value={draft[key]}
              onChange={event => setDraft({ ...draft, [key]: event.target.value === '' ? 0 : Number(event.target.value) })}
              className="w-20 rounded-lg border border-slate-200 px-2 py-1 text-right outline-none focus:ring-2 focus:ring-pink-200"
            />
          </label>
        ))}
        <SamplePageSelect
          value={draft.sample_page_id}
          candidates={candidates}
          loadError={candidatesError}
          onChange={pageId => setDraft({ ...draft, sample_page_id: pageId })}
        />
      </div>

      {saveError && <div role="alert" className="mt-4 rounded-xl bg-rose-50 p-3 text-xs font-semibold text-rose-700">{saveError}</div>}
      <div className="mt-4 flex justify-end gap-2">
        <button disabled={!dirty || saving} onClick={() => adopt(saved)} className="rounded-full bg-slate-100 px-4 py-2 text-xs font-bold text-slate-600 disabled:opacity-40">Hoàn tác</button>
        <button disabled={!dirty || saving} onClick={() => void save()} className="rounded-full bg-[#a43073] px-5 py-2 text-xs font-bold text-white hover:bg-[#85145a] disabled:opacity-40">
          {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
        </button>
      </div>
    </div>
  );
};
