/**
 * Service client for instance backup management (/api/v1/backups) and the
 * backup_settings configuration category.
 *
 * The backup endpoints are not part of @snackbase/sdk yet, so this module
 * speaks axios directly. Both deployment modes are supported:
 * - self-host: instance base URL, instance token from the SDK storage key
 * - platform: /env/{ref} proxied base URL, control-plane session token
 *
 * eslint-disable-next-file: The repo-wide `no-restricted-imports` rule
 * pushes HTTP through @snackbase/sdk, but the /api/v1/backups endpoints are
 * not part of the SDK yet — this PRD's service client is axios by design.
 */
/* eslint-disable no-restricted-imports */
import axios from 'axios';
import { IS_PLATFORM, loadConfig, platformBaseUrl } from '@/lib/config';
import {
  AUTH_STORAGE_KEY,
  CONTROL_PLANE_AUTH_STORAGE_KEY,
} from '@/lib/snackbase/constants';

export interface BackupActiveOperation {
  operation: 'backup' | 'restore';
  name: string;
  pid: number;
  started_at: string;
}

export interface BackupEntry {
  name: string;
  size: number;
  modified: string;
  is_automatic: boolean;
  backup_type: 'sqlite_physical' | 'logical' | string;
  restorable: boolean;
}

export interface BackupListResponse {
  backups: BackupEntry[];
  active: BackupActiveOperation | null;
  consecutive_failures: number;
  last_error: string | null;
  database_engine: string;
}

export interface RestoreIssue {
  type: string;
  severity: 'blocking' | 'warning' | string;
  message: string;
}

export interface RestorePreview {
  archive_name: string;
  manifest: Record<string, unknown>;
  created_at: string;
  source_version: string;
  includes_files: boolean;
  database_engine: string;
  backup_type: string;
  blocking: RestoreIssue[];
  warnings: RestoreIssue[];
}

export interface RestoreStatus {
  archive_name: string;
  status: 'completed' | 'failed' | string;
  completed_at: string;
  error?: string | null;
}

export interface BackupSettingsValues {
  destination?: 'local' | 's3';
  local_path?: string;
  s3_bucket?: string;
  s3_region?: string;
  s3_access_key_id?: string;
  s3_secret_access_key?: string;
  s3_key_prefix?: string;
  s3_endpoint_url?: string;
  cron?: string;
  max_keep?: number;
}

export interface BackupSettingsConfigRecord {
  id: string;
  category: string;
  provider_name: string;
  display_name: string;
  enabled: boolean;
  is_system: boolean;
  is_builtin: boolean;
  account_id: string;
}

