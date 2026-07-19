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

export interface HookListParams {
  limit?: number;
  offset?: number;
  enabled?: boolean;
  trigger_type?: 'event' | 'manual' | 'schedule' | string;
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
  execution_context?: Record<string, unknown> | null;
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

function sortHooksByUpdatedAtDesc(items: Hook[]): Hook[] {
  return [...items].sort((a, b) => {
    const ta = new Date(a.updated_at).getTime();
    const tb = new Date(b.updated_at).getTime();
    return tb - ta;
  });
}

export const hooksService = {
  /**
   * List hooks. When `trigger_type` is omitted, loads event + manual in parallel
   * (Hooks admin page). Pass `trigger_type` for a single filtered request.
   */
  list: async (params?: HookListParams): Promise<HookListResponse> => {
    if (params?.trigger_type) {
      const response = await apiClient.get<HookListResponse>('/hooks', {
        params: {
          limit: params.limit ?? 200,
          offset: params.offset ?? 0,
          ...(params.enabled !== undefined ? { enabled: params.enabled } : {}),
          trigger_type: params.trigger_type,
        },
      });
      return response.data;
    }

    // Default: server-side event + manual only (never unfiltered / schedule-inclusive dump)
    const limit = params?.limit ?? 200;
    const offset = params?.offset ?? 0;
    const enabled = params?.enabled;
    const common = {
      limit,
      offset,
      ...(enabled !== undefined ? { enabled } : {}),
    };

    const [eventRes, manualRes] = await Promise.all([
      apiClient.get<HookListResponse>('/hooks', {
        params: { ...common, trigger_type: 'event' },
      }),
      apiClient.get<HookListResponse>('/hooks', {
        params: { ...common, trigger_type: 'manual' },
      }),
    ]);

    const byId = new Map<string, Hook>();
    for (const item of [...eventRes.data.items, ...manualRes.data.items]) {
      byId.set(item.id, item);
    }
    const items = sortHooksByUpdatedAtDesc(Array.from(byId.values()));
    const total = (eventRes.data.total ?? 0) + (manualRes.data.total ?? 0);
    return { items, total };
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
