import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { errorMessage, isAbortedError } from '../api/client';
import { getPage } from '../api/library';
import {
  AppNotification,
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead
} from '../api/notifications';
import { TAB_PATHS, readerPath } from '../routes';

const POLL_INTERVAL_MS = 60_000;
const LIST_SIZE = 20;

const KIND_ICON: Record<string, string> = {
  reminder: 'alarm',
  report_resolved: 'task_alt',
  report_rejected: 'report'
};

const formatTime = (iso: string): string => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('vi-VN', { hour12: false });
};

/** Chuông thông báo (F14.04, F14.06): số chưa đọc lấy từ máy chủ, tải lại khi quay lại tab và mỗi 60 giây. */
export const NotificationBell: React.FC = () => {
  const navigate = useNavigate();
  const boxRef = useRef<HTMLDivElement>(null);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(value => value + 1), []);

  // Số chưa đọc: hỏi lại khi quay lại tab và định kỳ khi tab đang mở.
  useEffect(() => {
    const controller = new AbortController();
    getUnreadCount(controller.signal)
      .then(setUnread)
      .catch(() => undefined);
    return () => controller.abort();
  }, [tick]);

  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === 'visible') reload();
    };
    const timer = window.setInterval(refresh, POLL_INTERVAL_MS);
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, [reload]);

  // Danh sách: nạp mỗi khi mở khung và mỗi lần dữ liệu được làm mới khi khung đang mở.
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true);
    listNotifications(LIST_SIZE, controller.signal)
      .then(page => {
        setItems(page.items);
        setUnread(page.unread);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [open, tick]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const markRead = async (item: AppNotification) => {
    if (item.is_read) return;
    try {
      setUnread(await markNotificationRead(item.id));
      setItems(current => current.map(n => (n.id === item.id ? { ...n, is_read: true } : n)));
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const handleMarkAll = async () => {
    try {
      const result = await markAllNotificationsRead();
      setUnread(result.unread);
      setItems(current => current.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  // Đưa người học tới trang liên quan: báo lỗi → trang truyện bị báo, nhắc ôn → trang từ vựng.
  const handleOpen = async (item: AppNotification) => {
    await markRead(item);
    const pageId = item.data.page_id;
    try {
      if (typeof pageId === 'number' && Number.isInteger(pageId) && pageId > 0) {
        const page = await getPage(pageId);
        setOpen(false);
        navigate(readerPath({ chapterId: page.chapter_id, pageNo: page.page_no, pageId: page.id }));
      } else if (item.kind === 'reminder') {
        setOpen(false);
        navigate(TAB_PATHS.flashcards);
      }
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div ref={boxRef} className="relative">
      <button
        onClick={() => setOpen(value => !value)}
        className="relative w-9 h-9 rounded-full bg-white dark:bg-[#1e293b] border border-pink-100 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-[#a43073] dark:hover:text-pink-400 hover:border-pink-300 dark:hover:border-pink-900/60 flex items-center justify-center shadow-xs dark:shadow-none transition-colors duration-300"
        title="Thông báo"
        aria-label={unread > 0 ? `Thông báo, ${unread} chưa đọc` : 'Thông báo'}
        aria-expanded={open}
      >
        <span className="material-symbols-outlined text-[20px]">notifications</span>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-[#a43073] text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 max-w-[90vw] bg-white dark:bg-slate-800 rounded-2xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-pink-100 dark:border-slate-700">
            <span className="text-sm font-bold text-slate-800 dark:text-slate-100">Thông báo</span>
            <button
              onClick={handleMarkAll}
              disabled={unread === 0}
              className="text-[11px] font-bold text-[#a43073] dark:text-pink-400 hover:underline disabled:text-slate-400 dark:disabled:text-slate-500 disabled:no-underline"
            >
              Đánh dấu tất cả đã đọc
            </button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {error && (
              <div className="px-4 py-3 text-xs text-rose-600 dark:text-rose-400 flex items-center justify-between gap-2">
                <span>{error}</span>
                <button onClick={reload} className="font-bold underline">Thử lại</button>
              </div>
            )}
            {loading && items.length === 0 && <div className="px-4 py-6 text-center text-xs text-slate-500 dark:text-slate-400">Đang tải...</div>}
            {!loading && !error && items.length === 0 && (
              <div className="px-4 py-6 text-center text-xs text-slate-500 dark:text-slate-400">Chưa có thông báo nào.</div>
            )}
            {items.map(item => (
              <button
                key={item.id}
                onClick={() => void handleOpen(item)}
                className={`w-full text-left px-4 py-3 flex gap-3 border-b border-slate-50 dark:border-slate-700 hover:bg-pink-50 dark:hover:bg-slate-700 ${item.is_read ? '' : 'bg-pink-50/60 dark:bg-pink-900/20'}`}
              >
                <span className="material-symbols-outlined text-[20px] text-[#a43073] dark:text-pink-400 shrink-0">{KIND_ICON[item.kind] ?? 'notifications'}</span>
                <span className="flex flex-col gap-0.5 min-w-0">
                  <span className={`text-xs text-slate-800 dark:text-slate-100 ${item.is_read ? 'font-medium' : 'font-bold'}`}>{item.title}</span>
                  {item.body && <span className="text-[11px] text-slate-500 dark:text-slate-400 break-words">{item.body}</span>}
                  <span className="text-[10px] text-slate-400 dark:text-slate-500">{formatTime(item.created_at)}</span>
                </span>
                {!item.is_read && <span className="ml-auto mt-1 w-2 h-2 rounded-full bg-[#a43073] shrink-0" aria-label="Chưa đọc" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
