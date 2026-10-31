import React from 'react';
import { SamplePageCandidate } from '../api/adminSystem';

interface SamplePageSelectProps {
  value: number | null;
  candidates: SamplePageCandidate[] | null;
  loadError: string | null;
  onChange: (pageId: number | null) => void;
}

const describe = (c: SamplePageCandidate): string => {
  const chapter = c.chapter_title ? `Chương ${c.chapter_number}: ${c.chapter_title}` : `Chương ${c.chapter_number}`;
  return `${c.series_title} · ${chapter} · Trang ${c.page_no} (${c.bubble_count} khung thoại)`;
};

/** Ô chọn trang mẫu cho người mới (F13.05, F04.16): chỉ liệt kê trang công khai đã dịch xong. */
export const SamplePageSelect: React.FC<SamplePageSelectProps> = ({ value, candidates, loadError, onChange }) => {
  // Trang đang đặt có thể đã không còn hợp lệ (bị gỡ, chuyển riêng tư) nên vẫn hiện để admin thấy và đổi.
  const missingCurrent = value !== null && candidates !== null && !candidates.some(c => c.page_id === value);
  const empty = candidates !== null && candidates.length === 0;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-100 p-4 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-200 sm:col-span-2">
      <label htmlFor="sample-page-select">
        Trang mẫu cho người mới
        <span className="mt-0.5 block text-[10px] font-normal text-slate-500 dark:text-slate-400">
          Chỉ hiện trang thuộc truyện công khai đã dịch xong. Chọn trang có nhiều khung thoại để người mới thử Hover &amp; Dịch.
        </span>
      </label>
      <select
        id="sample-page-select"
        value={value === null ? '' : String(value)}
        onChange={event => onChange(event.target.value === '' ? null : Number(event.target.value))}
        disabled={candidates === null}
        className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 font-normal outline-none focus:ring-2 focus:ring-pink-200 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-200 dark:focus:ring-pink-900/40 disabled:opacity-50"
      >
        <option value="">— Không dùng trang mẫu —</option>
        {missingCurrent && <option value={String(value)}>Trang #{value} (không còn hợp lệ)</option>}
        {candidates?.map(c => (
          <option key={c.page_id} value={String(c.page_id)}>{describe(c)}</option>
        ))}
      </select>
      {candidates === null && !loadError && <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">Đang tải danh sách trang...</span>}
      {loadError && <span role="alert" className="text-[10px] font-normal text-rose-600 dark:text-rose-300">{loadError}</span>}
      {empty && (
        <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">
          Chưa có trang nào đủ điều kiện. Hãy đăng một truyện công khai và chờ trang dịch xong.
        </span>
      )}
      {missingCurrent && (
        <span className="text-[10px] font-normal text-amber-600 dark:text-amber-400">Trang mẫu đang đặt không còn hiển thị được, nên chọn trang khác.</span>
      )}
    </div>
  );
};
