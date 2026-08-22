import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export interface APIKeyListItem {
  id: string;
  name: string;
  key: string;
  last_used_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface APIKeyListResponse {
  items: APIKeyListItem[];
  total: number;
}

export interface APIKeyCreateRequest {
  name: string;
  expires_at: string | null;
}

export interface APIKeyCreateResponse {
  id: string;
  name: string;
  key: string;
  expires_at: string | null;
  created_at: string;
}

export interface APIKeyDetailResponse extends APIKeyListItem {
  updated_at: string;
}

export function createApiKeysService(client: SnackBaseClient) {
  return {
    getApiKeys: () => client.apiKeys.list() as Promise<APIKeyListResponse>,
    createApiKey: (data: APIKeyCreateRequest) =>
      client.apiKeys.create(data) as Promise<APIKeyCreateResponse>,
    getApiKeyById: (id: string) => client.apiKeys.get(id) as Promise<APIKeyDetailResponse>,
    revokeApiKey: async (id: string) => {
      await client.apiKeys.revoke(id);
    },
  };
}

export const useApiKeysService = createServiceHook(createApiKeysService);
export const apiKeysService = bindService(createApiKeysService);
