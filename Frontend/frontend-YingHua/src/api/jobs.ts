// Gọi API tác vụ nền (M15): trạng thái các tác vụ định kỳ, chỉ dành cho quản trị viên.
import { apiRequest } from './client';

export interface JobRun {
  id: number;
  status: string;
  started_at: string;
  finished_at: string | null;
  summary: Record<string, unknown> | null;
  error_message: string | null;
}

export interface JobInfo {
  name: string;
  interval_seconds: number;
  enabled: boolean;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_status: string | null;
  next_run_at: string | null;
  locked_until: string | null;
  locked_by: string | null;
  last_run: JobRun | null;
}

export const listJobs = (): Promise<{ items: JobInfo[] }> => apiRequest<{ items: JobInfo[] }>('/admin/jobs');
