import React, { useEffect, useRef, useState } from 'react';
import { errorMessage } from '../api/client';
import { retranslatePage } from '../api/imaging';
import {
  ApiChapter,
  ApiPage,
  ApiSeries,
  getSeries,
  listSeries,
  quickUpload,
  uploadChapterPages,
  validateImageFile,
  MAX_CHAPTER_UPLOAD_FILES
} from '../api/library';
import { TourReplayButton } from '../tour/TourReplayButton';
import { useTourModal } from '../tour/TourProvider';
import { ReaderTarget } from '../types';
import { formatChapterNumber } from '../utils/format';
import { AuthImage } from './AuthImage';
import { StatusPill } from './StatusPill';
import { usePageStatuses } from './usePageStatuses';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Gọi sau khi máy chủ nhận ảnh (để danh sách "Ảnh bạn đã tải lên" tải lại). */
  onUploaded: (pages: ApiPage[]) => void;
  onOpenReader: (target: ReaderTarget) => void;
  /** Mở trình quản lý truyện riêng (tạo truyện, thêm chương). */
  onOpenManager: () => void;
}

const DEMO_SAMPLE_IMAGE =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuBVsWOJghq30gbfhVWR5jlmhtSNvLHB-VswJral2VtbwsmZLOE5Fx0rBfNPh3YdFyEdwI4sYdh6G3RAU1QsY5lNUdgE5YfCjJFRJEnnYN2iI5ayZMDMdWadWQ9yS0aKVCjaRgJung8D2BAHRKintY0EUHWSAAoU9FNdEOSYHrMM7LUT5szykBJ-_hyCql_yd6kwo0rQqMaI_Xafc_WjPgqq7hSaKm3GFxwaeKyFTVxu4gahbAFapVcvgG9ro4Ntj5Q34A';

type Destination = 'quick' | 'chapter';

interface UploadedRow {
  page: ApiPage;
  filename: string;
}

