/**
 * Codelists API service
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';
import type {
  CodelistCreate,
  CodelistUpdate,
  CodelistValue,
  CodelistValueCreate,
  CodelistValueUpdate,
  OverridePayload,
} from '@/types/codelist';

export type {
  Codelist,
  CodelistOverride,
  EffectiveCodelistValue,
} from '@/types/codelist';

export function createCodelistsService(client: SnackBaseClient) {
  return {
    listCodelists: (params?: { scope?: string; active?: boolean }) => client.codelists.list(params),
    getCodelist: (code: string) => client.codelists.get(code),
    getEffectiveValues: (
      code: string,
      params?: { lang?: string; active?: boolean; account_id?: string },
    ) => client.codelists.getValues(code, params),
    createCodelist: (data: CodelistCreate) => client.codelists.create(data),
    updateCodelist: (code: string, data: CodelistUpdate) => client.codelists.update(code, data),
    deleteCodelist: (code: string, hard = false) => client.codelists.delete(code, hard),
    listManageValues: (code: string, includeInactive = true) =>
      client.codelists.listManageValues(code, includeInactive) as Promise<CodelistValue[]>,
    createValue: (code: string, data: CodelistValueCreate) =>
      client.codelists.createValue(code, data) as Promise<CodelistValue>,
    updateValue: (code: string, valueCode: string, data: CodelistValueUpdate) =>
      client.codelists.updateValue(code, valueCode, data) as Promise<CodelistValue>,
    upsertLabels: (
      code: string,
      valueCode: string,
      labels: Array<{
        language: string;
        label: string;
        description?: string | null;
        is_preferred?: boolean;
      }>,
    ) => client.codelists.upsertLabels(code, valueCode, labels),
    setOverride: (code: string, valueCode: string, data: OverridePayload, accountId?: string) =>
      client.codelists.setOverride(code, valueCode, data, accountId),
    clearOverride: async (code: string, valueCode: string, accountId?: string) => {
      await client.codelists.clearOverride(code, valueCode, accountId);
    },
    listOverrides: (code: string, accountId?: string) =>
      client.codelists.listOverrides(code, accountId),
    exportCodelist: (code: string) => client.codelists.export(code),
    importCodelist: (packageData: Record<string, unknown>) => client.codelists.import(packageData),
  };
}

export const useCodelistsService = createServiceHook(createCodelistsService);

const codelistsService = bindService(createCodelistsService);
export const listCodelists = codelistsService.listCodelists;
export const getCodelist = codelistsService.getCodelist;
export const getEffectiveValues = codelistsService.getEffectiveValues;
export const createCodelist = codelistsService.createCodelist;
export const updateCodelist = codelistsService.updateCodelist;
export const deleteCodelist = codelistsService.deleteCodelist;
export const listManageValues = codelistsService.listManageValues;
export const createValue = codelistsService.createValue;
export const updateValue = codelistsService.updateValue;
export const upsertLabels = codelistsService.upsertLabels;
export const setOverride = codelistsService.setOverride;
export const clearOverride = codelistsService.clearOverride;
export const listOverrides = codelistsService.listOverrides;
export const exportCodelist = codelistsService.exportCodelist;
export const importCodelist = codelistsService.importCodelist;

/** Validate codelist code pattern (PRD: ^[a-z][a-z0-9_]*$) */
export function isValidCodelistCode(code: string): boolean {
  return /^[a-z][a-z0-9_]*$/.test(code);
}
