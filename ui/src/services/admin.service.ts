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

  updateConfig: async (configId: string, enabled: boolean): Promise<any> => {
    const response = await api.patch(`/admin/configuration/${configId}`, { enabled });
    return response.data;
  },

  deleteConfig: async (configId: string): Promise<any> => {
    const response = await api.delete(`/admin/configuration/${configId}`);
    return response.data;
  },
};
