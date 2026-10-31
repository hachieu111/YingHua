import React from 'react';
import { ApiPage, TranslationStatus } from '../api/library';
import { AuthImage } from './AuthImage';

interface ReaderPageSidebarProps {
  /** Tiêu đề cột: "Chương 1 · 12 trang" hoặc "Ảnh tải lên · 6 ảnh". */
  heading: string;
  subheading?: string | null;
  pages: ApiPage[];
  currentIndex: number;
  /** Nhãn mỗi ô: "Trang 3" cho chương, "Ảnh 3" cho bộ ảnh tải lên. */
  labelOf: (page: ApiPage, index: number) => string;
  /** Trạng thái xử lý mới nhất theo id trang (thay cho trạng thái lúc nạp danh sách). */
  liveStatus: (page: ApiPage) => TranslationStatus | null;
  onSelect: (index: number) => void;
  onOpenUpload: () => void;
}

const badgeOf = (status: TranslationStatus | null): string =>
  status === 'done' ? 'Đã dịch' : status === 'failed' ? 'Lỗi' : status ? 'Đang chờ' : 'Ảnh gốc';

/** Cột trái của trình đọc: danh sách trang của chương hoặc bộ ảnh tải lên. */
export const ReaderPageSidebar: React.FC<ReaderPageSidebarProps> = ({
  heading,
  subheading,
  pages,
  currentIndex,
  labelOf,
  liveStatus,
  onSelect,
  onOpenUpload
}) => (
  <aside className="hidden lg:flex flex-col gap-3 lg:col-span-2 sticky top-24" aria-label="Danh sách trang">
    <div className="px-1">
      <span className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{heading}</span>
      {subheading && <span className="mt-0.5 block truncate text-[11px] font-semibold text-[#a43073] dark:text-pink-400" title={subheading}>{subheading}</span>}
    </div>

    <div className="space-y-3 custom-scrollbar max-h-[70vh] overflow-y-auto pr-1">
      <div
        onClick={onOpenUpload}
        className="group relative rounded-2xl border-2 border-dashed border-pink-300 hover:border-pink-500 bg-pink-50/50 hover:bg-pink-100/60 dark:border-pink-900/50 dark:bg-pink-900/10 dark:hover:bg-pink-900/20 dark:hover:border-pink-700 p-3 flex flex-col items-center justify-center text-center cursor-pointer transition-all shadow-xs"
      >
        <div className="w-8 h-8 rounded-xl bg-white dark:bg-slate-800 shadow-xs dark:shadow-none flex items-center justify-center text-pink-500 dark:text-pink-400 group-hover:scale-110 group-hover:bg-pink-500 group-hover:text-white transition-all mb-1">
          <span className="material-symbols-outlined text-[18px]">add_photo_alternate</span>
        </div>
        <span className="text-xs font-bold text-pink-600 dark:text-pink-400">+ Tải ảnh mới</span>
        <span className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">PNG, JPG, WebP</span>
      </div>

      {pages.map((page, idx) => {
        const isSelected = idx === currentIndex;
        const label = labelOf(page, idx);
        return (
          <button
            type="button"
            key={page.id}
            onClick={() => onSelect(idx)}
            aria-current={isSelected ? 'page' : undefined}
            className={`group relative block w-full rounded-2xl overflow-hidden cursor-pointer transition-all bg-white dark:bg-slate-800 text-left ${
              isSelected
                ? 'border-2 border-pink-400 shadow-md ring-4 ring-pink-100/70 dark:border-pink-500 dark:ring-pink-900/40 dark:shadow-none'
                : 'border-2 border-transparent hover:border-pink-200 shadow-xs hover:shadow-md dark:hover:border-pink-900/60 dark:shadow-none'
            }`}
          >
            <AuthImage
              src={page.original_url}
              alt={label}
              className={`w-full h-28 object-cover object-top transition-opacity ${isSelected ? 'opacity-100' : 'opacity-80 group-hover:opacity-100'}`}
            />
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-900/85 to-transparent p-2 flex items-center justify-between text-white">
              <span className="text-[11px] font-bold">{label}</span>
              <span className="text-[10px] bg-pink-500/90 px-1.5 py-0.5 rounded text-white font-medium">{badgeOf(liveStatus(page))}</span>
            </div>
          </button>
        );
      })}
    </div>

    <div className="mt-2 p-3 rounded-2xl bg-amber-50 border border-amber-200/70 text-slate-700 shadow-xs dark:bg-amber-900/20 dark:border-amber-900/40 dark:text-slate-300 dark:shadow-none">
      <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400 font-bold text-xs mb-1">
        <span className="material-symbols-outlined text-[16px]">lightbulb</span>
        <span>Mẹo học nhanh:</span>
      </div>
      <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
        Rê chuột vào các khung phát sáng <span className="inline-block w-2 h-2 rounded-full bg-pink-400 align-middle"></span> trên ảnh để xem Pinyin, nghĩa tiếng Việt và bấm nghe phát âm nhé!
      </p>
    </div>
  </aside>
);
