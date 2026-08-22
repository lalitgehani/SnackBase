import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';
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

export function createAdminService(client: SnackBaseClient) {
  return {
    getStats: () => client.admin.getConfigurationStats(),
    getRecentConfigs: (limit = 5) =>
      client.admin.getRecentConfigurations(limit) as Promise<Configuration[]>,
    getSystemConfigs: (category?: string) =>
      client.admin.listSystemConfigurations(category && category !== 'all' ? category : undefined),
    getAccountConfigs: (accountId: string, category?: string) =>
      client.admin.listAccountConfigurations(
        accountId,
        category && category !== 'all' ? category : undefined,
      ),
    getAccounts: (search?: string, page = 1, pageSize = 100): Promise<AccountListResponse> =>
      client.accounts.list({ page, page_size: pageSize, search }),
    updateConfig: (configId: string, enabled: boolean) =>
      client.admin.updateConfigurationStatus(configId, enabled),
    deleteConfig: async (configId: string) => {
      await client.admin.deleteConfiguration(configId);
    },
    getAvailableProviders: (category?: string) =>
      client.admin.listProviders(category && category !== 'all' ? category : undefined),
    getProviderSchema: (category: string, providerName: string) =>
      client.admin.getProviderSchema(category, providerName) as Promise<ProviderSchema>,
    getConfigValues: (configId: string) => client.admin.getConfigurationValues(configId),
    updateConfigValues: (configId: string, values: Record<string, unknown>) =>
      client.admin.updateConfigurationValues(configId, values),
    createConfig: (data: {
      category: string;
      provider_name: string;
      display_name: string;
      config: Record<string, unknown>;
      account_id?: string;
      logo_url?: string;
      enabled?: boolean;
      priority?: number;
    }) => client.admin.createConfiguration(data),
    testConnection: (data: {
      category: string;
      provider_name: string;
      config: Record<string, unknown>;
    }) => client.admin.testConnection(data.category, data.provider_name, data.config),
    setDefaultConfig: (configId: string) => client.admin.setConfigurationDefault(configId),
    unsetDefaultConfig: (configId: string) => client.admin.unsetConfigurationDefault(configId),
  };
}

export const useAdminService = createServiceHook(createAdminService);
export const adminService = bindService(createAdminService);
