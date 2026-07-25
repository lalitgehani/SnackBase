/**
 * Codelists API service
 */

import { apiClient } from '@/lib/api';
import type {
  Codelist,
  CodelistCreate,
  CodelistOverride,
  CodelistUpdate,
  CodelistValue,
  CodelistValueCreate,
  CodelistValueUpdate,
  EffectiveCodelistValue,
  OverridePayload,
} from '@/types/codelist';

export const listCodelists = async (params?: {
  scope?: string;
  active?: boolean;
}): Promise<Codelist[]> => {
  const response = await apiClient.get<Codelist[]>('/codelists', { params });
  return response.data;
};

export const getCodelist = async (code: string): Promise<Codelist> => {
  const response = await apiClient.get<Codelist>(`/codelists/${code}`);
  return response.data;
};

export const getEffectiveValues = async (
  code: string,
  params?: { lang?: string; active?: boolean; account_id?: string },
): Promise<EffectiveCodelistValue[]> => {
  const response = await apiClient.get<EffectiveCodelistValue[]>(
    `/codelists/${code}/values`,
    { params },
  );
  return response.data;
};

export const createCodelist = async (data: CodelistCreate): Promise<Codelist> => {
  const response = await apiClient.post<Codelist>('/codelists', data);
  return response.data;
};

export const updateCodelist = async (
  code: string,
  data: CodelistUpdate,
): Promise<Codelist> => {
  const response = await apiClient.patch<Codelist>(`/codelists/${code}`, data);
  return response.data;
};

export const deleteCodelist = async (
  code: string,
  hard = false,
): Promise<Codelist> => {
  const response = await apiClient.delete<Codelist>(`/codelists/${code}`, {
    params: { hard },
  });
  return response.data;
};

export const listManageValues = async (
  code: string,
  includeInactive = true,
): Promise<CodelistValue[]> => {
  const response = await apiClient.get<CodelistValue[]>(
    `/codelists/${code}/manage/values`,
    { params: { include_inactive: includeInactive } },
  );
  return response.data;
};

export const createValue = async (
  code: string,
  data: CodelistValueCreate,
): Promise<CodelistValue> => {
  const response = await apiClient.post<CodelistValue>(
    `/codelists/${code}/manage/values`,
    data,
  );
  return response.data;
};

export const updateValue = async (
  code: string,
  valueCode: string,
  data: CodelistValueUpdate,
): Promise<CodelistValue> => {
  const response = await apiClient.patch<CodelistValue>(
    `/codelists/${code}/manage/values/${valueCode}`,
    data,
  );
  return response.data;
};

export const upsertLabels = async (
  code: string,
  valueCode: string,
  labels: Array<{
    language: string;
    label: string;
    description?: string | null;
    is_preferred?: boolean;
  }>,
) => {
  const response = await apiClient.post(
    `/codelists/${code}/manage/values/${valueCode}/labels`,
    labels,
  );
  return response.data;
};

export const setOverride = async (
  code: string,
  valueCode: string,
  data: OverridePayload,
  accountId?: string,
): Promise<CodelistOverride> => {
  const response = await apiClient.put<CodelistOverride>(
    `/codelists/${code}/values/${valueCode}/override`,
    data,
    { params: accountId ? { account_id: accountId } : undefined },
  );
  return response.data;
};

export const clearOverride = async (
  code: string,
  valueCode: string,
  accountId?: string,
): Promise<void> => {
  await apiClient.delete(`/codelists/${code}/values/${valueCode}/override`, {
    params: accountId ? { account_id: accountId } : undefined,
  });
};

export const listOverrides = async (
  code: string,
  accountId?: string,
): Promise<CodelistOverride[]> => {
  const response = await apiClient.get<CodelistOverride[]>(
    `/codelists/${code}/overrides`,
    { params: accountId ? { account_id: accountId } : undefined },
  );
  return response.data;
};

export const exportCodelist = async (code: string): Promise<Record<string, unknown>> => {
  const response = await apiClient.get<Record<string, unknown>>(
    `/codelists/${code}/export`,
  );
  return response.data;
};

export const importCodelist = async (
  packageData: Record<string, unknown>,
): Promise<Codelist> => {
  const response = await apiClient.post<Codelist>('/codelists/import', {
    package: packageData,
  });
  return response.data;
};

/** Validate codelist code pattern (PRD: ^[a-z][a-z0-9_]*$) */
export function isValidCodelistCode(code: string): boolean {
  return /^[a-z][a-z0-9_]*$/.test(code);
}
