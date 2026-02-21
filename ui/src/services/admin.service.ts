import { apiClient as api } from '@/lib/api';
import type { AccountListResponse } from './accounts.service';

export interface ProviderSchema {
  category: string;
  provider_name: string;
  display_name: string;
  logo_url?: string;
  properties: Record<string, {
    type: string;
    title?: string;
    description?: string;
    default?: unknown;
    enum?: string[];
    format?: string;
    writeOnly?: boolean;
  }>;
  required?: string[];
}

export interface AvailableProvider {
  category: string;
  provider_name: string;
  display_name: string;
  logo_url: string;
  description?: string;
}

export interface ConfigStats {
  total: number;
  by_category: Record<string, number>;
}

export interface ConfigurationStats {
  system_configs: ConfigStats;
  account_configs: ConfigStats;
}

export interface Configuration {
  id: string;
  display_name: string;
  provider_name: string;
  category: string;
  updated_at: string;
  is_system: boolean;
  is_builtin?: boolean;
  is_default?: boolean;
  account_id: string;
  logo_url: string;
  enabled: boolean;
  priority?: number;
}

export const adminService = {
  getStats: async (): Promise<ConfigurationStats> => {
    const response = await api.get('/admin/configuration/stats');
    return response.data;
  },

  getRecentConfigs: async (limit: number = 5): Promise<Configuration[]> => {
    const response = await api.get(`/admin/configuration/recent?limit=${limit}`);
    return response.data;
  },

  getSystemConfigs: async (category?: string): Promise<Configuration[]> => {
    const params = new URLSearchParams();
    if (category && category !== 'all') {
      params.append('category', category);
    }
    const response = await api.get(`/admin/configuration/system?${params.toString()}`);
    return response.data;
  },

  getAccountConfigs: async (accountId: string, category?: string): Promise<Configuration[]> => {
    const params = new URLSearchParams();
    params.append('account_id', accountId);
    if (category && category !== 'all') {
      params.append('category', category);
    }
    const response = await api.get(`/admin/configuration/account?${params.toString()}`);
    return response.data;
  },

  getAccounts: async (search?: string, page: number = 1, pageSize: number = 100): Promise<AccountListResponse> => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());
    if (search) {
      params.append('search', search);
    }
    const response = await api.get<AccountListResponse>(`/accounts?${params.toString()}`);
    return response.data;
  },

  updateConfig: async (configId: string, enabled: boolean): Promise<Configuration> => {
    const response = await api.patch<Configuration>(`/admin/configuration/${configId}`, { enabled });
    return response.data;
  },

  deleteConfig: async (configId: string): Promise<void> => {
    await api.delete(`/admin/configuration/${configId}`);
  },

  getAvailableProviders: async (category?: string): Promise<AvailableProvider[]> => {
    const params = new URLSearchParams();
    if (category && category !== 'all') {
      params.append('category', category);
    }
    const response = await api.get<AvailableProvider[]>(`/admin/configuration/providers?${params.toString()}`);
    return response.data;
  },

  getProviderSchema: async (category: string, providerName: string): Promise<ProviderSchema> => {
    const response = await api.get<ProviderSchema>(`/admin/configuration/schema/${category}/${providerName}`);
    return response.data;
  },

  getConfigValues: async (configId: string): Promise<Record<string, unknown>> => {
    const response = await api.get<Record<string, unknown>>(`/admin/configuration/${configId}/values`);
    return response.data;
  },

  updateConfigValues: async (configId: string, values: Record<string, unknown>): Promise<Configuration> => {
    const response = await api.patch<Configuration>(`/admin/configuration/${configId}/values`, values);
    return response.data;
  },

  createConfig: async (data: {
    category: string;
    provider_name: string;
    display_name: string;
    config: Record<string, unknown>;
    account_id?: string;
    logo_url?: string;
    enabled?: boolean;
    priority?: number;
  }): Promise<Configuration> => {
    const response = await api.post<Configuration>('/admin/configuration', data);
    return response.data;
  },

  testConnection: async (data: {
    category: string;
    provider_name: string;
    config: Record<string, unknown>;
  }): Promise<{ success: boolean; message: string }> => {
    const response = await api.post('/admin/configuration/test-connection', data);
    return response.data;
  },

  setDefaultConfig: async (configId: string): Promise<{ status: string; is_default: boolean; provider_name: string; display_name: string }> => {
    const response = await api.post(`/admin/configuration/${configId}/set-default`);
    return response.data;
  },

  unsetDefaultConfig: async (configId: string): Promise<{ status: string; is_default: boolean }> => {
    const response = await api.delete(`/admin/configuration/${configId}/set-default`);
    return response.data;
  },
};
