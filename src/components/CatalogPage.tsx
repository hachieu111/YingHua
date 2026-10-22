import React, { useState } from 'react';
import { ALL_COMICS } from '../data/mockData';
import { speakChinese } from '../utils/speech';

interface CatalogPageProps {
  onSelectComic: (comicId: string) => void;
  onNavigateToFlashcards: () => void;
}

export const CatalogPage: React.FC<CatalogPageProps> = ({
  onSelectComic,
  onNavigateToFlashcards
}) => {
  const [selectedHskFilter, setSelectedHskFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [dailyWordSaved, setDailyWordSaved] = useState<boolean>(false);

  const filterComics = (hskCategory: string) => {
    return ALL_COMICS.filter(comic => {
      const matchSearch =
        comic.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        comic.chineseTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
        comic.genre.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchSearch) return false;
      if (hskCategory === 'all') return true;
      if (hskCategory === 'hsk1-2') return comic.hskLevel.includes('HSK 1') || comic.hskLevel.includes('HSK 2');
      if (hskCategory === 'hsk3-4') return comic.hskLevel.includes('HSK 3') || comic.hskLevel.includes('HSK 4');
      if (hskCategory === 'hsk5-6') return comic.hskLevel.includes('HSK 5') || comic.hskLevel.includes('HSK 6');
      return true;
    });
  };

  const handlePlayWord = (text: string) => {
    speakChinese(text, 0.9);
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6">
      
      {/* HERO BANNER SECTION (Đấu La Đại Lục IV) */}
      <section className="relative overflow-hidden rounded-3xl bg-white p-6 sm:p-10 shadow-soft border border-pink-100 mb-10">
        <div className="absolute -top-24 -left-20 w-80 h-80 bg-pink-100/60 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-10 right-1/3 w-72 h-72 bg-blue-100/50 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          
          {/* Left Hero Content */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            
            {/* Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-semibold text-xs flex items-center gap-1 shadow-xs">
                <span>⭐</span> HSK 4 Chuẩn
              </span>
              <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-800 font-semibold text-xs flex items-center gap-1 shadow-xs">
                <span className="material-symbols-outlined text-[15px]">translate</span>
                Pinyin + Dịch Tương Tác
              </span>
              <span className="px-3 py-1 rounded-full bg-pink-100 text-[#a43073] font-semibold text-xs flex items-center gap-1 shadow-xs">
                <span className="material-symbols-outlined text-[15px]">record_voice_over</span>
                Giọng Đọc Bản Xứ
              </span>
            </div>

            {/* Title */}
            <div>
              <div className="text-sm font-['Noto_Serif_SC'] font-bold text-pink-600 mb-1 flex items-center gap-2">
                <span>斗罗大陆IV · 终极斗罗</span>
                <span className="px-2 py-0.5 rounded text-[11px] bg-pink-50 text-[#a43073] border border-pink-200">HSK 4+</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans']">
                Đấu La Đại Lục IV: <span className="text-[#a43073]">Chung Cực Đấu La</span>
              </h1>
            </div>

            <p className="text-sm text-slate-600 leading-relaxed max-w-xl">
              Cùng theo chân Lam Hiên Vũ khám phá thế giới hồn sư vị lai. Học hơn 650 từ vựng trình độ HSK 4 qua hội thoại trường học, gia đình và phiêu lưu thám hiểm sống động.
            </p>

            {/* Sample Dialogue Quote */}
            <div className="p-3.5 rounded-2xl bg-[#eff4ff] border border-blue-100 flex items-start gap-3">
              <span className="text-blue-500 font-serif text-2xl font-bold leading-none mt-1">“</span>
              <div>
                <div className="text-sm font-['Noto_Serif_SC'] font-bold text-slate-800 flex items-center gap-2">
                  <span>期末考试即将面临。</span>
                  <span className="text-xs font-mono text-blue-600 font-medium">Qīmò kǎoshì jíjiāng miànlín.</span>
                </div>
                <div className="text-xs text-slate-600 mt-0.5">
                  Kỳ thi cuối kỳ sắp sửa diễn ra rồi.
                </div>
              </div>
            </div>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={() => onSelectComic('douluo4')}
                className="px-6 py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs sm:text-sm flex items-center gap-2 shadow-md shadow-pink-300/30 hover:scale-105 transition-all"
              >
                <span className="material-symbols-outlined text-[18px]">menu_book</span>
                <span>Đọc tiếp Chương 12</span>
              </button>
              
              <button
                onClick={() => alert('Đã lưu vào bộ sưu tập cá nhân của bạn!')}
                className="px-5 py-2.5 rounded-full bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm border border-slate-200 flex items-center gap-2 shadow-xs transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">bookmark_add</span>
                <span>Lưu vào Thư viện</span>
              </button>

              <span className="text-xs font-semibold text-slate-500 flex items-center gap-1 ml-1">
                <span className="text-amber-500">★</span> 4.9 (3.2k đánh giá)
              </span>
            </div>

          </div>

          {/* Right Hero Comic Preview Card */}
          <div className="lg:col-span-5 flex justify-center">
            <div
              onClick={() => onSelectComic('douluo4')}
              className="relative w-full max-w-sm rounded-2xl overflow-hidden shadow-floating border-2 border-pink-200 cursor-pointer group hover:scale-[1.02] transition-all"
            >
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAV5EIXD1MStadtH5j20dMt5t_npUus3Hcgx86oRMMjJ7zfhe6qJfSrqY9WYqFCCat2jG2x7dfyjZdOrVL-e4UrurZRPY0nHuczNTm26TEIF-MCwwuhtRRzQsxE_M76KiyVcOVC-ppktHSGcRidMdTiFwdqtJ4_yi_ox_LtIz2cneg2Je5aVo8m9uLUDi_an98rwO2209UokA-8vfPFaWhnDvvpRpfvmnxFLnEreWnabIH0eyMOyBqh1quqmZt-vgTRxw"
                alt="Chung Cực Đấu La Preview"
                className="w-full h-auto block"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent flex items-end justify-between p-4 text-white">
                <div>
                  <span className="text-xs font-bold block">Chạm vào bóng thoại</span>
                  <span className="text-[10px] text-pink-200">Tra từ tức thì & nghe phát âm</span>
                </div>
                <span className="px-3 py-1 rounded-full bg-[#f472b6] text-white text-xs font-bold shadow-sm">
                  Thử ngay
                </span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ROADMAP HEADER: grouped title and search, distinct from catalog content */}
      <section className="mb-6 rounded-3xl border border-blue-100 bg-gradient-to-r from-white via-white to-[#eff4ff] p-5 sm:p-7 shadow-soft">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="min-w-0">
          <span className="text-xs font-bold uppercase tracking-wider text-[#a43073]">
            Phân loại trình độ
          </span>
          <h2 className="text-2xl sm:text-[28px] font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
            Lộ Trình Đọc Theo Cấp Độ HSK
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-slate-500">
            Tìm truyện phù hợp với trình độ và mục tiêu học tập của bạn.
          </p>
          </div>

          {/* Search inside catalog */}
          <div className="relative w-full md:w-[min(100%,22rem)] shrink-0">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-[20px]">
            search
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên truyện hoặc từ khóa..."
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-white text-slate-800 text-sm shadow-xs border border-blue-100 outline-none focus:ring-2 focus:ring-[#f472b6] focus:border-pink-200 transition-all placeholder:text-slate-400"
          />
          </div>
        </div>
      </section>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 mb-8 custom-scrollbar">
        <button
          onClick={() => setSelectedHskFilter('all')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
            selectedHskFilter === 'all'
              ? 'bg-[#a43073] text-white shadow-sm'
              : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          Tất cả trình độ ({ALL_COMICS.length})
        </button>
        <button
          onClick={() => setSelectedHskFilter('hsk1-2')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
            selectedHskFilter === 'hsk1-2'
              ? 'bg-[#a43073] text-white shadow-sm'
              : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          HSK 1 - 2: Nhập môn & Đời thường
        </button>
        <button
          onClick={() => setSelectedHskFilter('hsk3-4')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
            selectedHskFilter === 'hsk3-4'
              ? 'bg-[#a43073] text-white shadow-sm'
              : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-blue-500"></span>
          HSK 3 - 4: Sơ & Trung cấp
        </button>
        <button
          onClick={() => setSelectedHskFilter('hsk5-6')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
            selectedHskFilter === 'hsk5-6'
              ? 'bg-[#a43073] text-white shadow-sm'
              : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-pink-500"></span>
          HSK 5 - 6: Cổ trang & Tiên hiệp
        </button>
      </div>

      {/* MAIN TWO-COLUMN BODY: Catalog Left (8 cols), Widgets Right (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT COLUMN: LIST OF COMICS BY LEVEL (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-10">
          
          {/* SECTION: Tiếp tục đọc dở */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-pink-500">📖</span>
                <h3 className="text-lg font-bold text-slate-800">Tiếp Tục Đọc Dở</h3>
              </div>
              <span className="text-xs text-slate-400">Duy trì thói quen đọc 15 phút mỗi ngày</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Reading Card 1 */}
              <div className="bg-white p-3.5 rounded-2xl shadow-xs border border-pink-100 flex gap-3 hover:shadow-md transition-all">
                <img
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuAOydlzp-Y5DeGe1Y9AT-UivLYt5SIcK908IpjHPW3wvyDUPdHjSlqNaQFNhspUtNu7LyhJ1GpygAaDjOOlhaVBs6w6zvQzth0A9aq6uT_J5Qw5CxjraALsLeeGm2a9r3CV0OAbTGGw3HiL91n_nclRLe7E828EhWXYJcz-OEw7NVQBGHtv-tIAqS8gdxF5ipw7llonfGEqQPxiDYrYVx1VHra4hhZ7a9b7ct3bPukVKdpXJ8VHHfL_uWilOD7Dhgim7w"
                  alt="Chung Cực Đấu La"
                  className="w-20 h-28 object-cover rounded-xl shrink-0"
                />
                <div className="flex flex-col justify-between flex-1 min-w-0">
                  <div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 text-[10px] font-bold">
                        HSK 4
                      </span>
                      <span className="text-[10px] text-slate-400">Vừa đọc 2 giờ trước</span>
                    </div>
                    <h4 className="text-xs font-bold text-slate-800 truncate mt-1">
                      Chung Cực Đấu La: Buổi Thử Nghiệm
                    </h4>
                    <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                      "抓到我，我就让你亲一下。" Khám phá câu điều kiện.
                    </p>
                  </div>
                  <div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mb-1.5">
                      <div className="bg-[#a43073] h-full rounded-full" style={{ width: '78%' }}></div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400">24 từ mới đã lưu</span>
                      <button
                        onClick={() => onSelectComic('douluo4')}
                        className="px-3 py-1 rounded-full bg-[#f472b6] text-white text-[11px] font-bold hover:bg-[#a43073] transition-colors"
                      >
                        Đọc ngay
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Reading Card 2 */}
              <div className="bg-white p-3.5 rounded-2xl shadow-xs border border-pink-100 flex gap-3 hover:shadow-md transition-all">
                <img
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBHBgjH3-B4PFCw3Gpkbi17LDCGnvGScI5_cfVneCueK8TAje8e-OsxBv_UjJYDxqAty8YRlBOp-YVw5BIHPLUZLaz5jmE73ZmC3JRe6S_hiI1vYnaxFUl3MzhdQTEkiG_LM1zQWWCB2nJ6mlffoIH6TVmbuRkK_uKxI4386bbfDn-qP7xvHHmu-ot7RGsHpmG6uFNvK3T8JEw3XEIyb6Y16rN2NZWYX9Vo0J18gof14Ti0HfaprnAjUftyHOekd9rSYw"
                  alt="Nhật Ký Tiểu Hồ Ly"
                  className="w-20 h-28 object-cover rounded-xl shrink-0"
                />
                <div className="flex flex-col justify-between flex-1 min-w-0">
                  <div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] font-bold">
                        HSK 2
                      </span>
                      <span className="text-[10px] text-slate-400">Hôm qua</span>
                    </div>
                    <h4 className="text-xs font-bold text-slate-800 truncate mt-1">
                      Nhật Ký Tiểu Hồ Ly: Đi Mua Trà Sữa
                    </h4>
                    <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                      Luyện mẫu câu gọi món, chỉ lượng từ và thanh toán.
                    </p>
                  </div>
                  <div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mb-1.5">
                      <div className="bg-amber-500 h-full rounded-full" style={{ width: '45%' }}></div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400">12 từ mới đã lưu</span>
                      <button
                        onClick={() => onSelectComic('amthuctinhcau')}
                        className="px-3 py-1 rounded-full bg-[#f472b6] text-white text-[11px] font-bold hover:bg-[#a43073] transition-colors"
                      >
                        Đọc ngay
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION: Catalog Cards Grid */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-500"></span>
                <h3 className="text-lg font-bold text-slate-800">Danh Mục Truyện Phù Hợp Trình Độ</h3>
              </div>
              <span className="text-xs text-slate-500">100% kèm Pinyin & dịch tương tác</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {filterComics(selectedHskFilter).map((comic) => (
                <div
                  key={comic.id}
                  onClick={() => onSelectComic(comic.id)}
                  className="bg-white rounded-2xl p-4 shadow-xs border border-pink-100 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between group"
                >
                  <div>
                    <div className="relative w-full h-44 rounded-xl overflow-hidden mb-3 bg-slate-100">
                      <img
                        src={comic.coverImage}
                        alt={comic.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                      <span className="absolute top-2 left-2 px-2.5 py-0.5 rounded-full bg-white/90 backdrop-blur-md text-xs font-bold text-[#a43073] shadow-xs">
                        {comic.hskLevel}
                      </span>
                      <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-slate-900/75 backdrop-blur-md text-[10px] font-medium text-white">
                        {comic.totalChapters} Chương
                      </span>
                    </div>

                    <h4 className="font-bold text-sm text-slate-800 group-hover:text-[#a43073] transition-colors">
                      {comic.title}
                    </h4>
                    <span className="text-[11px] font-['Noto_Serif_SC'] text-pink-600 block mt-0.5">
                      {comic.chineseTitle} • {comic.author}
                    </span>
                    <p className="text-xs text-slate-500 line-clamp-2 mt-2 leading-relaxed">
                      {comic.description}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400 font-medium">
                      {comic.savedVocabCount} từ vựng
                    </span>
                    <span className="text-xs font-bold text-[#a43073] flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                      Khám phá <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* RIGHT SIDEBAR: Vocabulary of the Day & Study Tips (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Card: Từ vựng trong ngày */}
          <div className="bg-white rounded-3xl p-6 shadow-soft border border-pink-100 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                <span>💡</span> TỪ VỰNG TRONG NGÀY
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 font-bold text-xs">
                HSK 4
              </span>
            </div>

            <div className="bg-gradient-to-b from-[#eff4ff] to-white p-5 rounded-2xl border border-blue-100 text-center flex flex-col items-center">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-3xl font-extrabold text-slate-800 font-['Noto_Serif_SC']">
                  临近
                </span>
                <button
                  onClick={() => handlePlayWord('临近')}
                  className="w-8 h-8 rounded-full bg-white hover:bg-blue-100 text-blue-600 flex items-center justify-center shadow-xs transition-colors"
                  title="Nghe phát âm"
                >
                  <span className="material-symbols-outlined text-[18px]">volume_up</span>
                </button>
              </div>
              <span className="text-xs font-mono font-semibold text-blue-600">
                lín jìn
              </span>
              <div className="text-xs text-slate-600 font-medium mt-2">
                Đến gần · Cận kề (thời gian / địa điểm)
              </div>
            </div>

            <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100 leading-relaxed">
              <span className="font-semibold text-slate-800">Ví dụ trích từ manhua:</span><br />
              <span className="italic font-['Noto_Serif_SC'] font-medium">"期末考试即将<strong>临近</strong>。"</span> (Kỳ thi cuối kỳ sắp sửa kéo đến.)
            </div>

            <button
              onClick={() => {
                setDailyWordSaved(true);
                setTimeout(() => setDailyWordSaved(false), 2500);
              }}
              className={`w-full py-2.5 rounded-full text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-1.5 ${
                dailyWordSaved
                  ? 'bg-emerald-500 text-white'
                  : 'bg-gradient-to-r from-pink-500 to-rose-400 text-white hover:from-pink-600 hover:to-rose-500'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">
                {dailyWordSaved ? 'check' : 'bookmark_add'}
              </span>
              <span>{dailyWordSaved ? 'Đã lưu thành công!' : 'Thêm vào Sổ Từ Vựng Yinghua'}</span>
            </button>
          </div>

          {/* Card: Mẹo đọc manhua tăng phản xạ */}
          <div className="bg-white rounded-3xl p-6 shadow-soft border border-pink-100 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <span className="text-pink-500 font-bold">🌸</span>
              <h3 className="text-sm font-bold text-slate-800">Mẹo Đọc Manhua Tăng Phản Xạ</h3>
            </div>

            <div className="space-y-3 text-xs text-slate-600">
              <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50">
                <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  1
                </span>
                <div>
                  <strong className="text-slate-800 block">Đọc ngữ cảnh hình ảnh trước</strong>
                  Quan sát biểu cảm nhân vật để dự đoán ý nghĩa câu trước khi bật Pinyin.
                </div>
              </div>

              <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50">
                <span className="w-5 h-5 rounded-full bg-pink-100 text-pink-700 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  2
                </span>
                <div>
                  <strong className="text-slate-800 block">Nghe lặp lại (Shadowing)</strong>
                  Chạm vào icon loa ở mỗi khung tranh và lặp lại theo ngữ điệu nhân vật.
                </div>
              </div>

              <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50">
                <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 font-bold flex items-center justify-center shrink-0 text-[11px]">
                  3
                </span>
                <div>
                  <strong className="text-slate-800 block">Ôn lại 10 từ/ngày</strong>
                  Các từ đã lưu trong khi đọc truyện sẽ tự động chuyển vào bộ Flashcard SRS.
                </div>
              </div>
            </div>

            <button
              onClick={onNavigateToFlashcards}
              className="text-xs font-bold text-[#a43073] hover:underline flex items-center justify-center gap-1 pt-1"
            >
              <span>Mở bộ nhớ Flashcard Spaced-Repetition</span>
              <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </button>
          </div>

          {/* Streak Card */}
          <div className="p-4 rounded-3xl bg-gradient-to-r from-pink-50 to-amber-50 border border-pink-200/60 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔥</span>
              <div>
                <span className="text-xs font-bold text-slate-800 block">Chuỗi học tập</span>
                <span className="text-[11px] text-slate-500">7 ngày kiên trì liên tục!</span>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full bg-[#a43073] text-white font-bold text-xs shadow-xs">
              +50 XP
            </span>
          </div>

        </div>

      </div>

    </div>
  );
};
