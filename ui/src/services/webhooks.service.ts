import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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
  error: string | null;
}

export interface WebhookDeliveryListParams {
  limit?: number;
  offset?: number;
}

export function createWebhooksService(client: SnackBaseClient) {
  return {
    list: async (): Promise<WebhookListResponse> => client.webhooks.list(),
    get: (id: string) => client.webhooks.get(id),
    create: (data: WebhookCreateRequest): Promise<WebhookCreateResponse> =>
      client.webhooks.create(data),
    update: (id: string, data: WebhookUpdateRequest) => client.webhooks.update(id, data),
    delete: async (id: string) => {
      await client.webhooks.delete(id);
    },
    getDeliveries: (id: string, params?: WebhookDeliveryListParams) =>
      client.webhooks.listDeliveries(id, params),
    test: (id: string): Promise<WebhookTestResponse> => client.webhooks.test(id),
  };
}

export const useWebhooksService = createServiceHook(createWebhooksService);
export const webhooksService = bindService(createWebhooksService);
