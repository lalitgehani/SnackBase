/**
 * Macros service for managing SQL macros
 */

import { apiClient } from '@/lib/api';
import type {
    Macro,
    MacroCreate,
    MacroUpdate,
    MacroTestRequest,
    MacroTestResponse,
} from '@/types/macro';

/**
 * List all SQL macros
 */
export const listMacros = async (skip = 0, limit = 100): Promise<Macro[]> => {
    const response = await apiClient.get<Macro[]>('/macros', { params: { skip, limit } });
    return response.data;
};

/**
 * Get a SQL macro by ID
 */
export const getMacro = async (macroId: number): Promise<Macro> => {
    const response = await apiClient.get<Macro>(`/macros/${macroId}`);
    return response.data;
};

/**
 * Create a new SQL macro
 */
export const createMacro = async (macro: MacroCreate): Promise<Macro> => {
    const response = await apiClient.post<Macro>('/macros', macro);
    return response.data;
};

/**
 * Update a SQL macro
 */
export const updateMacro = async (macroId: number, macro: MacroUpdate): Promise<Macro> => {
    const response = await apiClient.put<Macro>(`/macros/${macroId}`, macro);
    return response.data;
};

/**
 * Delete a SQL macro
 */
export const deleteMacro = async (macroId: number): Promise<void> => {
    await apiClient.delete(`/macros/${macroId}`);
};

/**
 * Test a SQL macro execution
 */
export const testMacro = async (macroId: number, testRequest: MacroTestRequest): Promise<MacroTestResponse> => {
    const response = await apiClient.post<MacroTestResponse>(`/macros/${macroId}/test`, testRequest);
    return response.data;
};
