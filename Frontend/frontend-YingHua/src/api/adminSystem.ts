// API quản trị hệ thống (M13): thống kê, cài đặt, kiểm duyệt, nhật ký, báo lỗi.
import { apiRequest } from './client';
import { ErrorReport, ReportStatus } from './notifications';

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// ---- Thống kê hệ thống (F12.03) ----
export interface ActivityTotals {
  active_users: number;
  reviews_count: number;
  pages_read: number;
  words_saved: number;
  quizzes_done: number;
  study_seconds: number;
}

export interface SystemStats {
  generated_at: string;
  users: { total: number; admins: number; locked: number; new_last_7_days: number };
  content: { series_total: number; series_public: number; chapters: number; pages: number };
  imaging: {
    pages_queued: number;
    pages_running: number;
    pages_done: number;
    pages_failed: number;
    bubbles: number;
    avg_processing_ms: number | null;
    ocr_success_rate: number | null;
    ocr_failure_rate: number | null;
  };
  words_saved_total: number;
  activity_today: ActivityTotals;
  activity_7_days: ActivityTotals;
  activity_30_days: ActivityTotals;
}

export const getSystemStats = (signal?: AbortSignal): Promise<SystemStats> =>
  apiRequest<SystemStats>('/admin/stats', { signal });

// ---- Báo lỗi (F14.02) ----
export interface AdminErrorReport extends ErrorReport {
  reporter: { id: number; display_name: string; email: string } | null;
}

export const listErrorReports = (
  status: ReportStatus | null,
  page: number,
  size: number,
  signal?: AbortSignal
): Promise<Paged<AdminErrorReport>> => {
  const query = new URLSearchParams({ page: String(page), size: String(size) });
  if (status) query.set('status', status);
  return apiRequest<Paged<AdminErrorReport>>(`/admin/error-reports?${query.toString()}`, { signal });
};

export const resolveErrorReport = (
  id: number,
  status: 'resolved' | 'rejected',
  note: string
): Promise<AdminErrorReport> =>
  apiRequest<AdminErrorReport>(`/admin/error-reports/${id}`, {
    method: 'PATCH',
    body: { status, note: note.trim() ? note.trim() : null }
  });

// ---- Cài đặt hệ thống (F13.05) ----
export interface SystemSettingsValues {
  llm_enabled: boolean;
  tts_enabled: boolean;
  quiz_daily_llm_limit: number;
  ai_note_daily_limit: number;
  grammar_daily_limit: number;
  mistake_review_daily_limit: number;
  maintenance_mode: boolean;
  auto_moderation_enabled: boolean;
  ocr_on_upload_enabled: boolean;
  admin_notifications_enabled: boolean;
  sample_page_id: number | null;
}

export interface SystemSettings {
  values: SystemSettingsValues;
  /** Khóa quản trị viên đã đặt; còn lại đang dùng mặc định. */
  overridden: string[];
}

export const getSystemSettings = (signal?: AbortSignal): Promise<SystemSettings> =>
  apiRequest<SystemSettings>('/admin/system-settings', { signal });

/** Chỉ gửi các khóa đã đổi; giá trị sai bị từ chối cả lượt (400 INVALID_SETTING_VALUE). */
export const updateSystemSettings = (changes: Partial<SystemSettingsValues>): Promise<SystemSettings> =>
  apiRequest<SystemSettings>('/admin/system-settings', { method: 'PATCH', body: changes });

/** Trang chọn được làm trang mẫu (F04.16): truyện công khai, đã dịch xong, ảnh chưa bị gỡ. */
export interface SamplePageCandidate {
  page_id: number;
  series_title: string;
  chapter_number: number;
  chapter_title: string | null;
  page_no: number;
  bubble_count: number;
}

export const listSamplePageCandidates = (signal?: AbortSignal): Promise<SamplePageCandidate[]> =>
  apiRequest<{ items: SamplePageCandidate[] }>('/admin/system-settings/sample-page-candidates', { signal }).then(
    body => body.items
  );

// ---- Kiểm duyệt (F13.04) ----
export interface PersonRef {
  id: number;
  display_name: string;
  email: string;
}

export interface ModerationUpload {
  file_id: number;
  page_id: number | null;
  url: string;
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  uploaded_at: string;
  uploader: PersonRef | null;
  flags: string[];
  quick_upload: boolean;
}

export interface Removal {
  id: number;
  file_id: number | null;
  page_id: number | null;
  reason: string;
  removed_at: string;
  removed_by: PersonRef | null;
  owner: PersonRef | null;
}

export const listModerationUploads = (
  flaggedOnly: boolean,
  page: number,
  size: number,
  signal?: AbortSignal
): Promise<Paged<ModerationUpload>> =>
  apiRequest<Paged<ModerationUpload>>(`/admin/moderation/uploads?flagged_only=${flaggedOnly}&page=${page}&size=${size}`, { signal });

export const removeContent = (target: { page_id: number | null; file_id: number }, reason: string): Promise<Removal> =>
  apiRequest<Removal>('/admin/moderation/removals', {
    method: 'POST',
    body: target.page_id !== null ? { page_id: target.page_id, reason: reason.trim() } : { file_id: target.file_id, reason: reason.trim() }
  });

export const listRemovals = (page: number, size: number, signal?: AbortSignal): Promise<Paged<Removal>> =>
  apiRequest<Paged<Removal>>(`/admin/moderation/removals?page=${page}&size=${size}`, { signal });

// ---- Nhật ký quản trị (F13.06) ----
export interface AuditLog {
  id: number;
  admin: PersonRef | null;
  action: string;
  target_type: string;
  target_id: number | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AuditFilter {
  adminId: number | null;
  action: string;
  targetType: string;
  /** Ngày dạng yyyy-mm-dd từ ô nhập ngày; rỗng = không lọc. */
  since: string;
  until: string;
}

export const listAuditLogs = (filter: AuditFilter, page: number, size: number, signal?: AbortSignal): Promise<Paged<AuditLog>> => {
  const query = new URLSearchParams({ page: String(page), size: String(size) });
  if (filter.adminId !== null) query.set('admin_id', String(filter.adminId));
  if (filter.action.trim()) query.set('action', filter.action.trim());
  if (filter.targetType.trim()) query.set('target_type', filter.targetType.trim());
  if (filter.since) query.set('since', new Date(`${filter.since}T00:00:00`).toISOString());
  if (filter.until) {
    // "Đến hết ngày": lấy mốc đầu ngày hôm sau.
    const end = new Date(`${filter.until}T00:00:00`);
    end.setDate(end.getDate() + 1);
    query.set('until', end.toISOString());
  }
  return apiRequest<Paged<AuditLog>>(`/admin/audit-logs?${query.toString()}`, { signal });
};
