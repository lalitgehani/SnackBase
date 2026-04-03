import { apiClient } from '@/lib/api';

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

export const endpointsService = {
  list: async (filters?: { method?: string; enabled?: boolean }): Promise<EndpointListResponse> => {
    const response = await apiClient.get<EndpointListResponse>('/endpoints', {
      params: { limit: 200, ...filters },
    });
    return response.data;
  },

  get: async (id: string): Promise<Endpoint> => {
    const response = await apiClient.get<Endpoint>(`/endpoints/${id}`);
    return response.data;
  },

  create: async (data: CreateEndpointPayload): Promise<Endpoint> => {
    const response = await apiClient.post<Endpoint>('/endpoints', data);
    return response.data;
  },

  update: async (id: string, data: UpdateEndpointPayload): Promise<Endpoint> => {
    const response = await apiClient.put<Endpoint>(`/endpoints/${id}`, data);
    return response.data;
  },

  toggle: async (id: string): Promise<Endpoint> => {
    const response = await apiClient.patch<Endpoint>(`/endpoints/${id}/toggle`);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/endpoints/${id}`);
  },

  listExecutions: async (id: string): Promise<EndpointExecutionListResponse> => {
    const response = await apiClient.get<EndpointExecutionListResponse>(
      `/endpoints/${id}/executions`,
      { params: { limit: 50 } },
    );
    return response.data;
  },
};
