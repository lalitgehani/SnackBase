import { apiClient } from '@/lib/api';

export interface ScheduledTask {
  id: string;
  account_id: string;
  name: string;
  description: string | null;
  trigger: { type: string; cron?: string };
  actions: Record<string, unknown>[];
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  cron: string | null;
  cron_description: string | null;
}

export interface ScheduledTaskListResponse {
  items: ScheduledTask[];
  total: number;
}

export interface CreateScheduledTaskRequest {
  name: string;
  description?: string;
  cron: string;
  enabled?: boolean;
}

export interface UpdateScheduledTaskRequest {
  name?: string;
  description?: string;
  cron?: string;
  enabled?: boolean;
}

export const scheduledTasksService = {
  list: async (): Promise<ScheduledTaskListResponse> => {
    const response = await apiClient.get<ScheduledTaskListResponse>('/hooks', {
      params: { trigger_type: 'schedule', limit: 200 },
    });
    return response.data;
  },

  get: async (id: string): Promise<ScheduledTask> => {
    const response = await apiClient.get<ScheduledTask>(`/hooks/${id}`);
    return response.data;
  },

  create: async (data: CreateScheduledTaskRequest): Promise<ScheduledTask> => {
    const response = await apiClient.post<ScheduledTask>('/hooks', data);
    return response.data;
  },

  update: async (id: string, data: UpdateScheduledTaskRequest): Promise<ScheduledTask> => {
    const response = await apiClient.patch<ScheduledTask>(`/hooks/${id}`, data);
    return response.data;
  },

  toggle: async (id: string): Promise<ScheduledTask> => {
    const response = await apiClient.patch<ScheduledTask>(`/hooks/${id}/toggle`);
    return response.data;
  },

  trigger: async (id: string): Promise<{ job_id: string; message: string }> => {
    const response = await apiClient.post<{ job_id: string; message: string }>(
      `/hooks/${id}/trigger`,
    );
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/hooks/${id}`);
  },
};
