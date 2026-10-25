// Tải ảnh qua máy chủ có kèm mã truy cập (ảnh riêng tư không mở được bằng thẻ <img> trần).
import { apiRequest } from './client';

const API_PREFIX = '/api/v1';

/** Địa chỉ tệp do máy chủ trả (`/api/v1/files/7`) → đường dẫn tương đối so với gốc API. */
export const toApiPath = (url: string): string => (url.startsWith(API_PREFIX) ? url.slice(API_PREFIX.length) : url);

export const fetchFileBlob = (url: string, signal?: AbortSignal): Promise<Blob> =>
  apiRequest<Blob>(toApiPath(url), { responseType: 'blob', signal });

/** Tải tệp về máy qua đường dẫn có kiểm quyền (F04.04). */
export async function downloadBlob(path: string, filename: string): Promise<void> {
  const blob = await apiRequest<Blob>(path, { responseType: 'blob' });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
