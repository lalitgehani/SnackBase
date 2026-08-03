import { apiClient } from '@/lib/api';

export interface FunctionItem {
  id: string;
  account_id: string;
  slug: string;
  name: string;
  description: string | null;
  entrypoint: string;
  auth_required: boolean;
  enabled: boolean;
  status: string;
  active_version_id: string | null;
  grants: { capabilities?: string[] } | Record<string, unknown>;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface FunctionListResponse {
  items: FunctionItem[];
  total: number;
}

export interface FunctionVersion {
  id: string;
  function_id: string;
  version: number;
  dependencies: string[];
  sha256: string;
  env_path: string | null;
  created_by: string | null;
  created_at: string;
}

export interface FunctionBody {
  version_id: string;
  version: number;
  entrypoint: string;
  files: Record<string, string>;
  dependencies: string[];
  sha256: string;
}

export interface FunctionExecution {
  id: string;
  function_id: string;
  version_id: string | null;
  status: string;
  http_status: number;
  duration_ms: number | null;
  request_data: Record<string, unknown> | null;
  response_body: unknown;
  stdout: string | null;
  stderr: string | null;
  error_message: string | null;
  used_admin_client: boolean;
  executed_at: string;
}

export interface FunctionSecret {
  id: string;
  name: string;
  updated_at: string;
}

export interface FunctionStats {
  total: number;
  by_status: Record<string, number>;
  p50_ms: number | null;
  p95_ms: number | null;
  range: string;
}

export interface CreateFunctionPayload {
  name: string;
  slug: string;
  description?: string;
  auth_required?: boolean;
  entrypoint?: string;
}

export interface UpdateFunctionPayload {
  name?: string;
  description?: string;
  auth_required?: boolean;
  enabled?: boolean;
  status?: string;
  entrypoint?: string;
}

export interface DeployPayload {
  entrypoint?: string;
  dependencies?: string[];
  files: Record<string, string>;
}

export interface TestPayload {
  method?: string;
  path?: string;
  headers?: Record<string, string>;
  body?: unknown;
  query?: Record<string, unknown>;
}

export const functionsService = {
  list: async (): Promise<FunctionListResponse> => {
    const response = await apiClient.get<FunctionListResponse>('/functions', {
      params: { limit: 100 },
    });
    return response.data;
  },

  get: async (slug: string): Promise<FunctionItem> => {
    const response = await apiClient.get<FunctionItem>(`/functions/${slug}`);
    return response.data;
  },

  create: async (data: CreateFunctionPayload): Promise<FunctionItem> => {
    const response = await apiClient.post<FunctionItem>('/functions', data);
    return response.data;
  },

  update: async (slug: string, data: UpdateFunctionPayload): Promise<FunctionItem> => {
    const response = await apiClient.patch<FunctionItem>(`/functions/${slug}`, data);
    return response.data;
  },

  delete: async (slug: string): Promise<void> => {
    await apiClient.delete(`/functions/${slug}`);
  },

  deploy: async (
    slug: string,
    data: DeployPayload,
  ): Promise<{ function: FunctionItem; version: FunctionVersion }> => {
    const response = await apiClient.post<{ function: FunctionItem; version: FunctionVersion }>(
      `/functions/${slug}/deploy`,
      data,
    );
    return response.data;
  },

  getBody: async (slug: string, versionId?: string): Promise<FunctionBody> => {
    const response = await apiClient.get<FunctionBody>(`/functions/${slug}/body`, {
      params: versionId ? { version_id: versionId } : undefined,
    });
    return response.data;
  },

  listVersions: async (slug: string) => {
    const response = await apiClient.get<{ items: FunctionVersion[]; total: number }>(
      `/functions/${slug}/versions`,
    );
    return response.data;
  },

  activateVersion: async (slug: string, versionId: string): Promise<FunctionItem> => {
    const response = await apiClient.post<FunctionItem>(
      `/functions/${slug}/versions/${versionId}/activate`,
    );
    return response.data;
  },

  updateGrants: async (slug: string, grants: string[]): Promise<FunctionItem> => {
    const response = await apiClient.patch<FunctionItem>(`/functions/${slug}/grants`, { grants });
    return response.data;
  },

  listExecutions: async (slug: string) => {
    const response = await apiClient.get<{ items: FunctionExecution[]; total: number }>(
      `/functions/${slug}/executions`,
      { params: { limit: 50 } },
    );
    return response.data;
  },

  test: async (slug: string, data: TestPayload) => {
    const response = await apiClient.post(`/functions/${slug}/test`, data);
    return response.data as {
      execution_id: string;
      status: string;
      http_status: number;
      headers: Record<string, string>;
      body: unknown;
      stdout: string;
      stderr: string;
      error_message: string | null;
      duration_ms: number;
    };
  },

  stats: async (slug: string, range: '1h' | '24h' | '7d' = '24h'): Promise<FunctionStats> => {
    const response = await apiClient.get<FunctionStats>(`/functions/${slug}/stats`, {
      params: { range },
    });
    return response.data;
  },

  listSecrets: async () => {
    const response = await apiClient.get<{ items: FunctionSecret[]; total: number }>(
      '/function-secrets',
    );
    return response.data;
  },

  upsertSecret: async (name: string, value: string): Promise<FunctionSecret> => {
    const response = await apiClient.post<FunctionSecret>('/function-secrets', { name, value });
    return response.data;
  },

  deleteSecret: async (name: string): Promise<void> => {
    await apiClient.delete(`/function-secrets/${name}`);
  },
};
