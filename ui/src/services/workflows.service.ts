import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export interface EventTriggerConfig {
  type: 'event';
  event: string;
  collection?: string;
  condition?: string;
}

export interface ScheduleTriggerConfig {
  type: 'schedule';
  cron: string;
}

export interface ManualTriggerConfig {
  type: 'manual';
}

export interface WebhookTriggerConfig {
  type: 'webhook';
  token?: string;
}

export type WorkflowTriggerConfig =
  | EventTriggerConfig
  | ScheduleTriggerConfig
  | ManualTriggerConfig
  | WebhookTriggerConfig;

export interface WorkflowStep {
  type: string;
  name: string;
  next?: string | null;
  position_x?: number;
  position_y?: number;
  [key: string]: unknown;
}

export interface Workflow {
  id: string;
  account_id: string;
  name: string;
  description: string | null;
  trigger_type: string;
  trigger_config: WorkflowTriggerConfig;
  steps: WorkflowStep[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface WorkflowListResponse {
  items: Workflow[];
  total: number;
}

export interface WorkflowInstance {
  id: string;
  workflow_id: string;
  account_id: string;
  status: 'pending' | 'running' | 'waiting' | 'completed' | 'failed' | 'cancelled';
  current_step: string | null;
  context: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  resume_job_id: string | null;
}

export interface WorkflowStepLog {
  id: string;
  instance_id: string;
  workflow_id: string;
  account_id: string;
  step_name: string;
  step_type: string;
  status: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface WorkflowInstanceDetail extends WorkflowInstance {
  step_logs: WorkflowStepLog[];
}

export interface WorkflowInstanceListResponse {
  items: WorkflowInstance[];
  total: number;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  trigger: WorkflowTriggerConfig;
  steps: WorkflowStep[];
  enabled?: boolean;
}

export interface UpdateWorkflowRequest {
  name?: string;
  description?: string;
  trigger?: WorkflowTriggerConfig;
  steps?: WorkflowStep[];
  enabled?: boolean;
}

export function createWorkflowsService(client: SnackBaseClient) {
  return {
    list: () => client.workflows.list({ limit: 200 }) as Promise<WorkflowListResponse>,
    get: (id: string) => client.workflows.get(id) as Promise<Workflow>,
    create: (data: CreateWorkflowRequest) => client.workflows.create(data) as Promise<Workflow>,
    update: (id: string, data: UpdateWorkflowRequest) =>
      client.workflows.update(id, data) as Promise<Workflow>,
    toggle: (id: string) => client.workflows.toggle(id) as Promise<Workflow>,
    trigger: (id: string, body?: Record<string, unknown>) =>
      client.workflows.trigger(id, body) as Promise<{ message: string; instance_id: string }>,
    delete: async (id: string) => {
      await client.workflows.delete(id);
    },
    listInstances: (
      workflowId: string,
      params?: { status?: string; limit?: number; offset?: number },
    ) =>
      client.workflows.listInstances(workflowId, { limit: 50, ...params }) as Promise<
        WorkflowInstanceListResponse
      >,
    getInstance: (instanceId: string) =>
      client.workflows.getInstance(instanceId) as Promise<WorkflowInstanceDetail>,
    cancelInstance: (instanceId: string) =>
      client.workflows.cancelInstance(instanceId) as Promise<WorkflowInstance>,
    resumeInstance: (instanceId: string) =>
      client.workflows.resumeInstance(instanceId) as Promise<{ message: string; instance_id: string }>,
  };
}

export const useWorkflowsService = createServiceHook(createWorkflowsService);
export const workflowsService = bindService(createWorkflowsService);
