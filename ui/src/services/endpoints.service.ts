import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export interface EndpointAction {
  type: string;
  [key: string]: unknown;
}

export interface Endpoint {
  id: string;
  account_id: string;
  name: string;
  description: string | null;
  path: string;
  method: string;
  auth_required: boolean;
  condition: string | null;
  actions: EndpointAction[];
  response_template: Record<string, unknown> | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface EndpointListResponse {
  items: Endpoint[];
  total: number;
}

export interface EndpointExecution {
  id: string;
  endpoint_id: string;
  status: 'success' | 'partial' | 'failed';
  http_status: number;
  duration_ms: number | null;
  request_data: Record<string, unknown> | null;
  response_body: Record<string, unknown> | null;
  error_message: string | null;
  executed_at: string;
}

export interface EndpointExecutionListResponse {
  items: EndpointExecution[];
  total: number;
}

export interface CreateEndpointPayload {
  name: string;
  description?: string;
  path: string;
  method: string;
  auth_required?: boolean;
  condition?: string;
  actions?: EndpointAction[];
  response_template?: Record<string, unknown>;
  enabled?: boolean;
}

export interface UpdateEndpointPayload {
  name?: string;
  description?: string;
  path?: string;
  method?: string;
  auth_required?: boolean;
  condition?: string;
  actions?: EndpointAction[];
  response_template?: Record<string, unknown> | null;
  enabled?: boolean;
}

export function createEndpointsService(client: SnackBaseClient) {
  return {
    list: (filters?: { method?: string; enabled?: boolean }) =>
      client.endpoints.list({ limit: 200, ...filters }) as Promise<EndpointListResponse>,
    get: (id: string) => client.endpoints.get(id) as Promise<Endpoint>,
    create: (data: CreateEndpointPayload) => client.endpoints.create(data) as Promise<Endpoint>,
    update: (id: string, data: UpdateEndpointPayload) =>
      client.endpoints.update(id, data) as Promise<Endpoint>,
    toggle: (id: string) => client.endpoints.toggle(id) as Promise<Endpoint>,
    delete: async (id: string) => {
      await client.endpoints.delete(id);
    },
    listExecutions: (id: string) =>
      client.endpoints.listExecutions(id, { limit: 50 }) as Promise<EndpointExecutionListResponse>,
  };
}

export const useEndpointsService = createServiceHook(createEndpointsService);
export const endpointsService = bindService(createEndpointsService);
