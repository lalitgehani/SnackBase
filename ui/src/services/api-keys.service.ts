import { apiClient as api } from '@/lib/api';

export interface APIKeyListItem {
  id: string;
  name: string;
  key: string; // Masked key
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
  key: string; // Plaintext key (returned once)
  expires_at: string | null;
  created_at: string;
}

export interface APIKeyDetailResponse extends APIKeyListItem {
  updated_at: string;
}

export const apiKeysService = {
  getApiKeys: async (): Promise<APIKeyListResponse> => {
    const response = await api.get<APIKeyListResponse>('/admin/api-keys');
    return response.data;
  },

  createApiKey: async (data: APIKeyCreateRequest): Promise<APIKeyCreateResponse> => {
    const response = await api.post<APIKeyCreateResponse>('/admin/api-keys', data);
    return response.data;
  },

  getApiKeyById: async (id: string): Promise<APIKeyDetailResponse> => {
    const response = await api.get<APIKeyDetailResponse>(`/admin/api-keys/${id}`);
    return response.data;
  },

  revokeApiKey: async (id: string): Promise<void> => {
    await api.delete(`/admin/api-keys/${id}`);
  },
};