function readStorageToken(key: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { token?: unknown; access_token?: unknown };
    if (typeof parsed.token === 'string' && parsed.token) return parsed.token;
    if (typeof parsed.access_token === 'string' && parsed.access_token) {
      return parsed.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

/** Instance token: platform bridge first, then the self-host SDK storage. */
export function resolveInstanceToken(): string | null {
  return (
    readStorageToken(CONTROL_PLANE_AUTH_STORAGE_KEY) ??
    readStorageToken(AUTH_STORAGE_KEY)
  );
}

export function resolveBackupsBaseUrl(envRef?: string): string {
  const config = loadConfig();
  if (IS_PLATFORM) {
    if (!envRef) {
      throw new Error('Backups API requires an environment ref in platform mode');
    }
    return platformBaseUrl(envRef, config);
  }
  return config.apiBaseUrl;
}

export interface BackupsApiOptions {
  baseUrl?: string;
  getToken?: () => string | null;
  envRef?: string;
}

export function createBackupsApi(options: BackupsApiOptions = {}) {
  const baseURL = options.baseUrl ?? resolveBackupsBaseUrl(options.envRef);
  const getToken = options.getToken ?? resolveInstanceToken;
  const http = axios.create({ baseURL });
  http.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  function downloadBlob(content: Blob, filename: string): void {
    const url = window.URL.createObjectURL(content);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  return {
    list: async (): Promise<BackupListResponse> => {
      const { data } = await http.get<BackupListResponse>('/api/v1/backups');
      return data;
    },

    create: async (name?: string | null, type?: string): Promise<{ name: string }> => {
      const body: Record<string, string> = {};
      if (name) body.name = name;
      if (type) body.type = type;
      const { data } = await http.post('/api/v1/backups', body);
      return data;
    },

    remove: async (name: string): Promise<void> => {
      await http.delete(`/api/v1/backups/${encodeURIComponent(name)}`);
    },

    download: async (name: string): Promise<void> => {
      const { data } = await http.get(
        `/api/v1/backups/${encodeURIComponent(name)}/download`,
        { responseType: 'blob' },
      );
      downloadBlob(data as Blob, name);
    },

    upload: async (file: File): Promise<{ name: string }> => {
      const form = new FormData();
      form.append('file', file);
      const { data } = await http.post('/api/v1/backups/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },

    restorePreview: async (
      name: string,
    ): Promise<RestorePreview> => {
      const { data } = await http.get(
        `/api/v1/backups/${encodeURIComponent(name)}/restore-preview`,
      );
      return data;
    },

    restore: async (
      name: string,
      force: boolean,
    ): Promise<Record<string, unknown>> => {
      const { data } = await http.post(
        `/api/v1/backups/${encodeURIComponent(name)}/restore`,
        { force },
      );
      return data;
    },

    restoreStatus: async (): Promise<RestoreStatus> => {
      const { data } = await http.get<RestoreStatus>(
        '/api/v1/backups/restore-status',
      );
      return data;
    },

    cronDescription: async (
      expr: string,
    ): Promise<{ expr: string; valid: boolean; error: string; description: string | null }> => {
      const { data } = await http.get('/api/v1/backups/cron-description', {
        params: { expr },
      });
      return data;
    },
  };
}

/** Settings CRUD against the generic configuration endpoints. */
export function createBackupsSettingsApi(options: BackupsApiOptions = {}) {
  const baseURL = options.baseUrl ?? resolveBackupsBaseUrl(options.envRef);
  const getToken = options.getToken ?? resolveInstanceToken;
  const http = axios.create({ baseURL });
  http.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return {
    async getConfig(): Promise<BackupSettingsConfigRecord | null> {
      const { data } = await http.get<BackupSettingsConfigRecord[]>(
        '/api/v1/admin/configuration/system',
        { params: { category: 'backup_settings' } },
      );
      const list = Array.isArray(data) ? data : [];
      return (
        list.find((item) => item.provider_name === 'backup' && item.is_system) ??
        list[0] ??
        null
      );
    },

    async getValues(configId: string): Promise<BackupSettingsValues> {
      const { data } = await http.get<BackupSettingsValues>(
        `/api/v1/admin/configuration/${configId}/values`,
      );
      return data;
    },

    async updateValues(
      configId: string,
      values: BackupSettingsValues,
    ): Promise<void> {
      await http.patch(
        `/api/v1/admin/configuration/${configId}/values`,
        values,
      );
    },

    async createConfig(values: BackupSettingsValues): Promise<{ id: string }> {
      const { data } = await http.post<{ id: string }>('/api/v1/admin/configuration', {
        category: 'backup_settings',
        provider_name: 'backup',
        display_name: 'Backup Settings',
        config: values,
      });
      return data;
    },
  };
}

/** Lazily-bound default instances following the codebase's bindService idiom. */
export const backupsApi = {
  list: () => createBackupsApi().list(),
  create: (...args: Parameters<ReturnType<typeof createBackupsApi>['create']>) =>
    createBackupsApi().create(...args),
  remove: (...args: Parameters<ReturnType<typeof createBackupsApi>['remove']>) =>
    createBackupsApi().remove(...args),
  download: (...args: Parameters<ReturnType<typeof createBackupsApi>['download']>) =>
    createBackupsApi().download(...args),
  upload: (...args: Parameters<ReturnType<typeof createBackupsApi>['upload']>) =>
    createBackupsApi().upload(...args),
  restorePreview: (
    ...args: Parameters<ReturnType<typeof createBackupsApi>['restorePreview']>
  ) => createBackupsApi().restorePreview(...args),
  restore: (...args: Parameters<ReturnType<typeof createBackupsApi>['restore']>) =>
    createBackupsApi().restore(...args),
  restoreStatus: () => createBackupsApi().restoreStatus(),
  cronDescription: (
    ...args: Parameters<ReturnType<typeof createBackupsApi>['cronDescription']>
  ) => createBackupsApi().cronDescription(...args),
};

export const backupsSettingsApi = {
  getConfig: () => createBackupsSettingsApi().getConfig(),
  getValues: (...args: Parameters<ReturnType<typeof createBackupsSettingsApi>['getValues']>) =>
    createBackupsSettingsApi().getValues(...args),
  updateValues: (
    ...args: Parameters<ReturnType<typeof createBackupsSettingsApi>['updateValues']>
  ) => createBackupsSettingsApi().updateValues(...args),
  createConfig: (
    ...args: Parameters<ReturnType<typeof createBackupsSettingsApi>['createConfig']>
  ) => createBackupsSettingsApi().createConfig(...args),
};

export default axios;
