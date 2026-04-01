import { apiClient } from '@/lib/api';

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'retrying' | 'dead';

export interface Job {
  id: string;
  queue: string;
  handler: string;
  payload: Record<string, unknown>;
  status: JobStatus;
  priority: number;
  run_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  attempt_number: number;
  max_retries: number;
  retry_delay_seconds: number;
  created_at: string;
  created_by: string | null;
  account_id: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
}

export interface JobStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  retrying: number;
  dead: number;
  avg_duration_seconds: number | null;
  failure_rate: number | null;
}

export interface JobListParams {
  status?: string;
  queue?: string;
  handler?: string;
  limit?: number;
  offset?: number;
}

export const jobsService = {
  list: async (params?: JobListParams): Promise<JobListResponse> => {
    const response = await apiClient.get<JobListResponse>('/admin/jobs', { params });
    return response.data;
  },

  getStats: async (): Promise<JobStats> => {
    const response = await apiClient.get<JobStats>('/admin/jobs/stats');
    return response.data;
  },

  retry: async (id: string): Promise<Job> => {
    const response = await apiClient.post<Job>(`/admin/jobs/${id}/retry`);
    return response.data;
  },

  cancel: async (id: string): Promise<void> => {
    await apiClient.delete(`/admin/jobs/${id}`);
  },
};
