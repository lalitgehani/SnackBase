/**
 * Groups API service
 * Handles all API calls related to group management
 */

import { apiClient } from '@/lib/api';
import type { User } from './users.service';

// Types
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

// API Functions

/**
 * Get list of groups with optional filtering and pagination
 */
export async function getGroups(params?: GroupListParams): Promise<GroupListResponse> {
  const queryParams = new URLSearchParams();
  
  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.search) queryParams.append('search', params.search);

  const response = await apiClient.get(`/groups?${queryParams.toString()}`);
  
  // Backend returns array directly, we need to wrap it for consistency
  if (Array.isArray(response.data)) {
    return {
      items: response.data,
      total: response.data.length,
    };
  }
  
  return response.data;
}

/**
 * Get a single group by ID
 */
export async function getGroup(id: string): Promise<Group> {
  const response = await apiClient.get(`/groups/${id}`);
  return response.data;
}

/**
 * Create a new group
 */
export async function createGroup(data: CreateGroupRequest): Promise<Group> {
  const response = await apiClient.post('/groups', data);
  return response.data;
}

/**
 * Update an existing group
 */
export async function updateGroup(id: string, data: UpdateGroupRequest): Promise<Group> {
  const response = await apiClient.patch(`/groups/${id}`, data);
  return response.data;
}

/**
 * Delete a group
 */
export async function deleteGroup(id: string): Promise<void> {
  await apiClient.delete(`/groups/${id}`);
}

/**
 * Add a user to a group
 */
export async function addUserToGroup(groupId: string, userId: string): Promise<void> {
  await apiClient.post(`/groups/${groupId}/users`, { user_id: userId });
}

/**
 * Remove a user from a group
 */
export async function removeUserFromGroup(groupId: string, userId: string): Promise<void> {
  await apiClient.delete(`/groups/${groupId}/users/${userId}`);
}
