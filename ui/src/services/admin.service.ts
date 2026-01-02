import { apiClient as api } from '@/lib/api';

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

  getAccounts: async (search?: string, page: number = 1, pageSize: number = 100): Promise<any> => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());
    if (search) {
      params.append('search', search);
    }
    const response = await api.get(`/accounts?${params.toString()}`);
    return response.data;
  },

  updateConfig: async (configId: string, enabled: boolean): Promise<any> => {
    const response = await api.patch(`/admin/configuration/${configId}`, { enabled });
    return response.data;
  },

  deleteConfig: async (configId: string): Promise<any> => {
    const response = await api.delete(`/admin/configuration/${configId}`);
    return response.data;
  },

  getAvailableProviders: async (category?: string): Promise<any[]> => {
    const params = new URLSearchParams();
    if (category && category !== 'all') {
      params.append('category', category);
    }
    const response = await api.get(`/admin/configuration/providers?${params.toString()}`);
    return response.data;
  },

  getProviderSchema: async (category: string, providerName: string): Promise<any> => {
    const response = await api.get(`/admin/configuration/schema/${category}/${providerName}`);
    return response.data;
  },

  getConfigValues: async (configId: string): Promise<Record<string, any>> => {
    const response = await api.get(`/admin/configuration/${configId}/values`);
    return response.data;
  },

  updateConfigValues: async (configId: string, values: Record<string, any>): Promise<any> => {
    const response = await api.patch(`/admin/configuration/${configId}/values`, values);
    return response.data;
  },

  createConfig: async (data: {
    category: string;
    provider_name: string;
    display_name: string;
    config: Record<string, any>;
    account_id?: string;
    logo_url?: string;
    enabled?: boolean;
    priority?: number;
  }): Promise<any> => {
    const response = await api.post('/admin/configuration', data);
    return response.data;
  },

  testConnection: async (data: {
    category: string;
    provider_name: string;
    config: Record<string, any>;
  }): Promise<{ success: boolean; message: string }> => {
    const response = await api.post('/admin/configuration/test-connection', data);
    return response.data;
  },
};
