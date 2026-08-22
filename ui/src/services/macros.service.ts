/**
 * Macros service for managing SQL macros
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';
import type {
  Macro,
  MacroCreate,
  MacroUpdate,
  MacroTestRequest,
  MacroTestResponse,
} from '@/types/macro';

export function createMacrosService(client: SnackBaseClient) {
  return {
    listMacros: async (skip = 0, limit = 100): Promise<Macro[]> => {
      const result = await client.macros.list({ skip, limit });
      if (Array.isArray(result)) return result;
      return result.items;
    },
    getMacro: (macroId: number) => client.macros.get(String(macroId)),
    createMacro: (macro: MacroCreate) => client.macros.create(macro),
    updateMacro: (macroId: number, macro: MacroUpdate) =>
      client.macros.update(String(macroId), macro),
    deleteMacro: async (macroId: number) => {
      await client.macros.delete(String(macroId));
    },
    testMacro: (macroId: number, testRequest: MacroTestRequest): Promise<MacroTestResponse> =>
      client.macros.test(String(macroId), testRequest.parameters as string[]),
  };
}

export const useMacrosService = createServiceHook(createMacrosService);

const macrosService = bindService(createMacrosService);
export const listMacros = macrosService.listMacros;
export const getMacro = macrosService.getMacro;
export const createMacro = macrosService.createMacro;
export const updateMacro = macrosService.updateMacro;
export const deleteMacro = macrosService.deleteMacro;
export const testMacro = macrosService.testMacro;
