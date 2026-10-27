// Trạng thái công khai của hệ thống (F13.05): bảo trì, LLM, TTS, trang mẫu.
import { apiRequest } from './client';

export interface SystemStatus {
  maintenance_mode: boolean;
  message: string | null;
  llm_enabled: boolean;
  tts_enabled: boolean;
  sample_page_available: boolean;
}

export const getSystemStatus = (signal?: AbortSignal): Promise<SystemStatus> =>
  apiRequest<SystemStatus>('/system/status', { auth: false, signal });
