/**
 * Users API service
 * Handles API calls for user management (superadmin only)
 */

import { apiClient } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  account_id: string;
  account_name: string;
  role_id: number;
  role_name: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export type UserListItem = User;

export interface UserListResponse {
  total: number;
  items: UserListItem[];
}

export interface UserListParams {
  account_id?: string;
  role_id?: number;
  is_active?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
  sort?: string;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  account_id: string;
  role_id: number;
  is_active?: boolean;
}

export interface UpdateUserRequest {
  email?: string;
  role_id?: number;
  is_active?: boolean;
}

export interface PasswordResetRequest {
  new_password: string;
}

/**
 * Get list of users with optional filters
 */
export const getUsers = async (params?: UserListParams): Promise<UserListResponse> => {
  const response = await apiClient.get<UserListResponse>('/users', { params });
  return response.data;
};

/**
 * Get a user by ID
 */
export const getUser = async (userId: string): Promise<User> => {
  const response = await apiClient.get<User>(`/users/${userId}`);
  return response.data;
};

/**
 * Create a new user
 */
export const createUser = async (data: CreateUserRequest): Promise<User> => {
  const response = await apiClient.post<User>('/users', data);
  return response.data;
};

/**
 * Update a user
 */
export const updateUser = async (userId: string, data: UpdateUserRequest): Promise<User> => {
  const response = await apiClient.patch<User>(`/users/${userId}`, data);
  return response.data;
};

/**
 * Reset a user's password
 */
export const resetUserPassword = async (
  userId: string,
  data: PasswordResetRequest
): Promise<{ message: string }> => {
  const response = await apiClient.put<{ message: string }>(`/users/${userId}/password`, data);
  return response.data;
};

/**
 * Deactivate a user (soft delete)
 */
export const deactivateUser = async (userId: string): Promise<void> => {
  await apiClient.delete(`/users/${userId}`);
};
