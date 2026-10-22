import React, { useState } from 'react';
import { ALL_COMICS } from '../data/mockData';

interface LibraryPageProps {
  onOpenUpload: () => void;
  onSelectComic: (comicId: string) => void;
  onNavigateToFlashcards: () => void;
}

export const LibraryPage: React.FC<LibraryPageProps> = ({
  onOpenUpload,
  onSelectComic,
  onNavigateToFlashcards
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'reading' | 'favorites' | 'completed' | 'uploads'>('all');
  const [viewStyle, setViewStyle] = useState<'grid' | 'list'>('grid');
  const [sortOption, setSortOption] = useState<string>('recent');

  const filteredComics = ALL_COMICS.filter(comic => {
    if (activeTab === 'all') return true;
    if (activeTab === 'reading') return comic.status === 'reading';
    if (activeTab === 'favorites') return comic.isFavorite;
    if (activeTab === 'completed') return comic.status === 'completed';
    if (activeTab === 'uploads') return comic.id === 'amthuctinhcau' || comic.id === 'caphemuaha';
    return true;
  });

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-10">
      
      {/* HERO HEADER & STATS BENTO */}
      <section className="relative overflow-hidden rounded-3xl bg-[#eff4ff] p-6 sm:p-10 shadow-soft border border-pink-100">
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-pink-100/50 blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full bg-blue-100/50 blur-3xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex flex-col max-w-2xl">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] font-bold text-xs tracking-wide flex items-center gap-1 shadow-xs">
                🌸 KHÔNG GIAN HỌC TẬP CÁ NHÂN
              </span>
              <span className="text-slate-500 text-xs hidden sm:inline">HSK 1 - HSK 4</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans']">
              Thư Viện Học Tập Của Bạn
            </h1>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Mỗi trang truyện là một bước tiến mới. Khám phá kho manhua có chú âm Pinyin, tích lũy từ vựng tự nhiên và tiếp tục hành trình chinh phục tiếng Trung hôm nay!
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={onOpenUpload}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-pink-500 to-rose-400 text-white font-bold text-xs sm:text-sm shadow-md shadow-pink-300/30 hover:scale-105 transition-all"
            >
              <span className="material-symbols-outlined text-[18px]">add_photo_alternate</span>
              <span>+ Tải lên trang truyện mới</span>
            </button>
          </div>
        </div>

        {/* Quick Stats Metrics Bento */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 bg-white/90 backdrop-blur-md rounded-2xl p-4 shadow-sm border border-pink-100/60">
          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-pink-100 flex items-center justify-center text-[#a43073]">
              <span className="material-symbols-outlined text-[24px]">collections_bookmark</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">12</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Bộ truyện đã lưu</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center text-[#0060ac]">
              <span className="material-symbols-outlined text-[24px]">auto_stories</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">03</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Bộ đang đọc dở</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center text-amber-800">
              <span className="material-symbols-outlined text-[24px]">style</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">486</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Từ vựng đã lưu</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-2">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-700">
              <span className="material-symbols-outlined text-[24px]">task_alt</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold text-slate-800 leading-none">04</span>
              <span className="text-xs text-slate-500 mt-1 font-medium">Bộ đã hoàn thành</span>
            </div>
          </div>
        </div>
      </section>

      {/* FILTER & SORT CONTROLS */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        
        {/* Tabs Filter */}
        <div className="flex items-center gap-1 overflow-x-auto p-1 bg-[#eff4ff] rounded-full custom-scrollbar">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'all'
                ? 'bg-[#f472b6] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Tất cả (12)
          </button>
          <button
            onClick={() => setActiveTab('reading')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'reading'
                ? 'bg-[#f472b6] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Đang đọc dở (3)
          </button>
          <button
            onClick={() => setActiveTab('favorites')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'favorites'
                ? 'bg-[#f472b6] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Yêu thích (5)
          </button>
          <button
            onClick={() => setActiveTab('completed')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'completed'
                ? 'bg-[#f472b6] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Đã xong (4)
          </button>
          <button
            onClick={() => setActiveTab('uploads')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'uploads'
                ? 'bg-[#f472b6] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Tải lên của tôi (2)
          </button>
        </div>

        {/* Sort & Grid/List View Controls */}
        <div className="flex items-center gap-3 self-end md:self-auto">
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full shadow-xs border border-pink-100">
            <span className="material-symbols-outlined text-[16px] text-slate-400">sort</span>
            <label className="text-xs text-slate-500" htmlFor="library-sort">
              Sắp xếp:
            </label>
            <select
              id="library-sort"
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-700 outline-none cursor-pointer"
            >
              <option value="recent">Gần đây nhất</option>
              <option value="hsk">HSK tăng dần</option>
              <option value="progress">Tiến độ cao nhất</option>
            </select>
          </div>

          <div className="hidden sm:flex items-center bg-white p-1 rounded-full shadow-xs border border-pink-100">
            <button
              onClick={() => setViewStyle('grid')}
              className={`p-1 rounded-full transition-colors ${
                viewStyle === 'grid' ? 'bg-pink-100 text-[#a43073]' : 'text-slate-400 hover:text-slate-700'
              }`}
              title="Dạng lưới"
            >
              <span className="material-symbols-outlined text-[18px]">grid_view</span>
            </button>
            <button
              onClick={() => setViewStyle('list')}
              className={`p-1 rounded-full transition-colors ${
                viewStyle === 'list' ? 'bg-pink-100 text-[#a43073]' : 'text-slate-400 hover:text-slate-700'
              }`}
              title="Dạng danh sách"
            >
              <span className="material-symbols-outlined text-[18px]">view_list</span>
            </button>
          </div>
        </div>

      </div>

      {/* READING LIST COMIC CARDS */}
      <div className={viewStyle === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'flex flex-col gap-4'}>
        {filteredComics.map((comic) => (
          <div
            key={comic.id}
            className="group relative flex flex-col rounded-2xl bg-white p-4 shadow-soft border border-pink-100 hover:shadow-md transition-all duration-300"
          >
            {/* Card Cover */}
            <div className="relative w-full h-52 rounded-xl overflow-hidden bg-slate-100">
              <img
                src={comic.coverImage}
                alt={comic.title}
                className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
                <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 text-xs font-bold shadow-xs">
                  {comic.hskLevel}
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-900 text-xs font-medium shadow-xs">
                  {comic.genre}
                </span>
              </div>
              <button
                className="absolute top-2.5 right-2.5 w-8 h-8 rounded-full bg-white/85 backdrop-blur-md text-[#a43073] hover:bg-white flex items-center justify-center shadow-xs transition-transform hover:scale-110"
                title="Yêu thích"
              >
                <span className="material-symbols-outlined text-[18px]">favorite</span>
              </button>
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-900/85 via-slate-900/30 to-transparent p-3 flex items-end justify-between">
                <span className="text-white text-xs font-bold flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">menu_book</span>
                  Trang {comic.currentPage}/{comic.totalPages} ({comic.progressPercent}%)
                </span>
                <span className="text-white/90 text-[11px]">
                  {comic.status === 'completed' ? 'Đã đọc xong' : 'Đọc gần đây'}
                </span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
              <div
                className={`h-full rounded-full ${comic.status === 'completed' ? 'bg-emerald-500' : 'bg-[#a43073]'}`}
                style={{ width: `${comic.progressPercent}%` }}
              ></div>
            </div>

            {/* Card Info */}
            <div className="flex flex-col mt-3 flex-1 justify-between">
              <div>
                <h3 className="font-bold text-base text-slate-800 group-hover:text-[#a43073] transition-colors">
                  {comic.title} ({comic.chineseTitle})
                </h3>
                <p className="text-xs text-slate-500 line-clamp-2 mt-1 leading-relaxed">
                  {comic.description}
                </p>
              </div>

              {/* Vocab Tag */}
              <div className="flex items-center gap-3 mt-3 py-1.5 px-3 rounded-xl bg-slate-50">
                <div className="flex items-center gap-1 text-[#a43073] text-xs font-bold">
                  <span className="material-symbols-outlined text-[15px]">translate</span>
                  <span>{comic.savedVocabCount} từ</span> đã lưu
                </div>
                <div className="text-slate-500 text-[11px] truncate">
                  {comic.currentChapterTitle}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2.5 mt-4 pt-1">
                <button
                  onClick={() => onSelectComic(comic.id)}
                  className="flex items-center justify-center gap-1 py-2 px-3 rounded-full bg-[#a43073] text-white text-xs font-bold shadow-xs hover:bg-[#85145a] transition-all"
                >
                  <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                  <span>{comic.status === 'completed' ? 'Đọc lại' : 'Đọc tiếp'}</span>
                </button>
                <button
                  onClick={onNavigateToFlashcards}
                  className="flex items-center justify-center gap-1 py-2 px-3 rounded-full bg-blue-100 text-blue-900 text-xs font-bold hover:bg-blue-200 transition-all"
                >
                  <span className="material-symbols-outlined text-[16px]">style</span>
                  <span>Ôn thẻ ({comic.savedVocabCount})</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* SECTION: UPLOADED MANHUA & OCR AI TRANSLATION WORKSPACE */}
      <section className="flex flex-col gap-4 mt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-2xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
                Trang Ảnh Bạn Đã Tải Lên Dịch
              </h2>
              <span className="px-2.5 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-xs font-bold">
                OCR AI
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 max-w-2xl">
              Tự do chụp hoặc tải lên bất kỳ trang manhua Trung Quốc nào từ Pinterest, Weibo. Hệ thống tự động nhận diện chữ Hán, phiên âm Pinyin và dịch tiếng Việt tức thì.
            </p>
          </div>

          <button
            onClick={onOpenUpload}
            className="flex items-center gap-2 self-start sm:self-auto px-4 py-2 rounded-full bg-white text-[#a43073] text-xs font-bold shadow-xs border border-pink-100 hover:bg-pink-50 transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">cloud_upload</span>
            <span>Tải file ảnh (.jpg, .png)</span>
          </button>
        </div>

        {/* Uploads Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* Item 1 */}
          <div className="group relative rounded-2xl bg-white p-3 shadow-xs border border-pink-100 hover:shadow-md transition-all flex flex-col">
            <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-slate-100">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBVsWOJghq30gbfhVWR5jlmhtSNvLHB-VswJral2VtbwsmZLOE5Fx0rBfNPh3YdFyEdwI4sYdh6G3RAU1QsY5lNUdgE5YfCjJFRJEnnYN2iI5ayZMDMdWadWQ9yS0aKVCjaRgJung8D2BAHRKintY0EUHWSAAoU9FNdEOSYHrMM7LUT5szykBJ-_hyCql_yd6kwo0rQqMaI_Xafc_WjPgqq7hSaKm3GFxwaeKyFTVxu4gahbAFapVcvgG9ro4Ntj5Q34A"
                alt="OCR Scan Trang Ẩm Thực"
                className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-300"
              />
              <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-slate-900/75 backdrop-blur-md text-white text-[10px] font-semibold">
                12 hội thoại OCR
              </span>
              <div className="absolute inset-0 bg-[#a43073]/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <button
                  onClick={() => onSelectComic('amthuctinhcau')}
                  className="px-4 py-1.5 rounded-full bg-white text-[#a43073] font-bold text-xs shadow-md flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[16px]">visibility</span>
                  <span>Mở bản dịch</span>
                </button>
              </div>
            </div>
            <div className="flex flex-col mt-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-800 truncate">
                  Bản quét: Thưởng thức thịt kho
                </span>
                <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                  HSK 2
                </span>
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5">
                Đã dịch xong • 8 từ vựng mới
              </span>
            </div>
          </div>

          {/* Item 2 */}
          <div className="group relative rounded-2xl bg-white p-3 shadow-xs border border-pink-100 hover:shadow-md transition-all flex flex-col">
            <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-slate-100">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpEfpMUl2HLlCeYZ6XHfSbF6L1u6DHcdWAcXb7vIZxzhSjkvBeYvs9_P2FJeDHssQAejpk5ITbW15sIw-Ry7Zc74Vq-IF3_o4wdjrojekeTu3mMrJ4LZFQMKGhLsBsbftoX9oHtHCxHGX4slF6zYzALqBOEMdjqgN9KOzzES2z413nEDByDKhZn0ykEdnti8rLaLzuvawjemhluI348p98syiJVFM-s__jgi2uHjNM1jbOfmdp1F3e8N617GpCAS_vCw"
                alt="OCR Scan Võ Lâm"
                className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-300"
              />
              <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-slate-900/75 backdrop-blur-md text-white text-[10px] font-semibold">
                19 hội thoại OCR
              </span>
              <div className="absolute inset-0 bg-[#a43073]/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <button
                  onClick={() => onSelectComic('douluo4')}
                  className="px-4 py-1.5 rounded-full bg-white text-[#a43073] font-bold text-xs shadow-md flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[16px]">visibility</span>
                  <span>Mở bản dịch</span>
                </button>
              </div>
            </div>
            <div className="flex flex-col mt-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-800 truncate">
                  Trang 03: Võ hiệp hội ngộ
                </span>
                <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                  HSK 3
                </span>
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5">
                Đã dịch xong • 14 từ vựng mới
              </span>
            </div>
          </div>

          {/* Item 3 */}
          <div className="group relative rounded-2xl bg-white p-3 shadow-xs border border-pink-100 hover:shadow-md transition-all flex flex-col">
            <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-slate-100">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDCPWA75LC_4twqpkc6tqvqpDEHI718UtBlrKcDD9H1djly6h4Un1boesSdeJOu9dCA74qkHahUcGROBhcXNzTdLSduo2_c9bdqlOseMsiFOsKPHZg0Me-CmYKuNKLxT6PHI8FJNvxPl4hF8InYonEQ59M0viElKqittho4FAYglKc-RlZR_WsAOs9r2g2nxaXkaRquSo1ZZedUSm7GngAecVr2zh8K_sVNKvJce5BsWfmBNWiUpHne"
                alt="OCR Scan Góc phố hoa anh đào"
                className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-300"
              />
              <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-slate-900/75 backdrop-blur-md text-white text-[10px] font-semibold">
                7 hội thoại OCR
              </span>
              <div className="absolute inset-0 bg-[#a43073]/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <button
                  onClick={() => onSelectComic('caphemuaha')}
                  className="px-4 py-1.5 rounded-full bg-white text-[#a43073] font-bold text-xs shadow-md flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[16px]">visibility</span>
                  <span>Mở bản dịch</span>
                </button>
              </div>
            </div>
            <div className="flex flex-col mt-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-800 truncate">
                  Góc phố hoa anh đào
                </span>
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                  HSK 1
                </span>
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5">
                Đã dịch xong • 5 từ vựng mới
              </span>
            </div>
          </div>

          {/* Item 4: Dropzone Box */}
          <div
            onClick={onOpenUpload}
            className="group relative rounded-2xl bg-[#eff4ff] p-5 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-[#dce9ff] transition-all border-2 border-dashed border-pink-200"
          >
            <div className="w-14 h-14 rounded-2xl bg-white shadow-xs flex items-center justify-center text-[#a43073] group-hover:scale-110 transition-transform mb-2">
              <span className="material-symbols-outlined text-[28px]">add_photo_alternate</span>
            </div>
            <span className="font-bold text-sm text-slate-800">Thêm ảnh trang mới</span>
            <p className="text-[11px] text-slate-500 mt-1 max-w-[180px]">
              Kéo thả hoặc bấm để tải lên ảnh manhua cần dịch
            </p>
            <span className="mt-3 px-2.5 py-0.5 rounded-full bg-white text-slate-500 text-[10px] font-medium border border-slate-200">
              PNG, JPG tối đa 15MB
            </span>
          </div>

        </div>
      </section>

      {/* READING HABIT & WEEKLY GOAL WIDGET */}
      <section className="rounded-3xl bg-gradient-to-r from-white via-[#eff4ff] to-white p-6 sm:p-8 shadow-soft border border-pink-100 flex flex-col lg:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          
          {/* Circular Progress Ring */}
          <div className="relative w-20 h-20 shrink-0 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-slate-200"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="3.5"
              />
              <path
                className="text-[#a43073]"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeDasharray="75, 100"
                strokeLinecap="round"
                strokeWidth="3.5"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-sm font-extrabold text-slate-800 leading-none">75%</span>
              <span className="text-[9px] text-slate-500 font-medium">Mục tiêu</span>
            </div>
          </div>

          <div className="flex flex-col">
            <h3 className="text-base sm:text-lg font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
              Mục Tiêu Đọc Tuần Này: 3 / 4 Chương Manhua
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Bạn đã ôn tập 85 từ vựng mới trong tuần qua! Hãy hoàn thành 1 chương nữa để nhận huy hiệu "Mọt Truyện Siêng Năng" 🌸
            </p>
          </div>
        </div>

        <button
          onClick={onNavigateToFlashcards}
          className="shrink-0 px-6 py-2.5 rounded-full bg-[#0060ac] hover:bg-[#004883] text-white font-bold text-xs sm:text-sm shadow-md transition-all flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-[18px]">school</span>
          <span>Vào phòng ôn tập từ vựng</span>
        </button>
      </section>

    </div>
  );
};
