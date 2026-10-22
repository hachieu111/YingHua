import React, { useEffect, useRef, useState } from 'react';
import { Bookmark, BookmarkCheck, Eraser, Highlighter, Palette, PenLine } from 'lucide-react';
import { COMIC_PAGES } from '../data/mockData';
import { VocabularyItem } from '../types';
import { speakChinese } from '../utils/speech';

interface ComicReaderProps {
  onOpenUpload: () => void;
  onSaveVocab?: (word: VocabularyItem) => void;
}

export const ComicReader: React.FC<ComicReaderProps> = ({ onOpenUpload, onSaveVocab }) => {
  const [savedWords, setSavedWords] = useState<string[]>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('yinghua-reader-flashcards') || '[]') as VocabularyItem[];
      return saved.map(item => item.hanzi);
    } catch {
      return [];
    }
  });
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0);
  const [viewMode, setViewMode] = useState<'bubble' | 'study'>('bubble');
  const [overlaysVisible, setOverlaysVisible] = useState<boolean>(true);
  const [speechRate, setSpeechRate] = useState<number>(1.0);
  const [fontSizeOffset, setFontSizeOffset] = useState<number>(0);
  const [isPlayingFullPage, setIsPlayingFullPage] = useState<boolean>(false);
  const [activeBubbleId, setActiveBubbleId] = useState<string | null>(null);
  const [savedSuccessMsg, setSavedSuccessMsg] = useState<string | null>(null);
  const [isStudyMenuOpen, setIsStudyMenuOpen] = useState(false);
  const [annotationTool, setAnnotationTool] = useState<'none' | 'highlight' | 'draw'>('none');
  const [annotationColor, setAnnotationColor] = useState('#f472b6');
  const [pageHighlights, setPageHighlights] = useState<Record<string, string>>(() => {
    try {
      return JSON.parse(localStorage.getItem('yinghua-reader-highlights') || '{}') as Record<string, string>;
    } catch {
      return {};
    }
  });
  const [pageStrokes, setPageStrokes] = useState<Record<string, { color: string; points: { x: number; y: number }[] }[]>>(() => {
    try {
      return JSON.parse(localStorage.getItem('yinghua-reader-strokes') || '{}') as Record<string, { color: string; points: { x: number; y: number }[] }[]>;
    } catch {
      return {};
    }
  });
  const [isDrawing, setIsDrawing] = useState(false);
  const [savedPages, setSavedPages] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('yinghua-reader-saved-pages') || '[]') as string[];
    } catch {
      return [];
    }
  });
  const drawingPointerId = useRef<number | null>(null);

  const activePage = COMIC_PAGES[currentPageIndex] || COMIC_PAGES[0];

  useEffect(() => {
    try {
      localStorage.setItem('yinghua-reader-highlights', JSON.stringify(pageHighlights));
    } catch {
      // Annotations remain usable for the current session when storage is unavailable.
    }
  }, [pageHighlights]);

  useEffect(() => {
    try {
      localStorage.setItem('yinghua-reader-strokes', JSON.stringify(pageStrokes));
    } catch {
      // Annotations remain usable for the current session when storage is unavailable.
    }
  }, [pageStrokes]);

  const handlePlayVoice = (text: string) => {
    speakChinese(text, speechRate);
  };

  const handleReadEntirePage = async () => {
    if (isPlayingFullPage) return;
    setIsPlayingFullPage(true);
    const fullText = activePage.bubbles.map(b => b.hanzi).join(' ');
    await speakChinese(fullText, speechRate);
    setIsPlayingFullPage(false);
  };

  const saveVocabulary = (vocab: typeof activePage.vocabulary[number]) => {
    onSaveVocab?.({
      id: `reader-${activePage.id}-${vocab.hanzi}`,
      hanzi: vocab.hanzi,
      pinyin: vocab.pinyin,
      sinoVietnamese: vocab.hanzi,
      vietnamese: vocab.vietnamese,
      hskLevel: 3,
      comicSource: `Đấu La Đại Lục IV · Trang ${activePage.pageNumber}`,
      status: 'needs_review',
      isStarred: false
    });
    setSavedWords(current => current.includes(vocab.hanzi) ? current : [...current, vocab.hanzi]);
    setSavedSuccessMsg(`Đã lưu “${vocab.hanzi}” vào bộ Flashcard của bạn.`);
    setTimeout(() => setSavedSuccessMsg(null), 3000);
  };

  const handleSaveAllVocab = () => {
    activePage.vocabulary.forEach(saveVocabulary);
    setSavedSuccessMsg(`Đã thêm ${activePage.vocabulary.length} từ của trang này vào Flashcard!`);
    setTimeout(() => setSavedSuccessMsg(null), 3000);
  };

  const toggleSavePage = () => {
    const isSaved = savedPages.includes(activePage.id);
    const updatedPages = isSaved ? savedPages.filter(id => id !== activePage.id) : [...savedPages, activePage.id];
    setSavedPages(updatedPages);
    try {
      localStorage.setItem('yinghua-reader-saved-pages', JSON.stringify(updatedPages));
    } catch {
      // Saving remains available for this session if browser storage is disabled.
    }
    setSavedSuccessMsg(isSaved ? 'Đã bỏ lưu trang truyện.' : 'Đã lưu trang truyện vào thư viện đọc.');
    setTimeout(() => setSavedSuccessMsg(null), 3000);
  };

  const handleBubbleAnnotation = (bubbleId: string) => {
    if (annotationTool !== 'highlight') return;
    setPageHighlights(current => {
      const next = { ...current };
      if (next[bubbleId]) delete next[bubbleId];
      else next[bubbleId] = annotationColor;
      return next;
    });
  };

  const getDrawingPoint = (event: React.PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1000, ((event.clientX - rect.left) / rect.width) * 1000)),
      y: Math.max(0, Math.min(1000, ((event.clientY - rect.top) / rect.height) * 1000))
    };
  };

  const startDrawing = (event: React.PointerEvent<SVGSVGElement>) => {
    if (annotationTool !== 'draw') return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    drawingPointerId.current = event.pointerId;
    setIsDrawing(true);
    const pageId = activePage.id;
    const point = getDrawingPoint(event);
    setPageStrokes(current => ({
      ...current,
      [pageId]: [...(current[pageId] || []), { color: annotationColor, points: [point] }]
    }));
  };

  const continueDrawing = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!isDrawing || drawingPointerId.current !== event.pointerId) return;
    const pageId = activePage.id;
    const point = getDrawingPoint(event);
    setPageStrokes(current => {
      const strokes = [...(current[pageId] || [])];
      const lastStroke = strokes[strokes.length - 1];
      if (!lastStroke) return current;
      strokes[strokes.length - 1] = { ...lastStroke, points: [...lastStroke.points, point] };
      return { ...current, [pageId]: strokes };
    });
  };

  const stopDrawing = (event: React.PointerEvent<SVGSVGElement>) => {
    if (drawingPointerId.current !== event.pointerId) return;
    drawingPointerId.current = null;
    setIsDrawing(false);
  };

  const clearAnnotations = () => {
    setPageHighlights(current => {
      const next = { ...current };
      activePage.bubbles.forEach(bubble => delete next[bubble.id]);
      return next;
    });
    setPageStrokes(current => ({ ...current, [activePage.id]: [] }));
  };

  const studyToolsMenu = isStudyMenuOpen ? (
    <div className="mt-2 w-64 max-h-[min(70vh,34rem)] overflow-y-auto rounded-2xl border border-blue-100 bg-white/95 p-3 shadow-xl backdrop-blur">
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
        <div>
          <h3 className="text-xs font-extrabold text-slate-800">Công cụ học tập</h3>
          <p className="text-[10px] text-slate-500">Từ vựng và ghi chú trang truyện</p>
        </div>
        <button onClick={toggleSavePage} className="inline-flex shrink-0 items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1.5 text-[10px] font-bold text-blue-700 hover:bg-blue-100">
          {savedPages.includes(activePage.id) ? <BookmarkCheck size={13}/> : <Bookmark size={13}/>}
          {savedPages.includes(activePage.id) ? 'Đã lưu trang' : 'Lưu trang'}
        </button>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold text-slate-600">Từ vựng · {activePage.vocabulary.length}</span>
        <button onClick={handleSaveAllVocab} className="inline-flex items-center gap-1 rounded-full bg-pink-50 px-2.5 py-1.5 text-[10px] font-bold text-[#a43073] hover:bg-pink-100">
          <span className="material-symbols-outlined text-[13px]">style</span>Lưu tất cả
        </button>
      </div>
      <div className="mt-2 space-y-1.5">
        {activePage.vocabulary.map(vocab => (
          <div key={vocab.hanzi} className="flex items-center justify-between gap-2 rounded-xl bg-slate-50 px-2.5 py-2">
            <div className="min-w-0">
              <span className="font-['Noto_Serif_SC'] text-sm font-bold text-slate-800">{vocab.hanzi}</span>
              <span className="ml-2 text-[10px] text-slate-500">{vocab.pinyin}</span>
              <div className="truncate text-[10px] text-slate-500">{vocab.vietnamese}</div>
            </div>
            <button onClick={() => saveVocabulary(vocab)} disabled={savedWords.includes(vocab.hanzi)} className="shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold disabled:bg-emerald-50 disabled:text-emerald-700 enabled:bg-white enabled:text-blue-700 enabled:hover:bg-blue-100">
              {savedWords.includes(vocab.hanzi) ? 'Đã lưu' : '+ Flashcard'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-3 border-t border-slate-100 pt-3">
        <div className="mb-2 text-[10px] font-bold text-slate-600">Bút ghi chú</div>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => setAnnotationTool(annotationTool === 'highlight' ? 'none' : 'highlight')} className={`flex items-center justify-center gap-1.5 rounded-xl px-2 py-2 text-[10px] font-bold ${annotationTool === 'highlight' ? 'bg-pink-500 text-white' : 'bg-pink-50 text-pink-700'}`}><Highlighter size={14}/>Tô nền thoại</button>
          <button onClick={() => setAnnotationTool(annotationTool === 'draw' ? 'none' : 'draw')} className={`flex items-center justify-center gap-1.5 rounded-xl px-2 py-2 text-[10px] font-bold ${annotationTool === 'draw' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700'}`}><PenLine size={14}/>Bút vẽ</button>
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-600"><Palette size={13}/>Màu bút</span>
          <label className="relative h-7 w-7 cursor-pointer overflow-hidden rounded-full border-2 border-white shadow ring-1 ring-slate-200" style={{ backgroundColor: annotationColor }} title="Chọn màu tùy chỉnh">
            <input type="color" value={annotationColor} onChange={event => setAnnotationColor(event.target.value)} aria-label="Chọn màu tùy chỉnh" className="absolute inset-0 h-full w-full cursor-pointer opacity-0" />
          </label>
        </div>
        <div className="mt-2 flex items-center gap-2">
          {['#f472b6', '#facc15', '#4ade80', '#38bdf8', '#a78bfa', '#fb7185', '#1e293b'].map(color => <button key={color} onClick={() => setAnnotationColor(color)} aria-label={`Chọn màu ${color}`} aria-pressed={annotationColor === color} className={`h-6 w-6 rounded-full border-2 ${annotationColor === color ? 'border-slate-700 ring-2 ring-slate-200' : 'border-white shadow'}`} style={{ backgroundColor: color }} />)}
        </div>
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-[9px] text-slate-400">{annotationTool === 'highlight' ? 'Chạm khung thoại để tô màu' : annotationTool === 'draw' ? 'Vẽ trực tiếp lên ảnh truyện' : 'Chọn loại bút để bắt đầu'}</span>
          <button onClick={clearAnnotations} className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-[9px] font-semibold text-slate-500 hover:bg-slate-100"><Eraser size={12}/>Xóa ghi chú</button>
        </div>
      </div>
    </div>
  ) : null;

  const cycleSpeed = () => {
    if (speechRate === 1.0) setSpeechRate(1.2);
    else if (speechRate === 1.2) setSpeechRate(0.8);
    else setSpeechRate(1.0);
  };

  const changeFontSize = (delta: number) => {
    setFontSizeOffset(prev => Math.max(-2, Math.min(4, prev + delta)));
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-6">
      
      {/* CHAPTER & SUB-NAV BAR */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6 bg-white/80 backdrop-blur-md p-3.5 px-6 rounded-2xl border border-pink-100 shadow-sm">
        
        {/* Breadcrumb / Title */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentPageIndex(prev => (prev > 0 ? prev - 1 : COMIC_PAGES.length - 1))}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-[#a43073] hover:bg-pink-50 transition-colors"
            title="Trang trước"
          >
            <span className="material-symbols-outlined text-[20px]">chevron_left</span>
          </button>
          
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-bold text-slate-800">
              Đấu La Đại Lục IV: Chung Cực Đấu La
            </span>
            <span className="text-slate-300 hidden sm:inline">|</span>
            <span className="text-xs text-[#a43073] font-semibold bg-pink-50 px-2.5 py-0.5 rounded-md border border-pink-200/50">
              Chương 12 · Trang {activePage.pageNumber}/18
            </span>
          </div>

          <button
            onClick={() => setCurrentPageIndex(prev => (prev < COMIC_PAGES.length - 1 ? prev + 1 : 0))}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-[#a43073] hover:bg-pink-50 transition-colors"
            title="Trang kế tiếp"
          >
            <span className="material-symbols-outlined text-[20px]">chevron_right</span>
          </button>
        </div>

        {/* View Mode & Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-gradient-to-r from-pink-500 to-rose-400 text-white shadow-xs hover:shadow-md hover:from-pink-600 hover:to-rose-500 text-xs font-semibold transition-all"
          >
            <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
            <span>Tải ảnh dịch</span>
          </button>

          {/* Overlay control */}
          <div className="flex items-center bg-slate-100 p-1 rounded-2xl border border-slate-200/60 text-xs font-medium">
            <button
              onClick={() => setViewMode('bubble')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl transition-all ${
                viewMode === 'bubble'
                  ? 'bg-white text-[#a43073] shadow-xs font-bold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <span className="material-symbols-outlined text-[16px] text-pink-400">chat_bubble</span>
              <span>Bóng Thoại (Overlay)</span>
            </button>
          </div>

          <button
            onClick={toggleSavePage}
            className="w-9 h-9 rounded-xl bg-white border border-pink-100 text-slate-500 hover:text-[#a43073] hover:border-pink-300 flex items-center justify-center shadow-xs transition-all"
            title={savedPages.includes(activePage.id) ? 'Bỏ lưu trang này' : 'Lưu trang này'}
          >
            {savedPages.includes(activePage.id) ? <BookmarkCheck size={18} className="text-[#a43073]"/> : <Bookmark size={18}/>}
          </button>
        </div>

      </div>

      {savedSuccessMsg && (
        <div className="mb-4 p-3 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold flex items-center gap-2 animate-bounce">
          <span className="material-symbols-outlined text-[18px] text-emerald-600">check_circle</span>
          <span>{savedSuccessMsg}</span>
        </div>
      )}

      {/* MAIN LAYOUT GRID (2 cols sidebar, 7 cols canvas, 3 cols study panel) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pb-28">
        
        {/* LEFT THUMBNAILS SIDEBAR (2 Cols) */}
        <aside className="hidden lg:flex flex-col gap-3 lg:col-span-2 sticky top-24">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Trang truyện
            </span>
            <span className="text-[11px] font-semibold text-[#a43073] bg-pink-50 px-2 py-0.5 rounded-full">
              4 trang mẫu
            </span>
          </div>

          <div className="space-y-3 custom-scrollbar max-h-[70vh] overflow-y-auto pr-1">
            
            {/* Upload Action Tile */}
            <div
              onClick={onOpenUpload}
              className="group relative rounded-2xl border-2 border-dashed border-pink-300 hover:border-pink-500 bg-pink-50/50 hover:bg-pink-100/60 p-3 flex flex-col items-center justify-center text-center cursor-pointer transition-all shadow-xs"
            >
              <div className="w-8 h-8 rounded-xl bg-white shadow-xs flex items-center justify-center text-pink-500 group-hover:scale-110 group-hover:bg-pink-500 group-hover:text-white transition-all mb-1">
                <span className="material-symbols-outlined text-[18px]">add_photo_alternate</span>
              </div>
              <span className="text-xs font-bold text-pink-600">+ Tải ảnh mới</span>
              <span className="text-[10px] text-slate-400 mt-0.5">PNG, JPG, WebP</span>
            </div>

            {/* List of Pages */}
            {COMIC_PAGES.map((page, idx) => {
              const isSelected = idx === currentPageIndex;
              return (
                <div
                  key={page.id}
                  onClick={() => setCurrentPageIndex(idx)}
                  className={`group relative rounded-2xl overflow-hidden cursor-pointer transition-all bg-white ${
                    isSelected
                      ? 'border-2 border-pink-400 shadow-md ring-4 ring-pink-100/70'
                      : 'border-2 border-transparent hover:border-pink-200 shadow-xs hover:shadow-md'
                  }`}
                >
                  <img
                    src={page.imageSrc}
                    alt={page.title}
                    className={`w-full h-28 object-cover object-top transition-opacity ${
                      isSelected ? 'opacity-100' : 'opacity-80 group-hover:opacity-100'
                    }`}
                  />
                  <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-900/85 to-transparent p-2 flex items-center justify-between text-white">
                    <span className="text-[11px] font-bold">
                      Trang 0{page.pageNumber}
                    </span>
                    <span className="text-[10px] bg-pink-500/90 px-1.5 py-0.5 rounded text-white font-medium">
                      {page.bubbles.length} thoại
                    </span>
                  </div>
                </div>
              );
            })}

          </div>

          {/* Quick Learning Tip */}
          <div className="mt-2 p-3 rounded-2xl bg-amber-50 border border-amber-200/70 text-slate-700 shadow-xs">
            <div className="flex items-center gap-1.5 text-amber-700 font-bold text-xs mb-1">
              <span className="material-symbols-outlined text-[16px]">lightbulb</span>
              <span>Mẹo học nhanh:</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Rê chuột vào các khung phát sáng <span className="inline-block w-2 h-2 rounded-full bg-pink-400 align-middle"></span> trên ảnh để xem Pinyin, nghĩa tiếng Việt và bấm nghe phát âm nhé!
            </p>
          </div>
        </aside>

        {/* CENTRAL MANHUA CANVAS (7 Cols) */}
        <section className="col-span-1 lg:col-span-7 flex flex-col items-center">
          <div className="relative w-full max-w-2xl bg-white p-3 sm:p-4 rounded-3xl shadow-soft border border-pink-100 transition-all">
            
            {/* Status Pill Top Right */}
            <div className="absolute top-6 right-6 z-20 flex items-center gap-2 bg-white/95 backdrop-blur-md px-3 py-1 rounded-full shadow-md border border-pink-100 text-xs font-semibold text-slate-700">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
              <span>Dịch trực tiếp: Tiếng Việt</span>
            </div>

            {/* Comic Canvas Wrapper */}
            <div id="canvas-wrapper" className="relative rounded-2xl overflow-hidden border border-slate-100 shadow-inner bg-slate-50">
              <div className="absolute left-3 top-3 z-50">
                <button type="button" onClick={() => setIsStudyMenuOpen(open => !open)} aria-expanded={isStudyMenuOpen} aria-label="Mở công cụ ghi chú" title="Công cụ học tập và ghi chú" className={`flex h-10 w-10 items-center justify-center rounded-full border shadow-lg transition ${annotationTool !== 'none' ? 'border-pink-300 bg-pink-500 text-white' : 'border-white bg-white/95 text-slate-700 hover:text-pink-600'}`}>
                  <PenLine size={18}/>
                </button>
                {studyToolsMenu}
              </div>
              <img
                src={activePage.imageSrc}
                alt={activePage.title}
                className="w-full h-auto block select-none"
              />

              <svg
                className={`absolute inset-0 z-40 h-full w-full ${annotationTool === 'draw' ? 'touch-none cursor-crosshair pointer-events-auto' : 'pointer-events-none'}`}
                viewBox="0 0 1000 1000"
                preserveAspectRatio="none"
                onPointerDown={startDrawing}
                onPointerMove={continueDrawing}
                onPointerUp={stopDrawing}
                onPointerCancel={stopDrawing}
                aria-label="Lớp ghi chú trên trang truyện"
              >
                {(pageStrokes[activePage.id] || []).map((stroke, index) => (
                  <polyline key={`${activePage.id}-stroke-${index}`} points={stroke.points.map(point => `${point.x},${point.y}`).join(' ')} fill="none" stroke={stroke.color} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                ))}
              </svg>

              {/* Speech Bubble Interactive Pins */}
              {overlaysVisible && activePage.bubbles.map((bubble, bIdx) => {
                const isPink = bubble.type === 'dialogue' || bubble.type === 'grammar';
                const borderColor = isPink ? 'border-pink-500' : 'border-blue-500';
                const bgColor = isPink ? 'bg-pink-400/10 hover:bg-pink-400/25' : 'bg-blue-400/10 hover:bg-blue-400/25';
                const badgeColor = isPink ? 'bg-pink-500' : 'bg-blue-500';
                const shadowGlow = isPink ? 'shadow-[0_0_20px_rgba(244,114,182,0.35)]' : 'shadow-[0_0_20px_rgba(96,165,250,0.35)]';
                const directTextColor = isPink ? 'text-pink-900 border-pink-200' : 'text-blue-900 border-blue-200';

                return (
                  <div
                    key={bubble.id}
                    style={{
                      top: bubble.top,
                      left: bubble.left,
                      right: bubble.right,
                      bottom: bubble.bottom,
                      width: bubble.width,
                      height: bubble.height
                    }}
                    onMouseEnter={() => setActiveBubbleId(bubble.id)}
                    onMouseLeave={() => setActiveBubbleId(null)}
                    onClick={() => {
                      if (annotationTool === 'highlight') handleBubbleAnnotation(bubble.id);
                      else handlePlayVoice(bubble.hanzi);
                    }}
                    className={`bubble-pin group absolute cursor-pointer z-30`}
                  >
                    {/* Highlight Box inside bubble */}
                    <div style={pageHighlights[bubble.id] ? { backgroundColor: `${pageHighlights[bubble.id]}33`, borderColor: pageHighlights[bubble.id] } : undefined} className={`w-full h-full rounded-xl border-2 ${borderColor} ${bgColor} ${shadowGlow} transition-all flex flex-col justify-between p-1.5`}>
                      <div className="flex items-center justify-between">
                        <span className={`${badgeColor} text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-xs flex items-center gap-1`}>
                          <span className="material-symbols-outlined text-[12px]">translate</span>
                          <span>Thoại {bIdx + 1}</span>
                        </span>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePlayVoice(bubble.hanzi);
                          }}
                          className={`w-5 h-5 rounded-full bg-white/90 hover:scale-110 ${isPink ? 'text-pink-600' : 'text-blue-600'} flex items-center justify-center text-[10px] shadow-xs`}
                          title="Nghe phát âm"
                        >
                          <span className="material-symbols-outlined text-[13px]">volume_up</span>
                        </button>
                      </div>

                      {/* Direct translation subtitle overlay */}
                      <div
                        style={{ fontSize: `${11 + fontSizeOffset}px` }}
                        className={`bubble-direct-trans bg-white/95 backdrop-blur-xs px-1.5 py-0.5 rounded font-semibold ${directTextColor} border leading-tight line-clamp-2`}
                      >
                        {bubble.vietnamese}
                      </div>
                    </div>

                    {/* Rich Hover Popover Card */}
                    <div className="opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-all duration-300 transform -translate-y-2 group-hover:translate-y-0 absolute top-full left-0 mt-2 w-80 bg-white/95 backdrop-blur-xl p-4 rounded-2xl shadow-floating border border-pink-200 z-50">
                      <div className="flex items-center justify-between border-b border-pink-100 pb-2 mb-2">
                        <span className="text-[11px] font-bold text-pink-500 uppercase tracking-wider flex items-center gap-1">
                          <span className="material-symbols-outlined text-[14px]">format_quote</span>
                          <span>Lời thoại {bIdx + 1}</span>
                        </span>
                        <span className="text-[10px] bg-pink-100 text-pink-600 px-2 py-0.5 rounded-full font-medium">
                          {bubble.locationLabel}
                        </span>
                      </div>

                      <div className="mb-2">
                        <div className="text-xs font-mono text-slate-500">
                          {bubble.pinyin}
                        </div>
                        <div className="text-base font-['Noto_Serif_SC'] font-bold text-slate-800 mt-0.5">
                          {bubble.hanzi}
                        </div>
                      </div>

                      <div className="p-2 rounded-xl bg-pink-50/80 border border-pink-200 text-pink-900 text-xs font-semibold leading-relaxed flex items-start gap-1.5">
                        <span className="material-symbols-outlined text-pink-500 text-[14px] mt-0.5">edit</span>
                        <span>"{bubble.vietnamese}"</span>
                      </div>

                      {/* Vocabulary Breakdown Chips */}
                      {bubble.vocabChips.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-1.5 text-[10px]">
                          {bubble.vocabChips.map((chip, cIdx) => (
                            <span
                              key={cIdx}
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePlayVoice(chip.word);
                              }}
                              className="bg-slate-100 hover:bg-pink-100 hover:text-pink-600 px-2 py-0.5 rounded-md text-slate-600 font-medium cursor-pointer transition-colors"
                              title="Bấm để nghe phát âm"
                            >
                              {chip.word} ({chip.meaning})
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Hint bar at bottom of canvas */}
            <div className="mt-3 flex flex-wrap items-center justify-between text-xs text-slate-500 px-2 gap-2">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-pink-400"></span>
                  <span>Khung hồng: Hội thoại / Ngữ pháp</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-400"></span>
                  <span>Khung xanh: Dẫn truyện</span>
                </span>
              </div>
              <span className="text-slate-400 text-[11px] flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">touch_app</span>
                <span>Chạm vào khung để nghe đọc</span>
              </span>
            </div>

          </div>
        </section>

        {/* RIGHT STUDY PANEL (3 Cols) */}
        <aside className="col-span-1 lg:col-span-3 flex flex-col gap-5 sticky top-24">
          
          {/* Card: Vocabulary on this page */}
          <div className="bg-white rounded-3xl p-5 shadow-soft border border-pink-100">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-xl bg-pink-100 flex items-center justify-center text-pink-600 text-xs font-bold">
                  <span className="material-symbols-outlined text-[16px]">school</span>
                </div>
                <h3 className="text-sm font-bold text-slate-800">Từ vựng trang này</h3>
              </div>
              <span className="text-xs font-semibold text-[#a43073] bg-pink-50 px-2 py-0.5 rounded-full">
                {activePage.vocabulary.length} từ mới
              </span>
            </div>

            <div className="space-y-2.5">
              {activePage.vocabulary.map((vocab, vIdx) => (
                <div
                  key={vIdx}
                  onClick={() => handlePlayVoice(vocab.hanzi)}
                  className="p-2.5 rounded-2xl bg-slate-50 hover:bg-pink-50/60 border border-slate-100 hover:border-pink-200 transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-['Noto_Serif_SC'] font-bold text-base text-slate-800 group-hover:text-[#a43073]">
                          {vocab.hanzi}
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          {vocab.pinyin}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600 font-medium">
                        {vocab.vietnamese}
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePlayVoice(vocab.hanzi);
                        }}
                        className="w-7 h-7 rounded-lg bg-white group-hover:bg-pink-200/60 text-slate-400 group-hover:text-pink-600 flex items-center justify-center text-xs transition-colors"
                        title="Phát âm"
                      >
                        <span className="material-symbols-outlined text-[16px]">volume_up</span>
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); saveVocabulary(vocab); }}
                        disabled={savedWords.includes(vocab.hanzi)}
                        className="w-7 h-7 rounded-lg bg-white text-slate-400 hover:bg-blue-100 hover:text-blue-700 disabled:text-emerald-600 disabled:bg-emerald-50 flex items-center justify-center transition-colors"
                        title={savedWords.includes(vocab.hanzi) ? 'Đã lưu vào Flashcard' : 'Lưu từ vào Flashcard'}
                      >
                        <span className="material-symbols-outlined text-[16px]">{savedWords.includes(vocab.hanzi) ? 'check' : 'style'}</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={handleSaveAllVocab}
              className="w-full mt-3 py-2 bg-pink-50 hover:bg-pink-100 text-[#a43073] text-xs font-bold rounded-2xl border border-pink-200 transition-colors flex items-center justify-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[14px]">add</span>
              <span>Lưu toàn bộ vào Flashcard</span>
            </button>
          </div>

          {/* Card: Grammar Spotlight */}
          {activePage.grammarSpotlight && (
            <div className="bg-gradient-to-br from-blue-50/80 via-white to-pink-50/50 rounded-3xl p-5 shadow-soft border border-blue-100/70">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                <span className="text-xs font-bold text-blue-600 uppercase tracking-wide">
                  Cấu trúc trọng điểm
                </span>
              </div>
              <div className="text-sm font-bold text-slate-800 mb-1">
                {activePage.grammarSpotlight.pattern}
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                {activePage.grammarSpotlight.description}
              </p>
              <div className="bg-white/80 p-2.5 rounded-xl border border-blue-200/60 text-xs text-slate-700">
                <span className="text-pink-600 font-bold">Ví dụ trong trang:</span>{' '}
                {activePage.grammarSpotlight.exampleHanzi}
                <div className="text-[11px] text-slate-500 italic mt-0.5">
                  {activePage.grammarSpotlight.exampleVietnamese}
                </div>
              </div>
            </div>
          )}

          {/* Card: Streak */}
          <div className="bg-white rounded-3xl p-4 shadow-soft border border-amber-100 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-100 flex items-center justify-center text-amber-500 text-lg">
                🔥
              </div>
              <div>
                <div className="text-xs font-bold text-slate-800">Chuỗi học 7 ngày</div>
                <div className="text-[11px] text-slate-500">Đã đọc 12 trang hôm nay</div>
              </div>
            </div>
            <span className="text-xs font-bold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-xl border border-amber-200">
              +50 XP
            </span>
          </div>

        </aside>

      </div>

      {/* FLOATING GLASS DOCK (Bottom Controls) */}
      <div className="fixed bottom-5 inset-x-0 mx-auto w-fit z-40 transition-all">
        <div className="glass-dock rounded-full px-5 py-2.5 flex items-center gap-4 border border-white/80">
          
          {/* Navigation */}
          <div className="flex items-center gap-1.5 border-r border-slate-200/80 pr-3">
            <button
              onClick={() => setCurrentPageIndex(prev => (prev > 0 ? prev - 1 : COMIC_PAGES.length - 1))}
              className="w-9 h-9 rounded-full bg-slate-100/80 hover:bg-pink-100 text-slate-600 hover:text-pink-600 flex items-center justify-center transition-all shadow-xs"
              title="Trang trước"
            >
              <span className="material-symbols-outlined text-[18px]">skip_previous</span>
            </button>
            <div className="text-center px-2">
              <span className="text-xs font-bold text-slate-700 block leading-tight">
                Trang 0{activePage.pageNumber}
              </span>
              <span className="text-[10px] text-slate-400 block font-medium">18 trang</span>
            </div>
            <button
              onClick={() => setCurrentPageIndex(prev => (prev < COMIC_PAGES.length - 1 ? prev + 1 : 0))}
              className="w-9 h-9 rounded-full bg-slate-100/80 hover:bg-pink-100 text-slate-600 hover:text-pink-600 flex items-center justify-center transition-all shadow-xs"
              title="Trang tiếp"
            >
              <span className="material-symbols-outlined text-[18px]">skip_next</span>
            </button>
          </div>

          {/* Full Page Read Button */}
          <div className="flex items-center gap-2 border-r border-slate-200/80 pr-3">
            <button
              onClick={handleReadEntirePage}
              disabled={isPlayingFullPage}
              className={`px-4 py-2 rounded-full text-white font-semibold text-xs flex items-center gap-2 shadow-md shadow-pink-300/40 hover:scale-105 transition-all ${
                isPlayingFullPage
                  ? 'bg-pink-400 animate-pulse'
                  : 'bg-gradient-to-r from-pink-500 to-rose-400 hover:from-pink-600 hover:to-rose-500'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">
                {isPlayingFullPage ? 'volume_up' : 'play_circle'}
              </span>
              <span>{isPlayingFullPage ? 'Đang đọc...' : 'Đọc thoại toàn trang'}</span>
            </button>
            
            <button
              onClick={cycleSpeed}
              className="w-8 h-8 rounded-full bg-slate-100/80 hover:bg-slate-200 text-slate-600 text-xs font-bold transition-colors"
              title="Tốc độ đọc"
            >
              {speechRate}x
            </button>
          </div>

          {/* Font Resize */}
          <div className="flex items-center gap-1 border-r border-slate-200/80 pr-3">
            <button
              onClick={() => changeFontSize(-1)}
              className="w-7 h-7 rounded-full hover:bg-slate-100 text-slate-600 flex items-center justify-center text-xs"
              title="Giảm cỡ chữ"
            >
              A-
            </button>
            <span className="text-xs font-mono font-semibold text-slate-600 px-1">Aa</span>
            <button
              onClick={() => changeFontSize(1)}
              className="w-7 h-7 rounded-full hover:bg-slate-100 text-slate-600 flex items-center justify-center text-xs"
              title="Tăng cỡ chữ"
            >
              A+
            </button>
          </div>

          {/* Overlay Toggle */}
          <button
            onClick={() => setOverlaysVisible(!overlaysVisible)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              overlaysVisible
                ? 'bg-pink-100 text-[#a43073] hover:bg-pink-200'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">
              {overlaysVisible ? 'visibility' : 'visibility_off'}
            </span>
            <span>{overlaysVisible ? 'Ẩn bản dịch' : 'Hiện bản dịch'}</span>
          </button>

        </div>
      </div>

    </div>
  );
};
