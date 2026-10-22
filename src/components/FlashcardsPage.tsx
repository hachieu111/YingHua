import React, { useState, useEffect } from 'react';
import { VOCABULARY_LIST, FLASHCARD_DECKS } from '../data/mockData';
import { VocabularyItem } from '../types';
import { speakChinese } from '../utils/speech';

interface FlashcardsPageProps {
  onNavigateToReader: () => void;
}

export const FlashcardsPage: React.FC<FlashcardsPageProps> = ({ onNavigateToReader }) => {
  const [vocabList, setVocabList] = useState<VocabularyItem[]>(VOCABULARY_LIST);
  const [currentCardIndex, setCurrentCardIndex] = useState<number>(0);
  const [isFlipped, setIsFlipped] = useState<boolean>(false);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedHskFilter, setSelectedHskFilter] = useState<number | 'all'>('all');
  const [selectedDeckId, setSelectedDeckId] = useState<string>('all');
  const [srsFeedbackMsg, setSrsFeedbackMsg] = useState<string | null>(null);

  const currentCard = vocabList[currentCardIndex] || vocabList[0];

  // Flip on Space key and SRS rating on keys 1-4
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsFlipped(prev => !prev);
      } else if (e.key === '1') {
        handleSrsRate('needs_review', '< 10 phút');
      } else if (e.key === '2') {
        handleSrsRate('reviewing', '1 ngày');
      } else if (e.key === '3') {
        handleSrsRate('reviewing', '3 ngày');
      } else if (e.key === '4') {
        handleSrsRate('mastered', '7 ngày');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [vocabList, currentCardIndex]);

  const handlePlayAudio = (text: string) => {
    speakChinese(text, 0.85);
  };

  const handleSrsRate = (newStatus: 'mastered' | 'reviewing' | 'needs_review', duration: string) => {
    setSrsFeedbackMsg(`Đã xếp lịch ôn tập sau: ${duration}!`);
    setTimeout(() => setSrsFeedbackMsg(null), 1800);

    // Update status in list
    setVocabList(prev => prev.map((item, idx) => {
      if (idx === currentCardIndex) {
        return { ...item, status: newStatus };
      }
      return item;
    }));

    // Auto flip back and advance to next card
    setTimeout(() => {
      setIsFlipped(false);
      setCurrentCardIndex(prev => (prev + 1) % vocabList.length);
    }, 250);
  };

  const toggleStar = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setVocabList(prev => prev.map(item => {
      if (item.id === id) {
        return { ...item, isStarred: !item.isStarred };
      }
      return item;
    }));
  };

  const deleteVocab = (id: string) => {
    setVocabList(prev => prev.filter(item => item.id !== id));
  };

  const filteredVocab = vocabList.filter(item => {
    const matchSearch =
      item.hanzi.toLowerCase().includes(searchFilter.toLowerCase()) ||
      item.pinyin.toLowerCase().includes(searchFilter.toLowerCase()) ||
      item.vietnamese.toLowerCase().includes(searchFilter.toLowerCase());

    const matchStatus = statusFilter === 'all' || item.status === statusFilter;
    const matchHsk = selectedHskFilter === 'all' || item.hskLevel === selectedHskFilter;

    return matchSearch && matchStatus && matchHsk;
  });

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6 flex flex-col gap-10">
      
      {/* TOP PROGRESS & SUMMARY BENTO */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Overall Goal Panel (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 shadow-soft border border-pink-100 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full bg-pink-100/50 blur-2xl pointer-events-none"></div>
          <div className="absolute right-1/3 bottom-0 w-32 h-32 rounded-full bg-blue-100/40 blur-xl pointer-events-none"></div>

          <div className="flex flex-col gap-2 relative z-10">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] font-bold text-xs shadow-xs">
                <span>🌸</span> SRS Spaced Repetition Hệ Thống
              </span>
              <span className="text-xs text-slate-500 font-medium">Cập nhật hôm nay: 18 từ mới</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight font-['Plus_Jakarta_Sans']">
              Từ Vựng & Flashcard Theo Manhua
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 max-w-xl leading-relaxed">
              Tập trung học sâu từ vựng bản xứ trích xuất trực tiếp qua từng khung tranh truyện. Ôn tập đúng nhịp độ khoa học, biến kiến thức thụ động thành phản xạ giao tiếp tự nhiên.
            </p>
          </div>

          {/* Progress Metrics */}
          <div className="mt-6 pt-4 flex flex-col gap-3 relative z-10">
            <div className="flex items-baseline justify-between">
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-[#a43073] font-['Plus_Jakarta_Sans']">
                  486
                </span>
                <span className="text-xs text-slate-500 font-semibold">tổng từ vựng tích lũy</span>
              </div>
              <span className="text-xs text-[#0060ac] font-bold bg-blue-100 px-3 py-1 rounded-full">
                66% Hoàn thành mục tiêu tháng
              </span>
            </div>

            {/* Segmented Multi-Color Bar */}
            <div className="w-full h-3 rounded-full bg-slate-100 flex overflow-hidden p-0.5">
              <div className="h-full bg-[#a43073] rounded-full" style={{ width: '65.8%' }} title="Đã thuộc: 320"></div>
              <div className="h-full bg-[#64a8fe] rounded-full mx-0.5" style={{ width: '26.3%' }} title="Đang ôn: 128"></div>
              <div className="h-full bg-amber-400 rounded-full" style={{ width: '7.9%' }} title="Cần xem lại: 38"></div>
            </div>

            {/* Legend Badges */}
            <div className="grid grid-cols-3 gap-3 pt-1">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#a43073]"></span>
                <div className="flex flex-col">
                  <span className="text-xs text-slate-800 font-bold">320 từ</span>
                  <span className="text-[10px] text-slate-500">Đã thuộc vững</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#64a8fe]"></span>
                <div className="flex flex-col">
                  <span className="text-xs text-slate-800 font-bold">128 từ</span>
                  <span className="text-[10px] text-slate-500">Đang ôn tập</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                <div className="flex flex-col">
                  <span className="text-xs text-slate-800 font-bold">38 từ</span>
                  <span className="text-[10px] text-slate-500">Cần xem lại</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Streak & Quick Action (5 cols) */}
        <div className="lg:col-span-5 bg-gradient-to-br from-[#eff4ff] to-white rounded-3xl p-6 sm:p-8 shadow-soft border border-pink-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-bold text-[#a43073] uppercase tracking-wider">
                Hôm Nay Cần Học
              </span>
              <div className="text-2xl font-bold text-slate-800 mt-1">24 Từ Cần Lặp Lại</div>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-pink-100 flex items-center justify-center text-[#a43073] shadow-xs">
              <span className="material-symbols-outlined text-[26px]">psychology</span>
            </div>
          </div>

          <div className="my-4 p-3.5 bg-white rounded-2xl shadow-xs border border-pink-100/60 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center text-blue-700">
              <span className="material-symbols-outlined text-[22px]">auto_stories</span>
            </div>
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-xs font-bold text-slate-800 truncate">
                Khánh Dư Niên (Chương 14)
              </span>
              <span className="text-[11px] text-slate-500">Có 6 từ mới đã đánh dấu lúc đọc</span>
            </div>
            <button
              onClick={onNavigateToReader}
              className="text-xs font-bold text-[#a43073] hover:underline"
            >
              Xem
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setCurrentCardIndex(0);
                setIsFlipped(false);
              }}
              className="flex-1 py-3 px-4 bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs sm:text-sm rounded-full shadow-md transition-all flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">play_circle</span>
              <span>Ôn Tập Ngay (24 từ)</span>
            </button>
            <button
              onClick={() => {
                const shuffled = [...vocabList].sort(() => Math.random() - 0.5);
                setVocabList(shuffled);
                setCurrentCardIndex(0);
                setIsFlipped(false);
              }}
              className="w-11 h-11 rounded-full bg-white hover:bg-slate-100 text-slate-600 flex items-center justify-center shadow-xs border border-slate-200 transition-colors"
              title="Xáo trộn thứ tự từ"
            >
              <span className="material-symbols-outlined text-[20px]">shuffle</span>
            </button>
          </div>
        </div>

      </div>

      {/* MAIN INTERACTIVE 3D FLASHCARD VIEWER */}
      <div className="w-full flex flex-col items-center gap-6">
        
        {/* Header bar of 3D room */}
        <div className="w-full flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-6 bg-[#a43073] rounded-full"></span>
            <h3 className="text-xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
              Phòng Luyện Flashcard 3D
            </h3>
            <span className="text-xs bg-slate-100 px-3 py-1 rounded-full text-slate-600 font-bold">
              Thẻ {currentCardIndex + 1} / {vocabList.length}
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-500 text-xs bg-white px-4 py-2 rounded-full shadow-xs border border-pink-100">
            <span className="material-symbols-outlined text-[16px] text-[#a43073]">keyboard</span>
            <span>
              Mẹo: Nhấn <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-800 font-bold font-mono text-[10px]">Space</kbd> để lật thẻ, phím <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-800 font-bold font-mono text-[10px]">1-4</kbd> để đánh giá
            </span>
          </div>
        </div>

        {srsFeedbackMsg && (
          <div className="px-4 py-1.5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs animate-bounce shadow-xs">
            {srsFeedbackMsg}
          </div>
        )}

        {/* 3D Card Stage */}
        <div className="w-full max-w-3xl flex flex-col items-center">
          
          <div
            onClick={() => setIsFlipped(!isFlipped)}
            className="w-full min-h-[420px] cursor-pointer select-none perspective-1200"
          >
            <div
              className={`relative w-full h-full min-h-[420px] transition-transform duration-500 rounded-3xl shadow-floating transform-style-3d ${
                isFlipped ? 'rotate-y-180' : ''
              }`}
            >
              
              {/* FRONT FACE */}
              <div className="absolute inset-0 w-full h-full rounded-3xl bg-white p-8 flex flex-col justify-between backface-hidden border-2 border-pink-100 shadow-soft">
                {/* Front Top Bar */}
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-bold text-xs flex items-center gap-1">
                      <span>⭐</span> HSK {currentCard.hskLevel}
                    </span>
                    <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-900 font-semibold text-xs">
                      {currentCard.status === 'mastered' ? 'Đã thuộc' : currentCard.status === 'needs_review' ? 'Cần ôn lại' : 'Đang học'}
                    </span>
                  </div>

                  <button
                    onClick={(e) => toggleStar(currentCard.id, e)}
                    className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                      currentCard.isStarred ? 'bg-amber-100 text-amber-500' : 'bg-slate-100 text-slate-400 hover:text-amber-500'
                    }`}
                    title="Đánh dấu sao"
                  >
                    <span className="material-symbols-outlined text-[20px]">
                      {currentCard.isStarred ? 'star' : 'star_border'}
                    </span>
                  </button>
                </div>

                {/* Front Center Hanzi & Pinyin */}
                <div className="flex flex-col items-center text-center my-auto">
                  <div className="text-xl font-bold text-[#0060ac] tracking-wide mb-1 flex items-center gap-2">
                    <span>{currentCard.pinyin}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePlayAudio(currentCard.hanzi);
                      }}
                      className="w-8 h-8 rounded-full bg-blue-100 hover:bg-blue-200 text-blue-700 flex items-center justify-center shadow-xs transition-transform hover:scale-110"
                      title="Phát âm chuẩn"
                    >
                      <span className="material-symbols-outlined text-[18px]">volume_up</span>
                    </button>
                  </div>

                  <h2 className="text-6xl sm:text-7xl font-extrabold text-slate-800 tracking-normal font-['Noto_Serif_SC'] my-3">
                    {currentCard.hanzi}
                  </h2>

                  <span className="text-xs text-slate-500 mt-2 px-3.5 py-1 rounded-full bg-slate-100 font-medium">
                    Âm Hán Việt: <strong className="text-slate-800">{currentCard.sinoVietnamese}</strong>
                  </span>
                </div>

                {/* Front Bottom Prompt */}
                <div className="flex items-center justify-between w-full pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-1.5 text-slate-500 text-xs">
                    <span className="material-symbols-outlined text-[#a43073] text-[18px]">auto_stories</span>
                    <span>Xuất hiện ở: <strong>{currentCard.comicSource}</strong></span>
                  </div>
                  <span className="text-xs font-bold text-[#a43073] flex items-center gap-1 animate-pulse">
                    <span>Chạm để lật mặt sau</span>
                    <span className="material-symbols-outlined text-[18px]">sync</span>
                  </span>
                </div>
              </div>

              {/* BACK FACE */}
              <div className="absolute inset-0 w-full h-full rounded-3xl bg-gradient-to-b from-white to-[#eff4ff] p-8 flex flex-col justify-between backface-hidden rotate-y-180 border-2 border-pink-200 shadow-soft">
                {/* Back Top */}
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-[#a43073] font-['Noto_Serif_SC']">
                      {currentCard.hanzi}
                    </span>
                    <span className="text-base text-blue-600 font-semibold font-mono">
                      ({currentCard.pinyin})
                    </span>
                  </div>
                  <span className="text-xs px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] font-bold">
                    Ý nghĩa & Ngữ cảnh
                  </span>
                </div>

                {/* Back Center Meaning & Context Quote */}
                <div className="flex flex-col gap-4 my-auto">
                  <div className="p-4 rounded-2xl bg-white shadow-xs border border-pink-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Định nghĩa tiếng Việt
                    </span>
                    <span className="text-base font-bold text-slate-800 leading-snug">
                      {currentCard.vietnamese}
                    </span>
                  </div>

                  {/* Context sentence */}
                  {currentCard.exampleSentence && (
                    <div className="p-4 rounded-2xl bg-[#ffd8e7]/30 border border-pink-200 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#a43073] flex items-center gap-1">
                          <span className="material-symbols-outlined text-[16px]">menu_book</span>
                          Câu thoại gốc trong Manhua
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePlayAudio(currentCard.exampleSentence?.hanzi || '');
                          }}
                          className="text-blue-700 hover:text-blue-900 flex items-center gap-1 text-[11px] font-bold"
                        >
                          <span className="material-symbols-outlined text-[16px]">volume_up</span>
                          Nghe câu
                        </button>
                      </div>

                      <p className="text-sm font-['Noto_Serif_SC'] font-bold text-slate-800 mt-0.5">
                        "{currentCard.exampleSentence.hanzi}"
                      </p>
                      <p className="text-xs text-blue-600 font-mono">
                        "{currentCard.exampleSentence.pinyin}"
                      </p>
                      <p className="text-xs text-slate-600 italic">
                        "{currentCard.exampleSentence.vietnamese}"
                      </p>
                    </div>
                  )}
                </div>

                {/* Back Footer */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onNavigateToReader();
                    }}
                    className="inline-flex items-center gap-1 text-xs font-bold text-[#0060ac] hover:underline"
                  >
                    <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                    <span>Xem lại trang truyện gốc nơi từ xuất hiện</span>
                  </button>
                  <span className="text-xs text-slate-400 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px]">touch_app</span>
                    Chạm để quay lại mặt trước
                  </span>
                </div>
              </div>

            </div>
          </div>

          {/* SRS RATING CONTROLS (Chưa nhớ, Khó, Tốt, Dễ) */}
          <div className="w-full mt-6 flex flex-col gap-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full">
              
              {/* Rating 1 */}
              <button
                onClick={() => handleSrsRate('needs_review', '< 10 phút')}
                className="flex flex-col items-center justify-center p-3 rounded-2xl bg-white hover:bg-rose-50 text-slate-800 hover:text-rose-700 shadow-xs hover:shadow-md border border-slate-200 transition-all text-center group"
              >
                <span className="text-xs text-rose-600 font-bold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-rose-500"></span> Chưa nhớ
                </span>
                <span className="text-sm font-bold mt-1">Lặp lại ngay</span>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5">&lt; 10 phút (Phím 1)</span>
              </button>

              {/* Rating 2 */}
              <button
                onClick={() => handleSrsRate('reviewing', '1 ngày')}
                className="flex flex-col items-center justify-center p-3 rounded-2xl bg-white hover:bg-amber-50 text-slate-800 hover:text-amber-800 shadow-xs hover:shadow-md border border-slate-200 transition-all text-center group"
              >
                <span className="text-xs text-amber-600 font-bold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span> Khó
                </span>
                <span className="text-sm font-bold mt-1">Cần củng cố</span>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5">1 ngày (Phím 2)</span>
              </button>

              {/* Rating 3 */}
              <button
                onClick={() => handleSrsRate('reviewing', '3 ngày')}
                className="flex flex-col items-center justify-center p-3 rounded-2xl bg-white hover:bg-blue-50 text-slate-800 hover:text-blue-800 shadow-xs hover:shadow-md border border-slate-200 transition-all text-center group"
              >
                <span className="text-xs text-blue-600 font-bold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span> Tốt
                </span>
                <span className="text-sm font-bold mt-1">Nhớ rõ</span>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5">3 ngày (Phím 3)</span>
              </button>

              {/* Rating 4 */}
              <button
                onClick={() => handleSrsRate('mastered', '7 ngày')}
                className="flex flex-col items-center justify-center p-3 rounded-2xl bg-white hover:bg-pink-50 text-slate-800 hover:text-[#a43073] shadow-xs hover:shadow-md border border-slate-200 transition-all text-center group"
              >
                <span className="text-xs text-[#a43073] font-bold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#a43073]"></span> Dễ
                </span>
                <span className="text-sm font-bold mt-1">Đã thuộc lòng</span>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5">7 ngày (Phím 4)</span>
              </button>

            </div>

            {/* Navigation buttons */}
            <div className="flex items-center justify-between px-2 pt-1">
              <button
                onClick={() => {
                  setCurrentCardIndex(prev => (prev > 0 ? prev - 1 : vocabList.length - 1));
                  setIsFlipped(false);
                }}
                className="flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900 py-1.5 px-3 rounded-full hover:bg-slate-100 transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                <span>Thẻ trước</span>
              </button>

              <button
                onClick={() => setIsFlipped(prev => !prev)}
                className="flex items-center gap-1.5 text-xs font-bold text-[#a43073] bg-[#ffd8e7]/60 hover:bg-[#ffd8e7] py-2 px-5 rounded-full transition-colors shadow-xs"
              >
                <span className="material-symbols-outlined text-[18px]">sync</span>
                <span>Lật thẻ (Space)</span>
              </button>

              <button
                onClick={() => {
                  setCurrentCardIndex(prev => (prev + 1) % vocabList.length);
                  setIsFlipped(false);
                }}
                className="flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900 py-1.5 px-3 rounded-full hover:bg-slate-100 transition-colors"
              >
                <span>Thẻ sau</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </button>
            </div>
          </div>

        </div>

      </div>

      {/* FLASHCARD DECKS / CATEGORIES GRID */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <span className="text-xs font-bold text-[#a43073] uppercase tracking-wider">
              Thư Viện Bộ Thẻ
            </span>
            <h3 className="text-2xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
              Chọn Bộ Flashcard Để Ôn Tập
            </h3>
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-full text-xs font-semibold">
            <button
              onClick={() => setSelectedDeckId('all')}
              className={`px-3.5 py-1.5 rounded-full transition-all ${
                selectedDeckId === 'all' ? 'bg-[#a43073] text-white shadow-xs' : 'text-slate-600'
              }`}
            >
              Tất cả
            </button>
            <button
              onClick={() => setSelectedDeckId('series')}
              className={`px-3.5 py-1.5 rounded-full transition-all ${
                selectedDeckId === 'series' ? 'bg-[#a43073] text-white shadow-xs' : 'text-slate-600'
              }`}
            >
              Theo Bộ Truyện
            </button>
            <button
              onClick={() => setSelectedDeckId('starred')}
              className={`px-3.5 py-1.5 rounded-full transition-all ${
                selectedDeckId === 'starred' ? 'bg-[#a43073] text-white shadow-xs' : 'text-slate-600'
              }`}
            >
              Yêu Thích ⭐
            </button>
          </div>
        </div>

        {/* Decks Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {FLASHCARD_DECKS.map((deck) => (
            <div
              key={deck.id}
              onClick={() => {
                alert(`Đang mở bộ Flashcard: ${deck.title}`);
              }}
              className="bg-white rounded-2xl p-4 shadow-xs border border-pink-100 hover:shadow-md transition-all flex flex-col justify-between cursor-pointer group"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${deck.badgeColor}`}>
                    {deck.badge}
                  </span>
                  <span className="text-xs font-bold text-slate-500">
                    {deck.vocabCount} từ vựng
                  </span>
                </div>

                <h4 className="text-sm font-bold text-slate-800 group-hover:text-[#a43073] transition-colors">
                  {deck.title}
                </h4>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                  {deck.description}
                </p>
                {deck.keyWords && (
                  <span className="text-[11px] font-['Noto_Serif_SC'] text-pink-600 block mt-2">
                    Từ trọng tâm: {deck.keyWords}
                  </span>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <div className="w-24 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[#a43073] h-full rounded-full"
                    style={{ width: `${Math.round((deck.reviewedCount / deck.vocabCount) * 100)}%` }}
                  ></div>
                </div>
                <span className="text-xs font-bold text-[#a43073]">
                  Ôn {deck.reviewedCount}/{deck.vocabCount}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* HSK LEVEL CHIP SELECTOR */}
      <div className="p-6 rounded-3xl bg-[#eff4ff] flex flex-col md:flex-row items-center justify-between gap-4 border border-blue-100 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-amber-200 text-amber-900 flex items-center justify-center font-bold text-sm shrink-0">
            HSK
          </div>
          <div>
            <div className="text-sm font-bold text-slate-800">
              Luyện Flashcard theo Cấp Độ Chuẩn HSK 3.0
            </div>
            <div className="text-xs text-slate-500">
              Lọc nhanh các từ xuất hiện trong Manhua phù hợp với trình độ thi cử của bạn
            </div>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          {[1, 2, 3, 4, 5, 6].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setSelectedHskFilter(selectedHskFilter === lvl ? 'all' : lvl)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                selectedHskFilter === lvl
                  ? 'bg-[#a43073] text-white shadow-xs'
                  : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200/60'
              }`}
            >
              HSK {lvl} {lvl === 4 && '🔥'}
            </button>
          ))}
          <button
            onClick={() => setSelectedHskFilter('all')}
            className={`px-3 py-1.5 rounded-full text-xs font-bold ${
              selectedHskFilter === 'all' ? 'bg-[#0060ac] text-white' : 'bg-white text-slate-600'
            }`}
          >
            Tất cả
          </button>
        </div>
      </div>

      {/* DETAILED VOCABULARY DATA TABLE */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-soft border border-pink-100 flex flex-col gap-4">
        
        {/* Table Header Controls */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2">
          <div>
            <h3 className="text-xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
              Danh Sách Chi Tiết Từ Vựng Đã Lưu
            </h3>
            <span className="text-xs text-slate-500">
              Tổng cộng {filteredVocab.length} từ đã đánh dấu từ các chương truyện Manhua
            </span>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <span className="material-symbols-outlined absolute left-3 top-2.5 text-slate-400 text-[18px]">
                search
              </span>
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Tìm Hán tự, Pinyin, nghĩa..."
                className="w-full pl-9 pr-3 py-1.5 rounded-full bg-slate-50 text-slate-800 text-xs border border-slate-200 outline-none focus:ring-2 focus:ring-[#f472b6] transition-all"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 outline-none cursor-pointer"
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="mastered">Thuộc vững</option>
              <option value="reviewing">Đang ôn</option>
              <option value="needs_review">Cần xem lại</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto w-full custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#eff4ff] text-slate-600 text-xs font-bold rounded-xl">
                <th className="py-3 px-4 rounded-l-xl">Hán Tự & Pinyin</th>
                <th className="py-3 px-4">Âm Hán Việt</th>
                <th className="py-3 px-4">Nghĩa Tiếng Việt</th>
                <th className="py-3 px-4">Cấp HSK</th>
                <th className="py-3 px-4">Nguồn Truyện</th>
                <th className="py-3 px-4">Trạng Thái</th>
                <th className="py-3 px-4 text-right rounded-r-xl">Thao Tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredVocab.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handlePlayAudio(item.hanzi)}
                        className="text-[#a43073] hover:scale-110 transition-transform"
                        title="Phát âm"
                      >
                        <span className="material-symbols-outlined text-[18px]">volume_up</span>
                      </button>
                      <div className="flex flex-col">
                        <span className="text-base font-bold text-slate-800 font-['Noto_Serif_SC']">
                          {item.hanzi}
                        </span>
                        <span className="font-mono text-blue-600 text-[11px]">
                          {item.pinyin}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-700">
                    {item.sinoVietnamese}
                  </td>
                  <td className="py-3.5 px-4 text-slate-600 font-medium">
                    {item.vietnamese}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[11px] font-bold">
                      HSK {item.hskLevel}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <button
                      onClick={onNavigateToReader}
                      className="text-blue-700 hover:underline flex items-center gap-1 font-medium"
                    >
                      {item.comicSource}
                    </button>
                  </td>
                  <td className="py-3.5 px-4">
                    {item.status === 'mastered' ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#ffd8e7] text-[#a43073] font-bold text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#a43073]"></span> Thuộc vững
                      </span>
                    ) : item.status === 'reviewing' ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 font-bold text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span> Đang ôn
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span> Cần xem lại
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={(e) => toggleStar(item.id, e)}
                        className={`p-1 rounded-full ${item.isStarred ? 'text-amber-500' : 'text-slate-400 hover:text-amber-500'}`}
                        title="Đánh dấu sao"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          {item.isStarred ? 'star' : 'star_border'}
                        </span>
                      </button>
                      <button
                        onClick={() => deleteVocab(item.id)}
                        className="p-1 rounded-full text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                        title="Xóa từ"
                      >
                        <span className="material-symbols-outlined text-[18px]">delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>

    </div>
  );
};
