import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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

export function createHooksService(client: SnackBaseClient) {
  return {
    /**
     * List hooks. When `trigger_type` is omitted, loads event + manual in parallel
     * (Hooks admin page). Pass `trigger_type` for a single filtered request.
     */
    list: async (params?: HookListParams): Promise<HookListResponse> => {
      if (params?.trigger_type) {
        return client.hooks.list({
          limit: params.limit ?? 200,
          offset: params.offset ?? 0,
          ...(params.enabled !== undefined ? { enabled: params.enabled } : {}),
          trigger_type: params.trigger_type,
        }) as Promise<HookListResponse>;
      }

      const limit = params?.limit ?? 200;
      const offset = params?.offset ?? 0;
      const enabled = params?.enabled;
      const common = {
        limit,
        offset,
        ...(enabled !== undefined ? { enabled } : {}),
      };

      const [eventRes, manualRes] = await Promise.all([
        client.hooks.list({ ...common, trigger_type: 'event' }),
        client.hooks.list({ ...common, trigger_type: 'manual' }),
      ]);

      const byId = new Map<string, Hook>();
      for (const item of [...eventRes.items, ...manualRes.items] as Hook[]) {
        byId.set(item.id, item);
      }
      const items = sortHooksByUpdatedAtDesc(Array.from(byId.values()));
      const total = (eventRes.total ?? 0) + (manualRes.total ?? 0);
      return { items, total };
    },

    get: (id: string) => client.hooks.get(id) as Promise<Hook>,
    create: (data: CreateHookRequest) => client.hooks.create(data) as Promise<Hook>,
    update: (id: string, data: UpdateHookRequest) => client.hooks.update(id, data) as Promise<Hook>,
    toggle: (id: string) => client.hooks.toggle(id) as Promise<Hook>,
    trigger: (id: string) =>
      client.hooks.trigger(id) as Promise<{
        message: string;
        status: string;
        actions_executed: number;
        error?: string;
      }>,
    delete: async (id: string) => {
      await client.hooks.delete(id);
    },
    listExecutions: (id: string) =>
      client.hooks.listExecutions(id, { limit: 50 }) as Promise<HookExecutionListResponse>,
  };
}

export const useHooksService = createServiceHook(createHooksService);
export const hooksService = bindService(createHooksService);
