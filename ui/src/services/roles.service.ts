/**
 * Roles API service
 * Handles API calls for role and permission management
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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
  context: Record<string, unknown>;
}

export interface TestRuleResponse {
  allowed: boolean;
  error: string | null;
  evaluation_details: string | null;
}

export interface PermissionUpdate {
  collection: string;
  operation: 'create' | 'read' | 'update' | 'delete';
  rule: string;
  fields: string[] | '*';
}

export interface BulkPermissionUpdateRequest {
  updates: PermissionUpdate[];
}

export interface BulkPermissionUpdateResponse {
  success_count: number;
  failure_count: number;
  errors: string[];
}

export function createRolesService(client: SnackBaseClient) {
  return {
    getRoles: () => client.roles.list(),
    getRoleById: (roleId: number) => client.roles.get(String(roleId)),
    createRole: (data: CreateRoleData) => client.roles.create(data),
    updateRole: (roleId: number, data: UpdateRoleData) =>
      client.roles.update(String(roleId), data),
    deleteRole: async (roleId: number) => {
      await client.roles.delete(String(roleId));
    },
    getRolePermissions: (roleId: number) =>
      client.roles.getPermissions(String(roleId)) as Promise<RolePermissionsResponse>,
    getRolePermissionsMatrix: (roleId: number) =>
      client.roles.getPermissionsMatrix(String(roleId)) as Promise<RolePermissionsResponse>,
    validateRule: (rule: string) => client.roles.validateRule(rule),
    testRule: (rule: string, context: Record<string, unknown>) =>
      client.roles.testRule(rule, context),
    updateRolePermissionsBulk: (roleId: number, request: BulkPermissionUpdateRequest) =>
      client.roles.updatePermissionsBulk(String(roleId), request),
    deletePermission: async (permissionId: number) => {
      await client.roles.deletePermission(permissionId);
    },
  };
}

export const useRolesService = createServiceHook(createRolesService);

const rolesService = bindService(createRolesService);
export const getRoles = rolesService.getRoles;
export const getRoleById = rolesService.getRoleById;
export const createRole = rolesService.createRole;
export const updateRole = rolesService.updateRole;
export const deleteRole = rolesService.deleteRole;
export const getRolePermissions = rolesService.getRolePermissions;
export const getRolePermissionsMatrix = rolesService.getRolePermissionsMatrix;
export const validateRule = rolesService.validateRule;
export const testRule = rolesService.testRule;
export const updateRolePermissionsBulk = rolesService.updateRolePermissionsBulk;
export const deletePermission = rolesService.deletePermission;
