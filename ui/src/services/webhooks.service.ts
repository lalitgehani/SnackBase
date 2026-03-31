import { apiClient } from '@/lib/api';

export interface WebhookListItem {
  id: string;
  account_id: string;
  url: string;
  collection: string;
  events: string[];
  filter: string | null;
  enabled: boolean;
  headers: Record<string, string> | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface WebhookCreateResponse extends WebhookListItem {
  secret: string;
}

export interface WebhookListResponse {
  items: WebhookListItem[];
  total: number;
}

export interface WebhookCreateRequest {
  url: string;
  collection: string;
  events: string[];
  secret?: string;
  filter?: string | null;
  enabled?: boolean;
  headers?: Record<string, string> | null;
}

export interface WebhookUpdateRequest {
  url?: string;
  collection?: string;
  events?: string[];
  filter?: string | null;
  enabled?: boolean;
  headers?: Record<string, string> | null;
}

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event: string;
  payload: Record<string, unknown>;
  response_status: number | null;
  response_body: string | null;
  attempt_number: number;
  delivered_at: string | null;
  next_retry_at: string | null;
  status: string;
  created_at: string;
}

export interface WebhookDeliveryListResponse {
  items: WebhookDelivery[];
  total: number;
}

export interface WebhookTestResponse {
  success: boolean;
  status_code: number | null;
  response_body: string | null;
  error: string | null;
}

export const webhooksService = {
  list: async (): Promise<WebhookListResponse> => {
    const response = await apiClient.get<WebhookListResponse>('/webhooks');
    return response.data;
  },

  get: async (id: string): Promise<WebhookListItem> => {
    const response = await apiClient.get<WebhookListItem>(`/webhooks/${id}`);
    return response.data;
  },

  create: async (data: WebhookCreateRequest): Promise<WebhookCreateResponse> => {
    const response = await apiClient.post<WebhookCreateResponse>('/webhooks', data);
    return response.data;
  },

  update: async (id: string, data: WebhookUpdateRequest): Promise<WebhookListItem> => {
    const response = await apiClient.put<WebhookListItem>(`/webhooks/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/webhooks/${id}`);
  },

  getDeliveries: async (
    webhookId: string,
    params: { limit?: number; offset?: number } = {}
  ): Promise<WebhookDeliveryListResponse> => {
    const response = await apiClient.get<WebhookDeliveryListResponse>(
      `/webhooks/${webhookId}/deliveries`,
      { params }
    );
    return response.data;
  },

  test: async (id: string): Promise<WebhookTestResponse> => {
    const response = await apiClient.post<WebhookTestResponse>(`/webhooks/${id}/test`);
    return response.data;
  },
};
