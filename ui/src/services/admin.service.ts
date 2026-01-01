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
  account_id: string;
  logo_url: string;
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
};
