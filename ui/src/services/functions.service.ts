import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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

export function createFunctionsService(client: SnackBaseClient) {
  return {
    list: () => client.functions.list(100) as Promise<FunctionListResponse>,
    get: (slug: string) => client.functions.get(slug) as Promise<FunctionItem>,
    create: (data: CreateFunctionPayload) => client.functions.create(data) as Promise<FunctionItem>,
    update: (slug: string, data: UpdateFunctionPayload) =>
      client.functions.update(slug, data) as Promise<FunctionItem>,
    delete: async (slug: string) => {
      await client.functions.delete(slug);
    },
    deploy: (slug: string, data: DeployPayload) => client.functions.deploy(slug, data),
    getBody: (slug: string, versionId?: string) =>
      client.functions.getBody(slug, versionId) as Promise<FunctionBody>,
    listVersions: (slug: string) => client.functions.listVersions(slug),
    activateVersion: (slug: string, versionId: string) =>
      client.functions.activateVersion(slug, versionId) as Promise<FunctionItem>,
    updateGrants: (slug: string, grants: string[]) =>
      client.functions.updateGrants(slug, grants) as Promise<FunctionItem>,
    listExecutions: (slug: string) => client.functions.listExecutions(slug),
    test: (slug: string, data: TestPayload) =>
      client.functions.test(slug, data) as Promise<{
        execution_id: string;
        status: string;
        http_status: number;
        headers: Record<string, string>;
        body: unknown;
        stdout: string;
        stderr: string;
        error_message: string | null;
        duration_ms: number;
      }>,
    stats: (slug: string, range: '1h' | '24h' | '7d' = '24h') =>
      client.functions.stats(slug, range) as Promise<FunctionStats>,
    listSecrets: () => client.functions.listSecrets(),
    upsertSecret: (name: string, value: string) =>
      client.functions.upsertSecret(name, value) as Promise<FunctionSecret>,
    deleteSecret: async (name: string) => {
      await client.functions.deleteSecret(name);
    },
  };
}

export const useFunctionsService = createServiceHook(createFunctionsService);
export const functionsService = bindService(createFunctionsService);
