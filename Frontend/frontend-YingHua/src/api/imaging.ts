// Gọi API xử lý ảnh (M04): trạng thái xử lý, dịch lại, tải ảnh về.
import { apiRequest } from './client';
import { downloadBlob } from './files';
import { Paged, TranslationStatus } from './library';

export interface PageStatus {
  page_id: number;
  translation_id: number | null;
  status: TranslationStatus | null;
  attempts: number;
  error_step: string | null;
  error_message: string | null;
  can_retranslate: boolean;
}

export type ImageVariant = 'original' | 'inpainted' | 'rendered';

export const getPageStatus = (pageId: number, signal?: AbortSignal): Promise<PageStatus> =>
  apiRequest<PageStatus>(`/pages/${pageId}/status`, { signal });

export const retranslatePage = (
  pageId: number
): Promise<{ page_id: number | null; translation_id: number; status: TranslationStatus }> =>
  apiRequest(`/pages/${pageId}/retranslate`, { method: 'POST' });

export const downloadPageImage = (pageId: number, variant: ImageVariant, filename: string): Promise<void> =>
  downloadBlob(`/pages/${pageId}/download?variant=${variant}`, filename);

/** Một bản dịch trong hàng đợi xử lý ảnh (F04.05, quản trị viên). */
export interface AdminTranslation {
  id: number;
  status: TranslationStatus;
  attempts: number;
  worker_id: string | null;
  error_step: string | null;
  error_message: string | null;
  original_url: string | null;
  inpainted_url: string | null;
  rendered_url: string | null;
  processing_ms: number | null;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface AdminTranslationPage extends Paged<AdminTranslation> {
  /** Số bản dịch theo từng trạng thái (toàn hệ thống, không phụ thuộc bộ lọc). */
  counts: Record<string, number>;
  avg_processing_ms: number | null;
}

export const listTranslations = (
  options: { status?: TranslationStatus; page?: number; size?: number } = {}
): Promise<AdminTranslationPage> => {
  const query = new URLSearchParams();
  if (options.status) query.set('status', options.status);
  query.set('page', String(options.page ?? 1));
  query.set('size', String(options.size ?? 20));
  return apiRequest<AdminTranslationPage>(`/admin/translations?${query.toString()}`);
};

/** Chạy lại bản dịch lỗi (F04.06). */
export const retryTranslation = (
  translationId: number
): Promise<{ page_id: number | null; translation_id: number; status: TranslationStatus }> =>
  apiRequest(`/admin/translations/${translationId}/retry`, { method: 'POST' });

/** Nhãn trạng thái xử lý hiển thị cho người học. */
export function statusLabel(status: TranslationStatus | null): string {
  switch (status) {
    case 'queued':
      return 'Đang xếp hàng chờ xử lý';
    case 'running':
      return 'Đang nhận diện và dịch';
    case 'done':
      return 'Đã dịch xong';
    case 'failed':
      return 'Xử lý lỗi';
    default:
      return 'Chưa có bản dịch';
  }
}
