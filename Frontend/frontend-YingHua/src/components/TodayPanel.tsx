import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { errorMessage, isAbortedError } from '../api/client';
import { TodayAction, TodayItem, TodayPlan, getToday } from '../api/stats';
import { QUIZ_SECTION_PARAM, QUIZ_SECTION_VALUE, SAMPLE_PAGE_PATH, TAB_PATHS, readerPath } from '../routes';
import { ACTIVITY_EVENT } from '../utils/useStreak';
import { useSystemStatus } from '../utils/useSystemStatus';

interface TodayPanelProps {
  isLoggedIn: boolean;
  onRequireLogin: (message: string) => void;
}

const KIND_ICONS: Record<string, string> = {
  review_due: 'style',
  continue_reading: 'auto_stories',
  take_quiz: 'quiz',
  weekly_goal: 'flag',
  chapter_suggestions: 'lightbulb',
  get_started: 'rocket_launch'
};

const ACTION_LABELS: Record<string, string> = {
  review: 'Ôn ngay',
  reader: 'Đọc tiếp',
  quiz: 'Làm bài kiểm tra',
  library: 'Mở Thư viện',
  chapter_suggestions: 'Xem gợi ý'
};

/** Đường dẫn đích của một việc "Hôm nay" theo loại hành động do máy chủ trả. */
function actionPath(action: TodayAction): string | null {
  switch (action.type) {
    case 'review':
      return TAB_PATHS.flashcards;
    case 'quiz':
      return `${TAB_PATHS.flashcards}?${QUIZ_SECTION_PARAM}=${QUIZ_SECTION_VALUE}`;
    case 'library':
      return TAB_PATHS.library;
    case 'reader':
    case 'chapter_suggestions':
      if (action.chapter_id === null) return TAB_PATHS.library;
      return readerPath({ chapterId: action.chapter_id, pageNo: action.page_no ?? undefined });
    default:
      return null;
  }
}

/** Khối "Hôm nay nên học gì" (F12.04): việc ưu tiên lấy từ máy chủ, tải lại khi quay lại tab và sau mỗi hoạt động học. */
export const TodayPanel: React.FC<TodayPanelProps> = ({ isLoggedIn, onRequireLogin }) => {
  const navigate = useNavigate();
  const { sample_page_available } = useSystemStatus();
  const [plan, setPlan] = useState<TodayPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    if (!isLoggedIn) return;
    const onVisible = () => {
      if (document.visibilityState === 'visible') reload();
    };
    window.addEventListener('focus', onVisible);
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener(ACTIVITY_EVENT, reload);
    return () => {
      window.removeEventListener('focus', onVisible);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener(ACTIVITY_EVENT, reload);
    };
  }, [isLoggedIn, reload]);

  useEffect(() => {
    if (!isLoggedIn) {
      setPlan(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    getToday(controller.signal)
      .then(result => {
        setPlan(result);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [isLoggedIn, tick]);

  const samplePrompt = sample_page_available ? (
    <button
      onClick={() => (isLoggedIn ? navigate(SAMPLE_PAGE_PATH) : onRequireLogin('Vui lòng đăng nhập để thử trang mẫu Hover & Dịch!'))}
      className="inline-flex items-center gap-1.5 rounded-full bg-white border border-pink-200 px-4 py-2 text-xs font-bold text-[#a43073] hover:bg-pink-50 transition-colors"
    >
      <span className="material-symbols-outlined text-[16px]">touch_app</span>
      Thử Hover & Dịch với trang mẫu
    </button>
  ) : null;

  // Khách chỉ thấy khối giới thiệu ở đầu trang; riêng lối thử trang mẫu vẫn hiển thị khi quản trị viên đã cấu hình.
  if (!isLoggedIn) {
    return samplePrompt ? <div className="mb-6 flex justify-center">{samplePrompt}</div> : null;
  }

  const items = plan ? [...plan.items].sort((a, b) => a.priority - b.priority) : [];

  const renderItem = (item: TodayItem) => {
    const path = actionPath(item.action);
    return (
      <article
        key={`${item.kind}-${item.priority}`}
        className={`rounded-2xl border p-4 flex flex-col gap-2 ${item.urgent ? 'border-[#a43073] bg-pink-50 shadow-soft' : 'border-slate-100 bg-white'}`}
      >
        <div className="flex items-start gap-3">
          <span className={`w-9 h-9 shrink-0 rounded-full flex items-center justify-center ${item.urgent ? 'bg-[#a43073] text-white' : 'bg-blue-50 text-blue-600'}`}>
            <span className="material-symbols-outlined text-[20px]">{KIND_ICONS[item.kind] ?? 'task_alt'}</span>
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-bold text-slate-800">{item.title}</h3>
              {item.urgent && <span className="rounded-full bg-[#a43073] px-2 py-0.5 text-[10px] font-bold text-white">Cần làm ngay</span>}
            </div>
            <p className="mt-0.5 text-xs text-slate-600 leading-relaxed">{item.message}</p>
          </div>
        </div>
        {path && (
          <button
            onClick={() => navigate(path)}
            className={`self-end rounded-full px-4 py-1.5 text-xs font-bold transition-colors ${item.urgent ? 'bg-[#a43073] text-white hover:bg-[#85145a]' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}
          >
            {ACTION_LABELS[item.action.type] ?? 'Mở'}
          </button>
        )}
      </article>
    );
  };

  return (
    <section aria-label="Hôm nay nên học gì" className="mb-8 rounded-3xl border border-pink-100 bg-white p-5 sm:p-6 shadow-soft">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-[#a43073]">Hôm nay</span>
          <h2 className="text-xl font-bold text-slate-800 font-['Plus_Jakarta_Sans']">Hôm nay nên học gì?</h2>
        </div>
        {samplePrompt}
      </div>

      {loading && !plan && (
        <div className="flex items-center gap-2 py-4 text-xs text-slate-400">
          <span className="w-4 h-4 border-2 border-pink-300 border-t-transparent rounded-full animate-spin"></span>Đang tải...
        </div>
      )}
      {error && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-xl bg-rose-50 p-3 text-xs font-semibold text-rose-700">
          <span>{error}</span>
          <button onClick={reload} className="rounded-full bg-white px-3 py-1 font-bold">Thử lại</button>
        </div>
      )}
      {plan && !error && (plan.all_done || items.length === 0) && (
        <div className="flex flex-col items-start gap-2 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-800 sm:flex-row sm:items-center sm:justify-between">
          <span className="font-semibold">{plan.message ?? 'Bạn đã hoàn thành hết việc hôm nay. Tuyệt vời!'}</span>
          <button onClick={() => navigate(TAB_PATHS.library)} className="rounded-full bg-white px-4 py-1.5 text-xs font-bold text-emerald-700 hover:bg-emerald-100">
            Mở Thư viện
          </button>
        </div>
      )}
      {plan && !error && !plan.all_done && items.length > 0 && <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{items.map(renderItem)}</div>}
    </section>
  );
};
