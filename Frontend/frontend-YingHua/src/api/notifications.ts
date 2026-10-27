// Gọi API Thông báo và báo lỗi bản dịch (M14).
import { ApiError, apiRequest } from './client';

export type ReportType = 'ocr' | 'translation' | 'other';
export type ReportStatus = 'new' | 'resolved' | 'rejected';

export interface CreateErrorReportBody {
  page_id: number;
  bubble_id?: number;
  report_type?: ReportType;
  description?: string;
}

export interface ErrorReport {
  id: number;
  status: ReportStatus;
  report_type: ReportType;
  description: string;
  resolution_note: string | null;
  page_id: number | null;
  bubble_id: number | null;
  series_title: string | null;
  chapter_number: number | null;
  page_no: number | null;
  bubble_text_zh: string | null;
  bubble_text_vi: string | null;
  created_at: string;
  handled_at: string | null;
}

export interface ErrorReportPage {
  items: ErrorReport[];
  total: number;
  page: number;
  size: number;
}

export interface AppNotification {
  id: number;
  kind: string;
  title: string;
  body: string | null;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface NotificationPage {
  items: AppNotification[];
  total: number;
  page: number;
  size: number;
  unread: number;
}

export const createErrorReport = (body: CreateErrorReportBody): Promise<ErrorReport> =>
  apiRequest<ErrorReport>('/error-reports', { method: 'POST', body });

export const listMyErrorReports = (page = 1, size = 20, signal?: AbortSignal): Promise<ErrorReportPage> =>
  apiRequest<ErrorReportPage>(`/error-reports?page=${page}&size=${size}`, { signal });

/** Báo trùng: người học đã báo đúng chỗ này và còn chờ xử lý. */
export const isReportDuplicate = (err: unknown): boolean =>
  err instanceof ApiError && err.code === 'REPORT_ALREADY_EXISTS';

export const listNotifications = (size = 20, signal?: AbortSignal): Promise<NotificationPage> =>
  apiRequest<NotificationPage>(`/notifications?page=1&size=${size}`, { signal });

export const getUnreadCount = async (signal?: AbortSignal): Promise<number> =>
  (await apiRequest<{ unread: number }>('/notifications/unread-count', { signal })).unread;

export const markNotificationRead = async (id: number): Promise<number> =>
  (await apiRequest<{ unread: number }>(`/notifications/${id}/read`, { method: 'POST' })).unread;

export const markAllNotificationsRead = (): Promise<{ updated: number; unread: number }> =>
  apiRequest<{ updated: number; unread: number }>('/notifications/read-all', { method: 'POST' });
