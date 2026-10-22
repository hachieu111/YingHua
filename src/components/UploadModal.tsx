import React, { useState } from 'react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (imageSrc: string) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess
}) => {
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFileName(file.name);
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = event.target?.result as string;
        setIsProcessing(true);
        setTimeout(() => {
          setIsProcessing(false);
          onUploadSuccess(result);
          onClose();
        }, 1500);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDemoUpload = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      onUploadSuccess('https://lh3.googleusercontent.com/aida-public/AB6AXuBVsWOJghq30gbfhVWR5jlmhtSNvLHB-VswJral2VtbwsmZLOE5Fx0rBfNPh3YdFyEdwI4sYdh6G3RAU1QsY5lNUdgE5YfCjJFRJEnnYN2iI5ayZMDMdWadWQ9yS0aKVCjaRgJung8D2BAHRKintY0EUHWSAAoU9FNdEOSYHrMM7LUT5szykBJ-_hyCql_yd6kwo0rQqMaI_Xafc_WjPgqq7hSaKm3GFxwaeKyFTVxu4gahbAFapVcvgG9ro4Ntj5Q34A');
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-lg rounded-3xl shadow-floating border border-pink-100 overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 bg-gradient-to-r from-pink-50/70 via-white to-pink-50/40">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-pink-100 flex items-center justify-center text-[#a43073] text-sm">
              <span className="material-symbols-outlined text-[20px]">cloud_upload</span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">Tải ảnh Manhua cần dịch</h3>
              <p className="text-[11px] text-slate-400 font-medium">
                Tự động nhận dạng ký tự tiếng Trung & dịch sang Tiếng Việt
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          
          {/* File input dropzone */}
          <div className="border-2 border-dashed border-pink-300 hover:border-pink-500 bg-pink-50/40 hover:bg-pink-50/80 rounded-3xl p-6 text-center cursor-pointer transition-all">
            <input
              type="file"
              id="comic-file-modal-input"
              accept="image/*"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="comic-file-modal-input" className="cursor-pointer flex flex-col items-center">
              <div className="w-14 h-14 rounded-2xl bg-white shadow-soft flex items-center justify-center text-[#a43073] text-2xl mb-3 border border-pink-100">
                <span className="material-symbols-outlined text-[32px]">image</span>
              </div>
              <span className="text-xs font-bold text-slate-700 mb-1">
                {selectedFileName ? (
                  <span className="text-[#a43073]">Đã chọn: {selectedFileName}</span>
                ) : (
                  <>Kéo thả ảnh manhua vào đây hoặc <span className="text-[#a43073] underline">bấm để duyệt tệp</span></>
                )}
              </span>
              <span className="text-[11px] text-slate-400">
                Hỗ trợ định dạng PNG, JPG, WEBP dung lượng tối đa 15MB
              </span>
            </label>
          </div>

          {/* Options */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100">
              <label className="text-[11px] font-bold text-slate-500 block mb-1">Ngôn ngữ gốc</label>
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 bg-white p-2 rounded-xl border border-slate-200">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                <span>Tiếng Trung (Giản thể)</span>
              </div>
            </div>

            <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100">
              <label className="text-[11px] font-bold text-slate-500 block mb-1">Dịch mục tiêu</label>
              <div className="flex items-center gap-2 text-xs font-semibold text-[#a43073] bg-white p-2 rounded-xl border border-pink-200">
                <span className="w-2 h-2 rounded-full bg-pink-500"></span>
                <span>Tiếng Việt + Pinyin</span>
              </div>
            </div>
          </div>

          {/* AI OCR Description Callout */}
          <div className="p-3.5 rounded-2xl bg-amber-50/80 border border-amber-200/70 flex items-start gap-3">
            <span className="material-symbols-outlined text-amber-600 text-[20px] mt-0.5">
              auto_awesome
            </span>
            <div>
              <div className="text-xs font-bold text-amber-900">Tự động nhận diện bóng thoại AI</div>
              <div className="text-[11px] text-slate-600 mt-0.5 leading-relaxed">
                Hệ thống sẽ quét khung thoại, phiên âm Pinyin từng chữ, giải thích ngữ pháp và tạo thẻ từ vựng tương tác tức thì.
              </div>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={handleDemoUpload}
            className="text-xs font-semibold text-blue-700 hover:underline"
          >
            Sử dụng trang quét mẫu
          </button>

          <div className="flex items-center gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
            >
              Hủy bỏ
            </button>
            <button
              onClick={handleDemoUpload}
              disabled={isProcessing}
              className="px-5 py-2 rounded-full text-xs font-bold text-white bg-gradient-to-r from-pink-500 to-[#a43073] hover:opacity-95 shadow-md transition-all flex items-center gap-1.5"
            >
              {isProcessing ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Đang phân tích...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[16px]">auto_fix_high</span>
                  <span>Tải lên & Phân tích</span>
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
