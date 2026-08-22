import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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
  actions?: Record<string, unknown>[];
}

export interface UpdateScheduledTaskRequest {
  name?: string;
  description?: string;
  cron?: string;
  enabled?: boolean;
}

export function createScheduledTasksService(client: SnackBaseClient) {
  return {
    list: () =>
      client.hooks.list({ trigger_type: 'schedule', limit: 200 }) as Promise<ScheduledTaskListResponse>,
    get: (id: string) => client.hooks.get(id) as Promise<ScheduledTask>,
    create: (data: CreateScheduledTaskRequest) =>
      client.hooks.create({
        name: data.name,
        description: data.description,
        trigger: { type: 'schedule', cron: data.cron },
        actions: data.actions ?? [],
        enabled: data.enabled ?? true,
      }) as Promise<ScheduledTask>,
    update: (id: string, data: UpdateScheduledTaskRequest) => {
      const payload: Record<string, unknown> = {};
      if (data.name !== undefined) payload.name = data.name;
      if (data.description !== undefined) payload.description = data.description;
      if (data.cron !== undefined) payload.trigger = { type: 'schedule', cron: data.cron };
      if (data.enabled !== undefined) payload.enabled = data.enabled;
      return client.hooks.update(id, payload) as Promise<ScheduledTask>;
    },
    toggle: (id: string) => client.hooks.toggle(id) as Promise<ScheduledTask>,
    trigger: (id: string) =>
      client.hooks.trigger(id) as Promise<{ job_id: string; message: string }>,
    delete: async (id: string) => {
      await client.hooks.delete(id);
    },
  };
}

export const useScheduledTasksService = createServiceHook(createScheduledTasksService);
export const scheduledTasksService = bindService(createScheduledTasksService);
