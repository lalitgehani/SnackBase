/**
 * Roles API service
 * Handles API calls for role and permission management
 */

import { apiClient } from '@/lib/api';

export interface Role {
  id: number;
  name: string;
  description: string | null;
}

export interface RoleListItem extends Role {
  collections_count: number;
}

export interface RoleListResponse {
  items: RoleListItem[];
  total: number;
}

export interface CreateRoleData {
  name: string;
  description?: string;
}

export interface UpdateRoleData {
  name: string;
  description?: string;
}

export interface OperationRule {
  rule: string;
  fields: string[] | '*';
}

export interface CollectionPermission {
  collection: string;
  permission_id: number | null;
  create: OperationRule | null;
  read: OperationRule | null;
  update: OperationRule | null;
  delete: OperationRule | null;
}

export interface RolePermissionsResponse {
  role_id: number;
  role_name: string;
  permissions: CollectionPermission[];
}

export interface ValidateRuleRequest {
  rule: string;
}

export interface ValidateRuleResponse {
  valid: boolean;
  error: string | null;
}

export interface TestRuleRequest {
  rule: string;
  context: Record<string, any>;
}

export interface TestRuleResponse {
  allowed: boolean;
  error: string | null;
  evaluation_details: string | null;
}

/**
 * Get list of roles
 */
export const getRoles = async (): Promise<RoleListResponse> => {
  const response = await apiClient.get<RoleListResponse>('/roles');
  return response.data;
};

/**
 * Get role by ID
 */
export const getRoleById = async (roleId: number): Promise<Role> => {
  const response = await apiClient.get<Role>(`/roles/${roleId}`);
  return response.data;
};

/**
 * Create a new role
 */
export const createRole = async (data: CreateRoleData): Promise<Role> => {
  const response = await apiClient.post<Role>('/roles', data);
  return response.data;
};

/**
 * Update a role
 */
export const updateRole = async (roleId: number, data: UpdateRoleData): Promise<Role> => {
  const response = await apiClient.put<Role>(`/roles/${roleId}`, data);
  return response.data;
};

/**
 * Delete a role
 */
export const deleteRole = async (roleId: number): Promise<void> => {
  await apiClient.delete(`/roles/${roleId}`);
};

/**
 * Get permissions for a role
 */
export const getRolePermissions = async (roleId: number): Promise<RolePermissionsResponse> => {
  const response = await apiClient.get<RolePermissionsResponse>(`/roles/${roleId}/permissions`);
  return response.data;
};

/**
 * Validate a permission rule
 */
export const validateRule = async (rule: string): Promise<ValidateRuleResponse> => {
  const response = await apiClient.post<ValidateRuleResponse>('/roles/validate-rule', { rule });
  return response.data;
};

/**
 * Test a permission rule with sample data
 */
export const testRule = async (
  rule: string,
  context: Record<string, any>
): Promise<TestRuleResponse> => {
  const response = await apiClient.post<TestRuleResponse>('/roles/test-rule', { rule, context });
  return response.data;
};