export const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose, onUploaded, onOpenReader, onOpenManager }) => {
  const [destination, setDestination] = useState<Destination>('quick');
  const [files, setFiles] = useState<File[]>([]);
  const [problems, setProblems] = useState<string[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [rows, setRows] = useState<UploadedRow[]>([]);
  const [mineSeries, setMineSeries] = useState<ApiSeries[]>([]);
  const [seriesId, setSeriesId] = useState<number | null>(null);
  const [chapters, setChapters] = useState<ApiChapter[]>([]);
  const [chapterId, setChapterId] = useState<number | null>(null);
  const [destinationError, setDestinationError] = useState<string | null>(null);
  const [showDemo, setShowDemo] = useState<boolean>(false);
  const [retrying, setRetrying] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useTourModal('upload', isOpen);

  const pageIds = rows.map(row => row.page.id);
  const { statuses, timedOut, restart } = usePageStatuses(pageIds, isOpen);

  // Đóng cửa sổ: dọn trạng thái; việc hỏi trạng thái tự dừng vì isOpen = false.
  useEffect(() => {
    if (isOpen) return;
    setFiles([]);
    setProblems([]);
    setRows([]);
    setUploading(false);
    setShowDemo(false);
    setDestination('quick');
    setDestinationError(null);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || destination !== 'chapter') return;
    let cancelled = false;
    listSeries({ scope: 'mine', size: 100 })
      .then(data => {
        if (cancelled) return;
        setMineSeries(data.items);
        setDestinationError(null);
        setSeriesId(current => current ?? data.items[0]?.id ?? null);
      })
      .catch(err => {
        if (!cancelled) setDestinationError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, destination]);

  useEffect(() => {
    if (seriesId === null) {
      setChapters([]);
      setChapterId(null);
      return;
    }
    let cancelled = false;
    getSeries(seriesId)
      .then(detail => {
        if (cancelled) return;
        setChapters(detail.chapters);
        setChapterId(detail.chapters[0]?.id ?? null);
      })
      .catch(err => {
        if (!cancelled) setDestinationError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [seriesId]);

  if (!isOpen) return null;

  const acceptFiles = (list: FileList | File[]) => {
    const picked = Array.from(list);
    const messages: string[] = [];
    const valid: File[] = [];
    picked.forEach(file => {
      const problem = validateImageFile(file);
      if (problem) messages.push(problem);
      else valid.push(file);
    });
    const limit = destination === 'quick' ? 5 : MAX_CHAPTER_UPLOAD_FILES;
    setFiles(valid.slice(0, limit));
    if (valid.length > limit) {
      const notice = destination === 'quick'
        ? 'Tải nhanh tối đa 5 ảnh mỗi lần, đã lấy 5 ảnh đầu.'
        : `Mỗi lần tải tối đa ${MAX_CHAPTER_UPLOAD_FILES} ảnh, đã lấy ${MAX_CHAPTER_UPLOAD_FILES} ảnh đầu`;
      setProblems([...messages, notice]);
    } else {
      setProblems(messages);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) acceptFiles(event.target.files);
    event.target.value = '';
  };

  const handleSubmit = async () => {
    if (files.length === 0 || uploading) return;
    if (destination === 'chapter' && chapterId === null) {
      setProblems(['Hãy chọn chương của truyện riêng để tải ảnh vào.']);
      return;
    }
    setUploading(true);
    setProblems([]);
    const uploaded: UploadedRow[] = [];
    const failures: string[] = [];
    try {
      if (destination === 'quick') {
        for (const file of files) {
          try {
            uploaded.push({ page: await quickUpload(file), filename: file.name });
          } catch (err) {
            failures.push(`“${file.name}”: ${errorMessage(err)}`);
          }
        }
      } else if (chapterId !== null) {
        const result = await uploadChapterPages(chapterId, files);
        result.results.forEach(item => {
          if (item.page) uploaded.push({ page: item.page, filename: item.filename ?? `Trang ${item.page.page_no}` });
          else failures.push(`“${item.filename ?? 'ảnh'}”: ${item.error?.message ?? 'Không tải lên được'}`);
        });
      }
    } catch (err) {
      failures.push(errorMessage(err));
    }
    setUploading(false);
    setProblems(failures);
    if (uploaded.length > 0) {
      setRows(uploaded);
      setFiles([]);
      onUploaded(uploaded.map(row => row.page));
    }
  };

  const handleRetranslate = async (pageId: number) => {
    setRetrying(pageId);
    try {
      await retranslatePage(pageId);
      restart(pageId);
    } catch (err) {
      setProblems([errorMessage(err)]);
    } finally {
      setRetrying(null);
    }
  };

  const openTranslated = (page: ApiPage) => {
    onOpenReader({ chapterId: page.chapter_id, pageId: page.id, pageNo: page.page_no });
    onClose();
  };

  const showingResults = rows.length > 0;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div data-tour="upload-panel" className="bg-white dark:bg-[#0f172a] w-full max-w-lg max-h-[92vh] overflow-y-auto rounded-3xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 transition-colors duration-300">

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 dark:border-slate-700 bg-gradient-to-r from-pink-50/70 via-white to-pink-50/40 dark:from-pink-900/20 dark:via-[#0f172a] dark:to-pink-900/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center text-[#a43073] dark:text-pink-400 text-sm">
              <span className="material-symbols-outlined text-[20px]">cloud_upload</span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800 dark:text-white">Tải ảnh Manhua cần dịch</h3>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                Tự động nhận dạng ký tự tiếng Trung & dịch sang Tiếng Việt
              </p>
            </div>
          </div>
          <TourReplayButton className="flex ml-auto mr-2" />
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 flex items-center justify-center transition-colors"
            aria-label="Đóng"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">

          {showingResults ? (
            <div data-tour="upload-results" className="space-y-3">
              <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-900/50 text-xs text-emerald-900 dark:text-emerald-300 font-semibold flex items-start gap-2">
                <span className="material-symbols-outlined text-[18px] text-emerald-600 dark:text-emerald-400">check_circle</span>
                <span>Đã tải lên {rows.length} ảnh. Hệ thống xử lý lần lượt; bạn có thể đóng cửa sổ này, kết quả hiện ở Thư viện.</span>
              </div>
              {rows.map(({ page, filename }) => {
                const live = statuses[page.id];
                const status = live ? live.status : page.status;
                return (
                  <div key={page.id} className="flex items-start gap-3 p-3 rounded-2xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                    <AuthImage src={page.original_url} alt={filename} className="w-14 h-14 object-cover rounded-xl shrink-0" />
                    <div className="min-w-0 flex-1 flex flex-col gap-1">
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">{filename}</span>
                      <StatusPill status={status} textReady={(live ? live.text_ready : page.text_ready) === true} />
                      {status === 'queued' && (
                        <span className="text-[10px] text-slate-400 dark:text-slate-500">Đang chờ đến lượt xử lý, có thể mất vài phút.</span>
                      )}
                      {status === 'failed' && (
                        <span className="text-[11px] text-red-600 dark:text-red-400">
                          {live?.error_message ?? page.error_message ?? 'Xử lý ảnh không thành công.'}
                        </span>
                      )}
                      <div className="flex items-center gap-2 pt-1">
                        {status === 'done' && (
                          <button onClick={() => openTranslated(page)} className="px-3 py-1 rounded-full bg-[#a43073] text-white text-[11px] font-bold hover:bg-[#85145a]">
                            Mở bản dịch
                          </button>
                        )}
                        {status === 'failed' && (live?.can_retranslate ?? true) && (
                          <button
                            onClick={() => handleRetranslate(page.id)}
                            disabled={retrying === page.id}
                            className="px-3 py-1 rounded-full bg-white dark:bg-[#1e293b] border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 text-[11px] font-bold hover:bg-red-50 dark:hover:bg-slate-700 disabled:opacity-60"
                          >
                            {retrying === page.id ? 'Đang gửi...' : 'Dịch lại'}
                          </button>
                        )}
                        {(status === 'queued' || status === 'running') && (
                          <button onClick={() => openTranslated(page)} className="px-3 py-1 rounded-full bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-[11px] font-semibold hover:bg-slate-100 dark:hover:bg-slate-700">
                            Xem ảnh gốc
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              {timedOut && (
                <p className="text-[11px] text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900/50 rounded-xl p-2.5">
                  Đã chờ lâu mà ảnh vẫn chưa xử lý xong. Bộ xử lý ảnh có thể đang bận hoặc tạm dừng; bạn có thể quay lại sau, ảnh vẫn nằm trong hàng đợi.
                </p>
              )}
            </div>
          ) : (
            <>
              {/* Destination */}
              <div data-tour="upload-destination" className="grid grid-cols-2 gap-2 p-1 bg-slate-100 dark:bg-[#1e293b] rounded-2xl text-xs font-semibold">
                <button
                  onClick={() => { setDestination('quick'); setFiles([]); setProblems([]); }}
                  className={`py-2 rounded-xl transition-all ${destination === 'quick' ? 'bg-white dark:bg-slate-700 text-[#a43073] dark:text-pink-400 shadow-xs dark:shadow-none font-bold' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white'}`}
                >
                  Tải nhanh (ảnh lẻ)
                </button>
                <button
                  onClick={() => { setDestination('chapter'); setFiles([]); setProblems([]); }}
                  className={`py-2 rounded-xl transition-all ${destination === 'chapter' ? 'bg-white dark:bg-slate-700 text-[#a43073] dark:text-pink-400 shadow-xs dark:shadow-none font-bold' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white'}`}
                >
                  Vào chương truyện của tôi
                </button>
              </div>

              {destination === 'chapter' && (
                <div className="bg-slate-50 dark:bg-slate-800 p-3 rounded-2xl border border-slate-100 dark:border-slate-700 space-y-2">
                  {destinationError ? (
                    <p className="text-xs text-red-600 dark:text-red-400">{destinationError}</p>
                  ) : mineSeries.length === 0 ? (
                    <p className="text-xs text-slate-600 dark:text-slate-300">
                      Bạn chưa có truyện riêng nào.{' '}
                      <button onClick={() => { onClose(); onOpenManager(); }} className="font-bold text-[#a43073] dark:text-pink-400 hover:underline">
                        Tạo truyện mới
                      </button>
                    </p>
                  ) : (
                    <>
                      <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block" htmlFor="upload-series">Truyện</label>
                      <select
                        id="upload-series"
                        value={seriesId ?? ''}
                        onChange={event => setSeriesId(Number(event.target.value))}
                        className="w-full text-xs font-semibold text-slate-700 dark:text-slate-100 bg-white dark:bg-[#1e293b] p-2 rounded-xl border border-slate-200 dark:border-slate-700 outline-none"
                      >
                        {mineSeries.map(series => (
                          <option key={series.id} value={series.id}>{series.title_vi}</option>
                        ))}
                      </select>
                      <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block" htmlFor="upload-chapter">Chương</label>
                      {chapters.length === 0 ? (
                        <p className="text-xs text-slate-600 dark:text-slate-300">
                          Truyện này chưa có chương.{' '}
                          <button onClick={() => { onClose(); onOpenManager(); }} className="font-bold text-[#a43073] dark:text-pink-400 hover:underline">
                            Thêm chương
                          </button>
                        </p>
                      ) : (
                        <select
                          id="upload-chapter"
                          value={chapterId ?? ''}
                          onChange={event => setChapterId(Number(event.target.value))}
                          className="w-full text-xs font-semibold text-slate-700 dark:text-slate-100 bg-white dark:bg-[#1e293b] p-2 rounded-xl border border-slate-200 dark:border-slate-700 outline-none"
                        >
                          {chapters.map(chapter => (
                            <option key={chapter.id} value={chapter.id}>
                              Chương {formatChapterNumber(chapter.number)}{chapter.title ? ` · ${chapter.title}` : ''}
                            </option>
                          ))}
                        </select>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* File input dropzone */}
              <div
                data-tour="upload-dropzone"
                onDragOver={event => event.preventDefault()}
                onDrop={event => {
                  event.preventDefault();
                  acceptFiles(event.dataTransfer.files);
                }}
                className="border-2 border-dashed border-pink-300 dark:border-pink-900/60 hover:border-pink-500 dark:hover:border-pink-500 bg-pink-50/40 dark:bg-pink-900/10 hover:bg-pink-50/80 dark:hover:bg-pink-900/20 rounded-3xl p-6 text-center cursor-pointer transition-all"
              >
                <input
                  ref={inputRef}
                  type="file"
                  id="comic-file-modal-input"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  onChange={handleFileChange}
                  className="hidden"
                />
                <label htmlFor="comic-file-modal-input" className="cursor-pointer flex flex-col items-center">
                  <div className="w-14 h-14 rounded-2xl bg-white dark:bg-[#1e293b] shadow-soft dark:shadow-none flex items-center justify-center text-[#a43073] dark:text-pink-400 text-2xl mb-3 border border-pink-100 dark:border-slate-700">
                    <span className="material-symbols-outlined text-[32px]">image</span>
                  </div>
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">
                    {files.length > 0 ? (
                      <span className="text-[#a43073] dark:text-pink-400">
                        Đã chọn {files.length} ảnh: {files.map(file => file.name).join(', ')}
                      </span>
                    ) : (
                      <>Kéo thả ảnh manhua vào đây hoặc <span className="text-[#a43073] dark:text-pink-400 underline">bấm để duyệt tệp</span></>
                    )}
                  </span>
                  <span className="text-[11px] text-slate-400 dark:text-slate-500">
                    {destination === 'chapter'
                      ? `Hỗ trợ PNG, JPG, WEBP: tối đa ${MAX_CHAPTER_UPLOAD_FILES} ảnh mỗi lần, mỗi ảnh ≤ 10MB`
                      : 'Hỗ trợ định dạng PNG, JPG, WEBP dung lượng tối đa 10MB'}
                  </span>
                </label>
              </div>

              {/* Options */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 dark:bg-slate-800 p-3 rounded-2xl border border-slate-100 dark:border-slate-700">
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">Ngôn ngữ gốc</label>
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-100 bg-white dark:bg-[#1e293b] p-2 rounded-xl border border-slate-200 dark:border-slate-700">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    <span>Tiếng Trung (Giản thể)</span>
                  </div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800 p-3 rounded-2xl border border-slate-100 dark:border-slate-700">
                  <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">Dịch mục tiêu</label>
                  <div className="flex items-center gap-2 text-xs font-semibold text-[#a43073] dark:text-pink-400 bg-white dark:bg-[#1e293b] p-2 rounded-xl border border-pink-200 dark:border-pink-900/40">
                    <span className="w-2 h-2 rounded-full bg-pink-500"></span>
                    <span>Tiếng Việt + Pinyin</span>
                  </div>
                </div>
              </div>

              {/* AI OCR Description Callout */}
              <div data-tour="upload-callout" className="p-3.5 rounded-2xl bg-amber-50/80 dark:bg-amber-900/20 border border-amber-200/70 dark:border-amber-900/50 flex items-start gap-3">
                <span className="material-symbols-outlined text-amber-600 dark:text-amber-400 text-[20px] mt-0.5">
                  auto_awesome
                </span>
                <div>
                  <div className="text-xs font-bold text-amber-900 dark:text-amber-300">Tự động nhận diện bóng thoại AI</div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed">
                    Sau khi tải lên, ảnh được xếp hàng để hệ thống quét khung thoại, phiên âm Pinyin từng chữ và dịch. Thời gian chờ tùy số ảnh đang xử lý.
                  </div>
                </div>
              </div>

              {showDemo && (
                <div className="rounded-2xl border border-blue-100 dark:border-slate-700 bg-blue-50/50 dark:bg-blue-900/20 p-3 space-y-2">
                  <img src={DEMO_SAMPLE_IMAGE} alt="Trang quét mẫu" className="w-full max-h-52 object-cover object-top rounded-xl" />
                  <p className="text-[11px] text-blue-900 dark:text-blue-300">
                    Đây chỉ là ảnh minh họa (demo), không được tải lên hay dịch. Hãy chọn ảnh thật của bạn ở trên.
                  </p>
                </div>
              )}
            </>
          )}

          {problems.length > 0 && (
            <ul className="p-3 rounded-2xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 text-[11px] text-red-700 dark:text-red-400 space-y-1" role="alert">
              {problems.map(message => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-[#0f172a] border-t border-slate-100 dark:border-slate-700 flex items-center justify-between">
          {showingResults ? (
            <button
              onClick={() => { setRows([]); setProblems([]); }}
              className="text-xs font-semibold text-blue-700 dark:text-blue-300 hover:underline"
            >
              Tải thêm ảnh
            </button>
          ) : (
            <button
              onClick={() => setShowDemo(value => !value)}
              className="text-xs font-semibold text-blue-700 dark:text-blue-300 hover:underline"
            >
              {showDemo ? 'Ẩn trang quét mẫu' : 'Xem trang quét mẫu (demo)'}
            </button>
          )}

          <div className="flex items-center gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              {showingResults ? 'Đóng' : 'Hủy bỏ'}
            </button>
            {!showingResults && (
              <button
                data-tour="upload-submit"
                onClick={handleSubmit}
                disabled={uploading || files.length === 0}
                className="px-5 py-2 rounded-full text-xs font-bold text-white bg-gradient-to-r from-pink-500 to-[#a43073] hover:opacity-95 shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span>Đang tải lên...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">auto_fix_high</span>
                    <span>Tải lên & Dịch</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
