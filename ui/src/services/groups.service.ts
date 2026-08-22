/**
 * Groups API service
 * Handles all API calls related to group management
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';
import type { User } from './users.service';

export interface Group {
  id: string;
  account_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  member_count?: number;
  users?: User[];
}

export interface GroupListParams {
  skip?: number;
  limit?: number;
  search?: string;
}

export interface CreateGroupRequest {
  name: string;
  description?: string | null;
  account_id?: string;
}

export interface UpdateGroupRequest {
  name?: string;
  description?: string | null;
}

export interface AddUserToGroupRequest {
  user_id: string;
}

export interface GroupListResponse {
  items: Group[];
  total: number;
}

export function createGroupsService(client: SnackBaseClient) {
  return {
    getGroups: (params?: GroupListParams): Promise<GroupListResponse> =>
      client.groups.list(params),
    getGroup: (id: string) => client.groups.get(id),
    createGroup: (data: CreateGroupRequest) => client.groups.create(data),
    updateGroup: (id: string, data: UpdateGroupRequest) => client.groups.update(id, data),
    deleteGroup: async (id: string) => {
      await client.groups.delete(id);
    },
    addUserToGroup: async (groupId: string, userId: string) => {
      await client.groups.addMember(groupId, userId);
    },
    removeUserFromGroup: async (groupId: string, userId: string) => {
      await client.groups.removeMember(groupId, userId);
    },
  };
}

export const useGroupsService = createServiceHook(createGroupsService);

const groupsService = bindService(createGroupsService);
export const getGroups = groupsService.getGroups;
export const getGroup = groupsService.getGroup;
export const createGroup = groupsService.createGroup;
export const updateGroup = groupsService.updateGroup;
export const deleteGroup = groupsService.deleteGroup;
export const addUserToGroup = groupsService.addUserToGroup;
export const removeUserFromGroup = groupsService.removeUserFromGroup;
