import { apiClient } from '@/lib/api';

export interface EventTrigger {
  type: 'event';
  event: string;
  collection?: string;
}

export interface ManualTrigger {
  type: 'manual';
}

export type HookTrigger = EventTrigger | ManualTrigger;

export interface HookAction {
  type: string;
  [key: string]: unknown;
}

export interface Hook {
  id: string;
  account_id: string;
  name: string;
  description: string | null;
  trigger: HookTrigger;
  condition: string | null;
  actions: HookAction[];
  enabled: boolean;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface HookListResponse {
  items: Hook[];
  total: number;
}

export interface HookExecution {
  id: string;
  hook_id: string;
  trigger_type: string;
  status: 'success' | 'partial' | 'failed';
  actions_executed: number;
  error_message: string | null;
  duration_ms: number | null;
  executed_at: string;
}

export interface HookExecutionListResponse {
  items: HookExecution[];
  total: number;
}

export interface CreateHookRequest {
  name: string;
  description?: string;
  trigger: HookTrigger;
  condition?: string;
  actions?: HookAction[];
  enabled?: boolean;
}

export interface UpdateHookRequest {
  name?: string;
  description?: string;
  trigger?: HookTrigger;
  condition?: string;
  actions?: HookAction[];
  enabled?: boolean;
}

export const hooksService = {
  list: async (): Promise<HookListResponse> => {
    const response = await apiClient.get<HookListResponse>('/hooks', {
      params: { limit: 200 },
    });
    // Filter out schedule-triggered hooks (those belong to Scheduled Tasks page)
    const all = response.data;
    const filtered = all.items.filter((h) => h.trigger.type !== 'schedule');
    return { items: filtered, total: filtered.length };
  },

  get: async (id: string): Promise<Hook> => {
    const response = await apiClient.get<Hook>(`/hooks/${id}`);
    return response.data;
  },

  create: async (data: CreateHookRequest): Promise<Hook> => {
    const response = await apiClient.post<Hook>('/hooks', data);
    return response.data;
  },

  update: async (id: string, data: UpdateHookRequest): Promise<Hook> => {
    const response = await apiClient.patch<Hook>(`/hooks/${id}`, data);
    return response.data;
  },

  toggle: async (id: string): Promise<Hook> => {
    const response = await apiClient.patch<Hook>(`/hooks/${id}/toggle`);
    return response.data;
  },

  trigger: async (id: string): Promise<{ message: string; status: string; actions_executed: number; error?: string }> => {
    const response = await apiClient.post<{ message: string; status: string; actions_executed: number; error?: string }>(
      `/hooks/${id}/trigger`,
    );
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/hooks/${id}`);
  },

  listExecutions: async (id: string): Promise<HookExecutionListResponse> => {
    const response = await apiClient.get<HookExecutionListResponse>(`/hooks/${id}/executions`, {
      params: { limit: 50 },
    });
    return response.data;
  },
};
