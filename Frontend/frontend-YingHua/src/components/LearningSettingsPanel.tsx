import React, { useCallback, useEffect, useState } from 'react';
import { errorMessage } from '../api/client';
import {
  ApiSettings,
  BUBBLE_FONT_SCALE_MAX,
  BUBBLE_FONT_SCALE_MIN,
  BUBBLE_FONT_SCALE_STEP,
  getSettings,
  updateSettings
} from '../api/settings';
import { TtsVoice, listVoices, synthesize } from '../api/tts';

interface LearningSettingsPanelProps {
  /** Gọi sau khi lưu thành công để nơi khác (hồ sơ, Thư viện) cập nhật theo. */
  onSaved: (settings: ApiSettings) => void;
  showToast: (message: string) => void;
}

const WEEKLY_GOAL_MAX = 1000;
const HSK_LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9];
const VOICE_SAMPLE_TEXT = '你好，欢迎来到映画。';
const BUBBLE_SAMPLE_BASE_PX = 12;

const fieldClass =
  'w-full bg-[#eff4ff] text-slate-800 text-xs px-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all';
const labelClass = 'text-xs font-semibold text-slate-700';

/** Cài đặt học tập của người học (F02.01-F02.03): trình độ, chế độ mặc định, giọng đọc, mục tiêu. */
export const LearningSettingsPanel: React.FC<LearningSettingsPanelProps> = ({ onSaved, showToast }) => {
  const [saved, setSaved] = useState<ApiSettings | null>(null);
  const [form, setForm] = useState<ApiSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [voices, setVoices] = useState<TtsVoice[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(true);
  const [previewing, setPreviewing] = useState(false);

  // Danh sách giọng lấy từ máy chủ; lỗi thì chỉ còn giọng mặc định và giọng đang lưu.
  useEffect(() => {
    const controller = new AbortController();
    listVoices(controller.signal)
      .then(result => setVoices(result.items))
      .catch(() => setVoices([]))
      .finally(() => {
        if (!controller.signal.aborted) setVoicesLoading(false);
      });
    return () => controller.abort();
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getSettings()
      .then(value => {
        setSaved(value);
        setForm(value);
      })
      .catch(err => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  if (!form || !saved) {
    return loading ? (
      <div className="flex justify-center py-8">
        <span className="w-6 h-6 border-2 border-pink-300 border-t-transparent rounded-full animate-spin"></span>
      </div>
    ) : (
      <div className="flex flex-col items-center gap-3 py-6 text-center" role="alert">
        <p className="text-xs text-red-700">{error ?? 'Không tải được cài đặt học tập.'}</p>
        <button onClick={load} className="px-4 py-1.5 rounded-full bg-white border border-pink-200 text-[#a43073] text-xs font-bold hover:bg-pink-50">
          Thử lại
        </button>
      </div>
    );
  }

  const set = <K extends keyof ApiSettings>(key: K, value: ApiSettings[K]) => setForm({ ...form, [key]: value });
  const goalInvalid = form.weekly_page_goal !== null && (form.weekly_page_goal < 1 || form.weekly_page_goal > WEEKLY_GOAL_MAX);
  // Bật nhắc ôn mà chưa chọn giờ thì máy chủ không biết nhắc lúc nào (F14.03).
  const reminderInvalid = form.reminder_enabled && !form.reminder_time;

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (goalInvalid) {
      showToast(`Mục tiêu trang mỗi tuần phải từ 1 đến ${WEEKLY_GOAL_MAX}.`);
      return;
    }
    if (reminderInvalid) return;
    const changes: Partial<ApiSettings> = {};
    (Object.keys(form) as (keyof ApiSettings)[]).forEach(key => {
      if (form[key] !== saved[key]) Object.assign(changes, { [key]: form[key] });
    });
    if (Object.keys(changes).length === 0) {
      showToast('Chưa có thay đổi nào để lưu.');
      return;
    }
    setBusy(true);
    try {
      const updated = await updateSettings(changes);
      setSaved(updated);
      setForm(updated);
      onSaved(updated);
      showToast('Đã lưu cài đặt học tập.');
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const voiceKnown = form.tts_voice === null || voices.some(voice => voice.short_name === form.tts_voice);

  // Nghe thử giọng đang chọn (chưa cần lưu): gửi giọng trực tiếp cho máy chủ.
  const handlePreviewVoice = async () => {
    if (previewing) return;
    setPreviewing(true);
    try {
      const result = await synthesize(VOICE_SAMPLE_TEXT, { voice: form.tts_voice ?? undefined });
      const url = URL.createObjectURL(result.audio);
      const audio = new Audio(url);
      const release = () => URL.revokeObjectURL(url);
      audio.onended = release;
      audio.onerror = release;
      await audio.play();
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setPreviewing(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className={labelClass} htmlFor="setting-hsk">Trình độ HSK hiện tại</label>
          <select id="setting-hsk" value={form.hsk_level ?? ''} onChange={e => set('hsk_level', e.target.value === '' ? null : Number(e.target.value))} className={fieldClass}>
            <option value="">Chưa chọn</option>
            {HSK_LEVELS.map(level => (
              <option key={level} value={level}>HSK {level}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className={labelClass} htmlFor="setting-mode">Chế độ đọc mặc định</label>
          <select id="setting-mode" value={form.default_mode} onChange={e => set('default_mode', e.target.value as ApiSettings['default_mode'])} className={fieldClass}>
            <option value="read">Đọc (xem bản dịch)</option>
            <option value="learn">Học (Hover và tra từ)</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className={labelClass} htmlFor="setting-goal">Mục tiêu học</label>
          <select id="setting-goal" value={form.learning_goal ?? ''} onChange={e => set('learning_goal', (e.target.value || null) as ApiSettings['learning_goal'])} className={fieldClass}>
            <option value="">Chưa chọn</option>
            <option value="study">Học tiếng Trung</option>
            <option value="entertainment">Giải trí</option>
            <option value="both">Cả hai</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className={labelClass} htmlFor="setting-weekly">Mục tiêu trang mỗi tuần</label>
          <input
            id="setting-weekly"
            type="number"
            min={1}
            max={WEEKLY_GOAL_MAX}
            value={form.weekly_page_goal ?? ''}
            placeholder="Chưa đặt"
            onChange={e => set('weekly_page_goal', e.target.value === '' ? null : Number(e.target.value))}
            className={`${fieldClass} ${goalInvalid ? 'ring-2 ring-red-300' : ''}`}
          />
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2">
          <label className={labelClass} htmlFor="setting-voice">Giọng đọc (TTS)</label>
          <div className="flex items-center gap-2">
            <select id="setting-voice" value={form.tts_voice ?? ''} onChange={e => set('tts_voice', e.target.value || null)} className={fieldClass} aria-busy={voicesLoading}>
              <option value="">Giọng mặc định của hệ thống</option>
              {!voiceKnown && <option value={form.tts_voice ?? ''}>{form.tts_voice}</option>}
              {voices.map(voice => (
                <option key={voice.short_name} value={voice.short_name}>
                  {voice.friendly_name} ({voice.gender === 'male' ? 'nam' : 'nữ'}, {voice.locale})
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void handlePreviewVoice()}
              disabled={previewing}
              className="shrink-0 px-4 py-2.5 rounded-full bg-white border border-pink-200 text-[#a43073] text-xs font-bold hover:bg-pink-50 disabled:opacity-60 flex items-center gap-1"
              title="Nghe thử giọng đang chọn"
            >
              <span className="material-symbols-outlined text-[16px]">volume_up</span>
              <span>{previewing ? 'Đang phát...' : 'Nghe thử'}</span>
            </button>
          </div>
          {voicesLoading && <span className="text-[11px] text-slate-400">Đang tải danh sách giọng...</span>}
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2">
          <label className={labelClass} htmlFor="setting-font-scale">Cỡ chữ bản dịch trên trang: {form.bubble_font_scale}%</label>
          <input
            id="setting-font-scale"
            type="range"
            min={BUBBLE_FONT_SCALE_MIN}
            max={BUBBLE_FONT_SCALE_MAX}
            step={BUBBLE_FONT_SCALE_STEP}
            value={form.bubble_font_scale}
            onChange={e => set('bubble_font_scale', Number(e.target.value))}
            className="w-full accent-[#a43073]"
          />
          <span
            className="rounded-xl bg-white/95 border border-pink-200 px-2.5 py-1 font-semibold text-pink-900 w-fit"
            style={{ fontSize: `${(BUBBLE_SAMPLE_BASE_PX * form.bubble_font_scale) / 100}px` }}
          >
            Chữ mẫu của bản dịch
          </span>
        </div>
      </div>

      <label className="flex items-start gap-2.5 p-3 rounded-2xl bg-pink-50/60 border border-pink-100 cursor-pointer">
        <input type="checkbox" checked={form.show_xianxia} onChange={e => set('show_xianxia', e.target.checked)} className="mt-0.5" />
        <span>
          <span className="text-xs font-bold text-slate-800 block">Hiện thuật ngữ tu tiên</span>
          <span className="text-[11px] text-slate-500">Bật để hiển thị các thuật ngữ tiên hiệp (cảnh giới, công pháp...) khi đọc và tra từ.</span>
        </span>
      </label>

      <div className="flex flex-col gap-2 p-3 rounded-2xl bg-pink-50/60 border border-pink-100">
        <label className="flex items-start gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={form.reminder_enabled}
            onChange={e => set('reminder_enabled', e.target.checked)}
            className="mt-0.5"
          />
          <span>
            <span className="text-xs font-bold text-slate-800 block">Nhắc ôn thẻ mỗi ngày</span>
            <span className="text-[11px] text-slate-500">Nhận thông báo trong ứng dụng vào giờ bạn chọn khi có thẻ đến hạn.</span>
          </span>
        </label>
        {form.reminder_enabled && (
          <div className="flex flex-col gap-1 pl-6">
            <label className={labelClass} htmlFor="setting-reminder-time">Giờ nhắc</label>
            <input
              id="setting-reminder-time"
              type="time"
              value={form.reminder_time ?? ''}
              onChange={e => set('reminder_time', e.target.value === '' ? null : e.target.value)}
              className={`${fieldClass} sm:w-40 ${reminderInvalid ? 'ring-2 ring-red-300' : ''}`}
              aria-invalid={reminderInvalid}
            />
            {reminderInvalid && <span className="text-[11px] text-red-600" role="alert">Hãy chọn giờ nhắc để bật nhắc ôn.</span>}
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={busy || goalInvalid || reminderInvalid}
          className="px-6 py-2.5 rounded-full bg-gradient-to-r from-pink-500 to-[#a43073] text-white font-bold text-xs shadow-md disabled:opacity-60 flex items-center gap-1.5"
        >
          <span className="material-symbols-outlined text-[16px]">save</span>
          <span>{busy ? 'Đang lưu...' : 'Lưu cài đặt học tập'}</span>
        </button>
      </div>
    </form>
  );
};
