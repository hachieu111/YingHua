// Lớp gọi API dùng chung: gắn mã truy cập, tự làm mới phiên khi gặp 401 (F01.03), báo lỗi theo định dạng chuẩn của server.

const API_BASE = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

const STORAGE_KEY = 'yinghua-auth';

/** Phát ra khi phiên không còn hiệu lực và không làm mới được. App lắng nghe để đưa người dùng về đăng nhập. */
export const SESSION_EXPIRED_EVENT = 'yinghua:session-expired';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

export function loadTokens(): StoredTokens | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredTokens>;
    if (typeof parsed.accessToken === 'string' && typeof parsed.refreshToken === 'string') {
      return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken };
    }
  } catch {
    // Dữ liệu hỏng hoặc trình duyệt chặn lưu trữ: coi như chưa đăng nhập.
  }
  return null;
}

export function saveTokens(tokens: StoredTokens | null): void {
  try {
    if (tokens) localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Phiên vẫn dùng được đến khi tải lại trang nếu không lưu được.
  }
}

const networkError = () => new ApiError(0, 'NETWORK_ERROR', 'Không thể kết nối, vui lòng thử lại');
const abortError = () => new ApiError(0, 'ABORTED', 'Yêu cầu đã bị hủy');
const isAbort = (err: unknown) => err instanceof DOMException && err.name === 'AbortError';

/** Lỗi do chính giao diện hủy yêu cầu: không cần báo cho người dùng. */
/** Thông điệp tiếng Việt hiển thị cho người dùng từ một lỗi bất kỳ. */
export const errorMessage = (err: unknown): string =>
  err instanceof ApiError ? err.message : 'Có lỗi xảy ra, vui lòng thử lại.';

export const isAbortedError = (err: unknown): boolean => err instanceof ApiError && err.code === 'ABORTED';

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as { error?: { code?: string; message?: string; details?: Record<string, unknown> } };
    if (body.error) {
      return new ApiError(res.status, body.error.code ?? 'HTTP_ERROR', body.error.message ?? 'Có lỗi xảy ra', body.error.details);
    }
  } catch {
    // Phản hồi không phải JSON.
  }
  return new ApiError(res.status, 'HTTP_ERROR', `Có lỗi xảy ra (${res.status})`);
}

type RefreshOutcome = 'ok' | 'rejected' | 'offline';
let refreshInFlight: Promise<RefreshOutcome> | null = null;

/** Một lần làm mới tại một thời điểm: nhiều yêu cầu cùng gặp 401 sẽ dùng chung kết quả (mã làm mới xoay vòng). */
function refreshTokens(): Promise<RefreshOutcome> {
  if (refreshInFlight) return refreshInFlight;
  const current = loadTokens();
  if (!current) return Promise.resolve('rejected');
  refreshInFlight = (async (): Promise<RefreshOutcome> => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: current.refreshToken })
      });
      if (!res.ok) return 'rejected';
      const data = (await res.json()) as { tokens: { access_token: string; refresh_token: string } };
      saveTokens({ accessToken: data.tokens.access_token, refreshToken: data.tokens.refresh_token });
      return 'ok';
    } catch {
      return 'offline';
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  /** Đối tượng JSON, hoặc FormData cho tải tệp (trình duyệt tự đặt Content-Type multipart). */
  body?: unknown;
  /** false cho các lệnh không cần đăng nhập (đăng nhập, đăng ký...). */
  auth?: boolean;
  /** Header bổ sung (vd. X-Guest-Session). */
  headers?: Record<string, string>;
  /** 'blob' cho ảnh/tệp nhị phân. */
  responseType?: 'json' | 'blob';
  /** Hủy yêu cầu (đóng cửa sổ, đổi trang). */
  signal?: AbortSignal;
  /** Gọi khi nhận phản hồi thành công, để đọc header (vd. X-TTS-Voice-Fallback). */
  onResponse?: (res: Response) => void;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, headers: extraHeaders, responseType = 'json', signal, onResponse } = options;
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;

  const send = (): Promise<Response> => {
    const headers: Record<string, string> = { ...extraHeaders };
    if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
    const tokens = loadTokens();
    if (auth && tokens) headers.Authorization = `Bearer ${tokens.accessToken}`;
    return fetch(`${API_BASE}${path}`, {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body)
    });
  };

  let res: Response;
  try {
    res = await send();
  } catch (err) {
    throw isAbort(err) ? abortError() : networkError();
  }

  if (res.status === 401 && auth && loadTokens()) {
    const outcome = await refreshTokens();
    if (outcome === 'ok') {
      try {
        res = await send();
      } catch (err) {
        throw isAbort(err) ? abortError() : networkError();
      }
    } else if (outcome === 'rejected') {
      saveTokens(null);
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    } else {
      // Mất mạng đúng lúc làm mới: không đăng xuất, để người dùng thử lại.
      throw networkError();
    }
  }

  if (!res.ok) throw await toApiError(res);
  onResponse?.(res);
  if (res.status === 204) return undefined as T;
  if (responseType === 'blob') return (await res.blob()) as T;
  return (await res.json()) as T;
}
