import { apiClient } from '@/lib/api';

// ---------------------------------------------------------------------------
// Trigger config types
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Step types
// ---------------------------------------------------------------------------

export interface WorkflowStep {
    type: string;
    name: string;
    next?: string | null;
    [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Core models
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const workflowsService = {
    list: async (): Promise<WorkflowListResponse> => {
        const response = await apiClient.get<WorkflowListResponse>('/workflows', {
            params: { limit: 200 },
        });
        return response.data;
    },

    get: async (id: string): Promise<Workflow> => {
        const response = await apiClient.get<Workflow>(`/workflows/${id}`);
        return response.data;
    },

    create: async (data: CreateWorkflowRequest): Promise<Workflow> => {
        const response = await apiClient.post<Workflow>('/workflows', data);
        return response.data;
    },

    update: async (id: string, data: UpdateWorkflowRequest): Promise<Workflow> => {
        const response = await apiClient.put<Workflow>(`/workflows/${id}`, data);
        return response.data;
    },

    toggle: async (id: string): Promise<Workflow> => {
        const response = await apiClient.patch<Workflow>(`/workflows/${id}/toggle`);
        return response.data;
    },

    trigger: async (id: string, body?: Record<string, unknown>): Promise<{ message: string; instance_id: string }> => {
        const response = await apiClient.post<{ message: string; instance_id: string }>(
            `/workflows/${id}/trigger`,
            body ?? {},
        );
        return response.data;
    },

    delete: async (id: string): Promise<void> => {
        await apiClient.delete(`/workflows/${id}`);
    },

    listInstances: async (
        workflowId: string,
        params?: { status?: string; limit?: number; offset?: number },
    ): Promise<WorkflowInstanceListResponse> => {
        const response = await apiClient.get<WorkflowInstanceListResponse>(
            `/workflows/${workflowId}/instances`,
            { params: { limit: 50, ...params } },
        );
        return response.data;
    },

    getInstance: async (instanceId: string): Promise<WorkflowInstanceDetail> => {
        const response = await apiClient.get<WorkflowInstanceDetail>(
            `/workflow-instances/${instanceId}`,
        );
        return response.data;
    },

    cancelInstance: async (instanceId: string): Promise<WorkflowInstance> => {
        const response = await apiClient.post<WorkflowInstance>(
            `/workflow-instances/${instanceId}/cancel`,
        );
        return response.data;
    },

    resumeInstance: async (instanceId: string): Promise<{ message: string; instance_id: string }> => {
        const response = await apiClient.post<{ message: string; instance_id: string }>(
            `/workflow-instances/${instanceId}/resume`,
        );
        return response.data;
    },
};
